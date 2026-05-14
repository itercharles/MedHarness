from __future__ import annotations

"""Helpers for recording design impact back onto the CR item."""

from pathlib import Path

from dhfkit.local_adapter import LocalDHFAdapter

_DESIGN_IMPACT_START = "<!-- medharness:design-impact:start -->"
_DESIGN_IMPACT_END = "<!-- medharness:design-impact:end -->"


def _format_item_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _replace_managed_block(existing: str, block: str) -> str:
    start = existing.find(_DESIGN_IMPACT_START)
    end = existing.find(_DESIGN_IMPACT_END)
    if start != -1 and end != -1 and end > start:
        end += len(_DESIGN_IMPACT_END)
        replacement = block.strip()
        prefix = existing[:start].rstrip()
        suffix = existing[end:].lstrip()
        parts = [part for part in (prefix, replacement, suffix) if part]
        return "\n\n".join(parts).strip()
    if not existing.strip():
        return block.strip()
    return f"{existing.rstrip()}\n\n{block.strip()}"


def _build_design_impact_notes(items_changed: dict[str, list[str]]) -> str:
    lines = [
        _DESIGN_IMPACT_START,
        "## Design Impact Snapshot",
        "",
        f"- DHF items created: {_format_item_list(items_changed.get('created', []))}",
        f"- DHF items updated: {_format_item_list(items_changed.get('updated', []))}",
        f"- DHF items deleted: {_format_item_list(items_changed.get('deleted', []))}",
        _DESIGN_IMPACT_END,
    ]
    return "\n".join(lines)


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

    existing_notes = str(existing.get("implementation_notes") or "")
    design_notes = _build_design_impact_notes(items_changed)
    payload = {
        "affected_items": recorded_affected,
        "implementation_notes": _replace_managed_block(existing_notes, design_notes),
    }
    adapter.update_item(cr_id, payload, author="medharness", cr_id=cr_id)
    return {
        "recorded": True,
        "reason": "updated",
        "affected_items": recorded_affected,
    }
