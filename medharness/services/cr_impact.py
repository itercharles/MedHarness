from __future__ import annotations

"""Helpers for recording design impact back onto the CR item."""

from pathlib import Path

from dhfkit.local_adapter import LocalDHFAdapter


def _record_design_impact_in_cr(
    cr_id: str,
    dhf_path: Path,
    items_changed: dict[str, list[str]],
) -> dict[str, object]:
    try:
        adapter = LocalDHFAdapter(dhf_path)
    except FileNotFoundError:
        return {"recorded": False, "reason": "dhf_not_found"}

    existing = adapter.get_item(cr_id)
    if existing is None:
        return {"recorded": False, "reason": "cr_item_not_found"}

    touched_ids: list[str] = []
    for bucket in ("created", "updated", "deleted"):
        touched_ids.extend(items_changed.get(bucket, []) or [])
    recorded_affected = sorted(set(touched_ids))

    # Only update affected_items — implementation_notes is LLM-authored
    # during generate-dhf and must not be overwritten by the harness.
    adapter.update_item(
        cr_id,
        {"affected_items": recorded_affected},
        author="medharness",
        cr_id=cr_id,
    )
    return {
        "recorded": True,
        "reason": "updated",
        "affected_items": recorded_affected,
    }
