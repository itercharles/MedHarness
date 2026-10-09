"""Everything one release needs, built in one pass — IEC 62304 §9.

`build_release` runs the checks (`services/verify_release.py` and the other
`verify_*` gates), writes the baseline, the software BOM and the evidence
bundle to one directory, and — only when all of that passed — records the REL
item. This module only builds; what makes a release unfit is judged there.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dhfkit.store import open_store
from medharness.services.verify_release import (
    RELEASABLE_STATE,
    known_anomalies,
    still_closed,
    unreleasable_crs,
)
from medharness.services.soup_sync import _KNOWN_MANIFESTS, _dispatch_parser


def _auto_collect_crs(dhf: Path) -> list[str]:
    """Return IDs of completed CRs not already referenced in a REL item."""
    released_crs: set[str] = set()
    completed_unreleased: list[str] = []

    for item in open_store(dhf).list_items():
        item_type = item.get("type")
        if item_type == "REL":
            for cr_id in item.get("included_items") or []:
                released_crs.add(cr_id)
        elif item_type == "CR":
            state = item.get("status") or ""
            if state == RELEASABLE_STATE:
                completed_unreleased.append(item["id"])

    return sorted(uid for uid in completed_unreleased if uid not in released_crs)


# ---------------------------------------------------------------------------
# BOM collection
# ---------------------------------------------------------------------------

def _collect_bom(dhf: Path, manifest_paths: list[Path]) -> tuple[dict, list[str]]:
    """Collect SOUP items and manifest packages into a software BOM.

    Returns ``(bom_dict, errors)`` where errors is non-empty when any manifest
    is unreadable or unsupported — callers must propagate these to avoid
    producing an incomplete BOM that silently looks successful.
    """
    bom_errors: list[str] = []

    dhf_soup: list[dict] = []
    for item in open_store(dhf).list_items():
        if item.get("type") == "SOUP":
            dhf_soup.append({
                # Items expose "id"; keep the artifact key as "uid" so existing
                # release-baseline.json consumers are unaffected.
                "uid": item["id"],
                "name": item.get("name", ""),
                "version": item.get("version", ""),
                "manufacturer": item.get("manufacturer", ""),
                "license": item.get("license", ""),
                "safety_class": item.get("safety_class", ""),
            })

    manifest_packages: list[dict] = []
    for path in manifest_paths:
        # Support is decided by filename, not by catching the parser's error:
        # a malformed package.json raises JSONDecodeError, which is a ValueError,
        # and reporting that as "unsupported format" would send a reader looking
        # for the wrong problem.
        if path.name not in _KNOWN_MANIFESTS:
            bom_errors.append(f"Unsupported manifest format for BOM: {path}")
            continue
        try:
            # The same dispatch `build soup` uses. This listed requirements.txt and
            # package.json by hand and failed the whole baseline on the other
            # seven formats `build soup` reads — a project on a lockfile could sync
            # its SOUP register and then not build a release from it.
            manifest_packages.extend(_dispatch_parser(path))
        except Exception as exc:  # noqa: BLE001
            bom_errors.append(f"Failed to parse BOM manifest {path}: {exc}")

    return {"dhf_soup": dhf_soup, "manifest_packages": manifest_packages}, bom_errors


# ---------------------------------------------------------------------------
# Release notes generation
# ---------------------------------------------------------------------------

def _generate_release_notes(
    version: str,
    cr_ids: list[str],
    bom: dict,
    dhf: Path,
) -> str:
    lines: list[str] = [f"# Release {version}", ""]

    if cr_ids:
        lines.append("## Included Change Requests")
        for cr_id in sorted(cr_ids):
            item = open_store(dhf).get_item(cr_id)
            title = item.get("title", "") if item else ""
            lines.append(f"- {cr_id}: {title}")
        lines.append("")

    soup_count = len(bom.get("dhf_soup") or [])
    if soup_count:
        lines.append("## Software BOM")
        lines.append(f"{soup_count} SOUP component(s) in DHF — see software-bom.json for details.")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def _refused(version: str, cr_ids: list[str], errors: list[str],
             known_anomalies: list[dict] = ()) -> dict:
    """The baseline of a release that failed a gate before anything was written."""
    return {
        "outcome": "completed_with_errors",
        "version": version,
        "cr_ids": sorted(cr_ids),
        "known_anomalies": list(known_anomalies),
        "release_notes": "",
        "artifacts": [],
        "soup_count": 0,
        "manifest_packages_count": 0,
        "errors": errors,
        "warnings": [],
    }


def build_release_baseline(
    dhf: Path,
    version: str,
    manifest_paths: list[Path],
    cr_ids: list[str],
    out_dir: Path,
) -> dict:
    """Check the CRs and anomalies, and write the baseline and BOM artifacts."""
    errors: list[str] = []
    warnings: list[str] = []

    # Auto-collect CRs if none provided
    if not cr_ids:
        cr_ids = _auto_collect_crs(dhf)

    # Gate: all CRs must be completed
    gate_violations = unreleasable_crs(dhf, cr_ids)
    for v in gate_violations:
        errors.append(f"{v['cr']}: {v['issue']}")

    if gate_violations:
        return _refused(version, cr_ids, errors)

    # Gate: unresolved defects must each carry an assessment (§9.7)
    anomalies, anomaly_errors = known_anomalies(dhf)
    errors.extend(anomaly_errors)
    if anomaly_errors:
        return _refused(version, cr_ids, errors, anomalies)

    # Collect BOM — propagate any manifest errors so an incomplete BOM fails loudly
    bom, bom_errors = _collect_bom(dhf, manifest_paths)
    errors.extend(bom_errors)

    # Generate release notes
    release_notes = _generate_release_notes(version, cr_ids, bom, dhf)

    soup_count = len(bom.get("dhf_soup") or [])
    manifest_packages_count = len(bom.get("manifest_packages") or [])

    # Build baseline record
    baseline = {
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "included_crs": sorted(cr_ids),
        "soup_count": soup_count,
        "manifest_packages_count": manifest_packages_count,
        "known_anomalies": anomalies,
        "release_notes": release_notes,
    }

    bom_record = {
        "version": version,
        "generated_at": baseline["generated_at"],
        "dhf_soup": bom["dhf_soup"],
        "manifest_packages": bom["manifest_packages"],
    }

    # Write artifacts
    artifacts: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        baseline_path = out_dir / "release-baseline.json"
        baseline_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        artifacts.append(str(baseline_path))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Failed to write release-baseline.json: {exc}")

    try:
        bom_path = out_dir / "software-bom.json"
        bom_path.write_text(json.dumps(bom_record, indent=2), encoding="utf-8")
        artifacts.append(str(bom_path))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Failed to write software-bom.json: {exc}")

    # The same components in the format a regulator asks for. software-bom.json
    # is dhfkit's own shape and stays as it is; this is the CycloneDX view of
    # the release, which is what FDA cybersecurity guidance and the EU CRA want.
    try:
        from importlib.metadata import version as pkg_version

        from dhfkit.sbom import build_sbom, merge_release_components, purl_gap, write_sbom

        soup_items = [i for i in open_store(dhf).list_items() if i.get("type") == "SOUP"]
        components = merge_release_components(soup_items, bom["manifest_packages"])
        try:
            tool_version = pkg_version("medharness")
        except Exception:  # noqa: BLE001
            tool_version = "unknown"
        try:
            project_name = open_store(dhf).config.project_name
        except Exception:  # noqa: BLE001
            # Cosmetic metadata. It must not turn a successful release into
            # completed_with_errors — a name the SBOM cannot read is not a
            # reason to fail the baseline.
            project_name = dhf.resolve().parent.name
        document = build_sbom(
            components, project_name=project_name, tool_version=tool_version,
        )
        sbom_path, _changed = write_sbom(document, out_dir / "sbom.cdx.json")
        artifacts.append(str(sbom_path))
        # A component with no purl is one a consumer of the SBOM cannot resolve;
        # the two causes need different fixes, so each is named.
        for component in document["components"]:
            if "purl" not in component:
                props = {p["name"]: p["value"] for p in component.get("properties", [])}
                reason = purl_gap(component["name"], component["version"],
                                  props.get("dhfkit:ecosystem", ""))
                warnings.append(f"{component['bom-ref']}: no purl in the SBOM — {reason}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Failed to write sbom.cdx.json: {exc}")

    return {
        "outcome": "completed_with_errors" if errors else "completed",
        "version": version,
        "cr_ids": sorted(cr_ids),
        "known_anomalies": anomalies,
        "release_notes": release_notes,
        "artifacts": artifacts,
        "soup_count": soup_count,
        "manifest_packages_count": manifest_packages_count,
        "errors": errors,
        "warnings": warnings,
    }


def record_release(dhf: Path, baseline: dict) -> str:
    """Create the REL item for a baseline that passed. Returns its ID."""
    item = open_store(dhf).create_item({
        "type": "REL",
        "version": baseline["version"],
        "included_items": baseline["cr_ids"],
        # §9.7: the anomalies this release ships with, carried on the record
        # rather than only in the generated artifact.
        "known_anomalies": baseline["known_anomalies"],
        "release_notes": baseline["release_notes"],
    })
    return item["id"]


def build_release(
    dhf: Path,
    version: str,
    out_dir: Path,
    *,
    manifest_paths: list[Path] = (),
    cr_ids: list[str] = (),
    junit_paths: list[Path] = (),
    doc_format: str = "html",
    write: bool = False,
) -> dict:
    """Check, build and optionally record one release.

    The DHF is checked by `verify dhf`'s own gate with coverage gaps failing: a
    release is not the place for advisory findings, and a second definition of
    "the DHF is sound" is how two gates came to disagree before.
    """
    from medharness.services.release_artifacts import build_evidence_bundle
    from medharness.services.verify_dhf import ci_structural_gate

    gate = ci_structural_gate(dhf, strict=True)
    baseline = build_release_baseline(dhf, version, list(manifest_paths), list(cr_ids), out_dir)
    # Last, so its manifest hashes the baseline's files as well as its own.
    manifest = build_evidence_bundle(
        dhf, out_dir, version=version, junit_paths=list(junit_paths), doc_format=doc_format,
        gate=gate,
    )

    closure_errors, closure_warnings = still_closed(dhf, baseline["cr_ids"], list(junit_paths))
    errors = [f"DHF: {e}" for e in gate["errors"]] + baseline["errors"] + closure_errors
    warnings = list(baseline.get("warnings", [])) + closure_warnings
    rel_uid: Optional[str] = None
    if write and not errors:
        try:
            rel_uid = record_release(dhf, baseline)
        except Exception as exc:  # noqa: BLE001
            # The artifacts are written; a REL the store refused is reported,
            # not raised, so the run still says what it produced.
            errors.append(f"Failed to create REL item: {exc}")

    return {
        "outcome": "completed_with_errors" if errors else "completed",
        "version": version,
        "cr_ids": baseline["cr_ids"],
        "rel_uid": rel_uid,
        "soup_count": baseline["soup_count"],
        "artifacts": [f["path"] for f in manifest["files"]],
        "errors": errors,
        "warnings": warnings,
    }
