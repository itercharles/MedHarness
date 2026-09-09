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
    # The CR is always in its own change set: `change plan` writes triage_result,
    # affected_risk_items and implementation_notes onto it, so it shows up as an
    # updated item and was then recorded as affecting itself. That is a
    # one-item traceability cycle, and `verify dhf` fails on it as of 0.20.0 —
    # so every CR the workflow planned would have failed the gate that shipped
    # to catch broken references.
    recorded_affected = sorted(set(touched_ids) - {cr_id})

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
