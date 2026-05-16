"""Release baseline builder — IEC 62304 §9 release record automation.

Verifies that all included CRs are completed or cancelled, collects the
software BOM from DHF SOUP items, and writes a release baseline JSON artifact.
Optionally creates a REL item in the DHF.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from medharness.services.soup_sync import parse_package_json, parse_requirements_txt


# ---------------------------------------------------------------------------
# Gate helpers
# ---------------------------------------------------------------------------

_TERMINAL_STATES = {"completed", "cancelled", "rejected"}


def _verify_cr_gates(dhf, cr_ids: list[str]) -> list[dict]:
    """Return violation dicts for any CR not in a terminal state."""
    import dhfkit.api as api

    violations: list[dict] = []
    for cr_id in cr_ids:
        item = api.get_item(dhf, cr_id)
        if item is None:
            violations.append({"cr": cr_id, "issue": "CR not found"})
            continue
        state = item.get("state") or item.get("status") or ""
        if state not in _TERMINAL_STATES:
            violations.append({
                "cr": cr_id,
                "issue": f"CR is in state '{state}', expected one of {sorted(_TERMINAL_STATES)}",
            })
    return violations


def _auto_collect_crs(dhf) -> list[str]:
    """Return IDs of completed CRs not already referenced in a REL item."""
    import dhfkit.api as api

    released_crs: set[str] = set()
    for item in api.list_items(dhf):
        if item.get("type") != "REL":
            continue
        for cr_id in item.get("included_items") or []:
            released_crs.add(cr_id)

    result: list[str] = []
    for item in api.list_items(dhf):
        if item.get("type") != "CR":
            continue
        state = item.get("state") or item.get("status") or ""
        if state == "completed" and item["uid"] not in released_crs:
            result.append(item["uid"])
    return sorted(result)


# ---------------------------------------------------------------------------
# BOM collection
# ---------------------------------------------------------------------------

def _collect_bom(dhf, manifest_paths: list[Path]) -> dict:
    """Collect SOUP items and manifest packages into a software BOM."""
    import dhfkit.api as api

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
                continue
            manifest_packages.extend(pkgs)
        except Exception:  # noqa: BLE001
            pass

    return {"dhf_soup": dhf_soup, "manifest_packages": manifest_packages}


# ---------------------------------------------------------------------------
# Release notes generation
# ---------------------------------------------------------------------------

def _generate_release_notes(
    version: str,
    cr_ids: list[str],
    bom: dict,
    dhf,
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
        lines.append(f"## Software BOM")
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

    # Gate: all CRs must be in a terminal state
    gate_violations = _verify_cr_gates(dhf, cr_ids)
    for v in gate_violations:
        errors.append(f"{v['cr']}: {v['issue']}")

    if gate_violations:
        return {
            "outcome": "completed_with_errors",
            "version": version,
            "cr_ids": cr_ids,
            "gate_violations": gate_violations,
            "errors": errors,
            "write": write,
            "artifacts": [],
        }

    # Collect BOM
    bom = _collect_bom(dhf, manifest_paths)

    # Generate release notes
    release_notes = _generate_release_notes(version, cr_ids, bom, dhf)

    # Build baseline record
    baseline = {
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "included_crs": sorted(cr_ids),
        "soup_count": len(bom.get("dhf_soup") or []),
        "manifest_packages_count": len(bom.get("manifest_packages") or []),
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
        "soup_count": len(bom.get("dhf_soup") or []),
        "manifest_packages_count": len(bom.get("manifest_packages") or []),
        "write": write,
        "errors": errors,
    }
