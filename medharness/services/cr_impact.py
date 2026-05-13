"""Helpers for recording design impact back onto the CR item."""

from pathlib import Path

from dhfkit.local_adapter import LocalDHFAdapter

from medharness.services.spec_validation import read_spec_json

_DESIGN_IMPACT_START = "<!-- medharness:design-impact:start -->"
_DESIGN_IMPACT_END = "<!-- medharness:design-impact:end -->"


def _normalize_proposed_item(entry: object) -> str:
    if not isinstance(entry, dict):
        return str(entry)
    item_type = str(entry.get("type") or "").strip()
    title = str(entry.get("title") or "").strip()
    parent = str(entry.get("parent") or "").strip()
    details = f"{item_type}: {title}".strip(": ")
    if parent:
        details = f"{details} (parent: {parent})"
    return details


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


def _build_design_impact_notes(spec_json: dict, items_changed: dict[str, list[str]]) -> str:
    proposed = spec_json.get("proposed_new_items")
    proposed_lines = (
        "\n".join(f"- {_normalize_proposed_item(entry)}" for entry in proposed)
        if isinstance(proposed, list) and proposed
        else "- none"
    )
    lines = [
        _DESIGN_IMPACT_START,
        "## Design Impact Snapshot",
        "",
        f"- Spec affected items: {_format_item_list(list(spec_json.get('affected_items', []) or []))}",
        "- Spec proposed new items:",
        proposed_lines,
        f"- DHF items created: {_format_item_list(items_changed.get('created', []))}",
        f"- DHF items updated: {_format_item_list(items_changed.get('updated', []))}",
        f"- DHF items deleted: {_format_item_list(items_changed.get('deleted', []))}",
        _DESIGN_IMPACT_END,
    ]
    return "\n".join(lines)


def _record_design_impact_in_cr(
    cr_id: str,
    dhf_path: Path,
    spec_path: Path,
    items_changed: dict[str, list[str]],
) -> None:
    spec_json = read_spec_json(spec_path) or {}
    try:
        adapter = LocalDHFAdapter(dhf_path)
    except FileNotFoundError:
        return

    existing = adapter.get_item(cr_id)
    if existing is None:
        return

    affected_ids = list(spec_json.get("affected_items", []) or [])
    touched_ids: list[str] = []
    for bucket in ("created", "updated", "deleted"):
        touched_ids.extend(items_changed.get(bucket, []) or [])
    recorded_affected = sorted(set(affected_ids) | set(touched_ids))

    existing_notes = str(existing.get("implementation_notes") or "")
    design_notes = _build_design_impact_notes(spec_json, items_changed)
    payload = {
        "affected_items": recorded_affected,
        "implementation_notes": _replace_managed_block(existing_notes, design_notes),
    }
    adapter.update_item(cr_id, payload, author="medharness", cr_id=cr_id)
