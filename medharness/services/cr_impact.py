"""Helpers for recording design impact back onto the CR item."""

from __future__ import annotations

from pathlib import Path

from dhfkit.store import open_store


def _record_design_impact_in_cr(
    cr_id: str,
    dhf_path: Path,
    items_changed: dict[str, list[str]],
) -> str | None:
    """Write the CR's `affected_items`. Returns why it could not, or None once it did."""
    try:
        adapter = open_store(dhf_path)
    except FileNotFoundError:
        return f"affected_items of {cr_id} not recorded: the DHF was not found."

    if adapter.get_item(cr_id) is None:
        return f"affected_items of {cr_id} not recorded: {cr_id} is not in the DHF."

    touched_ids: list[str] = []
    for bucket in ("created", "updated", "deleted"):
        touched_ids.extend(items_changed.get(bucket, []) or [])
    # `build plan` writes impact_analysis onto the CR, so the CR is in its own change set;
    # recording it would be a one-item traceability cycle that `verify dhf` fails on.
    adapter.update_item(cr_id, {"affected_items": sorted(set(touched_ids) - {cr_id})})
    return None
