"""Release baseline builder — IEC 62304 §9 release record automation.

Verifies that all included CRs are in `completed` state, collects the
software BOM from DHF SOUP items, and writes a release baseline JSON artifact.
Optionally creates a REL item in the DHF.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dhfkit.soup_sync import parse_package_json, parse_requirements_txt


# ---------------------------------------------------------------------------
# Gate helpers
# ---------------------------------------------------------------------------

# Only completed CRs may be included in a release.  cancelled/rejected CRs
# represent abandoned work and are not deliverables; including them would
# produce a REL item that fails validate_release() in dhfkit/core.py.
_RELEASABLE_STATE = "completed"


def _verify_cr_gates(dhf: Path, cr_ids: list[str]) -> list[dict]:
    """Return violation dicts for any CR not in `completed` state."""
    import dhfkit.api as api

    violations: list[dict] = []
    for cr_id in cr_ids:
        item = api.get_item(dhf, cr_id)
        if item is None:
            violations.append({"cr": cr_id, "issue": "CR not found"})
            continue
        state = item.get("state") or item.get("status") or ""
        if state != _RELEASABLE_STATE:
            violations.append({
                "cr": cr_id,
                "issue": f"CR is in state '{state}', must be '{_RELEASABLE_STATE}' to be included in a release",
            })
    return violations


def _auto_collect_crs(dhf: Path) -> list[str]:
    """Return IDs of completed CRs not already referenced in a REL item."""
    import dhfkit.api as api

    released_crs: set[str] = set()
    completed_unreleased: list[str] = []

    for item in api.list_items(dhf):
        item_type = item.get("type")
        if item_type == "REL":
            for cr_id in item.get("included_items") or []:
                released_crs.add(cr_id)
        elif item_type == "CR":
            state = item.get("state") or item.get("status") or ""
            if state == _RELEASABLE_STATE:
                completed_unreleased.append(item["uid"])

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
    import dhfkit.api as api

    bom_errors: list[str] = []

    dhf_soup: list[dict] = []
    for item in api.list_items(dhf):
        if item.get("type") == "SOUP":
            dhf_soup.append({
                "uid": item["uid"],
                "name": item.get("name", ""),
                "version": item.get("version", ""),
                "manufacturer": item.get("manufacturer", ""),
                "license": item.get("license", ""),
                "safety_class": item.get("safety_class", ""),
            })

    manifest_packages: list[dict] = []
    for path in manifest_paths:
        try:
            if path.name == "requirements.txt":
                pkgs = parse_requirements_txt(path)
            elif path.name == "package.json":
                pkgs = parse_package_json(path)
            else:
                bom_errors.append(f"Unsupported manifest format for BOM: {path}")
                continue
            manifest_packages.extend(pkgs)
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
    import dhfkit.api as api

    lines: list[str] = [f"# Release {version}", ""]

    if cr_ids:
        lines.append("## Included Change Requests")
        for cr_id in sorted(cr_ids):
            item = api.get_item(dhf, cr_id)
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

def build_release_baseline(
    dhf: Path,
    version: str,
    manifest_paths: list[Path],
    cr_ids: list[str],
    out_dir: Path,
    *,
    write: bool = False,
    author: str = "ci",
) -> dict:
    """Build a release baseline, write artifacts, optionally create a REL item.

    Returns a structured result dict.
    """
    import dhfkit.api as api

    errors: list[str] = []

    # Auto-collect CRs if none provided
    if not cr_ids:
        cr_ids = _auto_collect_crs(dhf)

    # Gate: all CRs must be completed
    gate_violations = _verify_cr_gates(dhf, cr_ids)
    for v in gate_violations:
        errors.append(f"{v['cr']}: {v['issue']}")

    if gate_violations:
        return {
            "outcome": "completed_with_errors",
            "version": version,
            "cr_ids": sorted(cr_ids),
            "rel_uid": None,
            "gate_violations": gate_violations,
            "artifacts": [],
            "soup_count": 0,
            "manifest_packages_count": 0,
            "write": write,
            "errors": errors,
        }

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

    # Optionally create a REL item
    rel_uid: Optional[str] = None
    if write:
        try:
            rel_data = {
                "type": "REL",
                "version": version,
                "included_items": sorted(cr_ids),
                "release_notes": release_notes,
            }
            new_item = api.create_item(dhf, rel_data, author=author)
            rel_uid = new_item["uid"]
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Failed to create REL item: {exc}")

    outcome = "completed_with_errors" if errors else "completed"
    return {
        "outcome": outcome,
        "version": version,
        "cr_ids": sorted(cr_ids),
        "rel_uid": rel_uid,
        "artifacts": artifacts,
        "soup_count": soup_count,
        "manifest_packages_count": manifest_packages_count,
        "write": write,
        "errors": errors,
    }
