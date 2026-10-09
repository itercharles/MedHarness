"""What makes a release unfit to cut: the checks `build release` runs before it writes anything.

Judging only, like every other `verify` module: nothing here writes.
"""

from __future__ import annotations

from pathlib import Path

from dhfkit.store import open_store

# Only completed CRs may be included in a release.  cancelled/rejected CRs
# represent abandoned work and are not deliverables; including them would
# produce a REL item that fails validate_release() in dhfkit/core.py.
RELEASABLE_STATE = "completed"


# A defect in any of these states still affects the software being released.
# 'cancelled' means the report was withdrawn, not that the software changed.
_UNRESOLVED_DEFECT_STATES = ("draft", "open", "in_progress")


def known_anomalies(dhf: Path) -> tuple[list[dict], list[str]]:
    """Gather unresolved defects and the rationale each carries.

    IEC 62304 §9.7 requires a release to document its residual known anomalies
    and why each is acceptable. A defect may ship — but not silently, and not
    without someone having judged it.

    Mirrors the SOUP accepted_vulns mechanism: an assessment recorded against
    the specific finding, not a blanket suppression.

    Returns (anomalies, errors).
    """
    anomalies: list[dict] = []
    errors: list[str] = []

    for item in open_store(dhf).list_items():
        uid = str(item.get("id") or "")
        if not uid.startswith("DEF-"):
            continue
        state = str(item.get("status") or "").strip().lower()
        if state not in _UNRESOLVED_DEFECT_STATES:
            continue

        rationale = str(item.get("release_rationale") or "").strip()
        entry = {
            "defect": uid,
            "title": item.get("title", ""),
            "severity": item.get("severity", ""),
            "state": state,
            "rationale": rationale,
        }
        anomalies.append(entry)
        if not rationale:
            errors.append(
                f"{uid} is unresolved (state '{state}') and has no "
                f"release_rationale. §9.7 requires the residual anomalies a "
                f"release ships with to be documented and assessed — record why "
                f"it is acceptable, or resolve it before baselining."
            )

    return sorted(anomalies, key=lambda a: a["defect"]), errors


def unreleasable_crs(dhf: Path, cr_ids: list[str]) -> list[dict]:
    """Return violation dicts for any CR not in `completed` state."""
    violations: list[dict] = []
    for cr_id in cr_ids:
        item = open_store(dhf).get_item(cr_id)
        if item is None:
            violations.append({"cr": cr_id, "issue": "CR not found"})
            continue
        state = item.get("status") or ""
        if state != RELEASABLE_STATE:
            violations.append({
                "cr": cr_id,
                "issue": f"CR is in state '{state}', must be '{RELEASABLE_STATE}' to be included in a release",
            })
    return violations


def still_closed(dhf: Path, cr_ids: list[str], junit_paths: list[Path]) -> tuple[list[str], list[str]]:
    """``(errors, warnings)`` of running `verify completion` again on each CR to be released.

    `completed` is a status anyone can write. A CR ships only if it still passes
    the same closure gate `verify completion` runs.
    """
    from medharness.services.verify_completion import cr_closure_gate

    errors: list[str] = []
    warnings: list[str] = []
    for cr_id in cr_ids:
        closure = cr_closure_gate(cr_id, dhf, junit_paths=junit_paths)
        errors += [f"{cr_id}: {e}" for e in closure["errors"]]
        warnings += [f"{cr_id}: {w}" for w in closure["warnings"]]
    return errors, warnings
