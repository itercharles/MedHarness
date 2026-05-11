"""Deterministic post-design validation.

Runs structural checks against the DHF state and the approved spec,
returning a list of structured error dicts (matching the spec_validation
pattern) suitable for assembling a fix-only LLM prompt.

Checks:
- Schema validity of all DHF items
- Required traceability rules, orphans, coverage gaps
- Every item listed in the spec's `affected_items` exists in the DHF
- Every item listed in the spec's `proposed_new_items` exists in the DHF
"""

from __future__ import annotations

from pathlib import Path

from medharness.services.spec_validation import parse_spec_frontmatter, read_spec_json


def validate_design(
    cr_id: str,
    dhf_path: Path,
    spec_path: Path,
) -> list[dict]:
    """Validate post-design DHF state.

    Args:
        cr_id: CR identifier (e.g., "CR-042"). Currently unused but reserved
            for future per-CR scoping (e.g., only check items linked to this CR).
        dhf_path: Path to the DHF root directory.
        spec_path: Path to the approved spec markdown file.

    Returns:
        List of error dicts with keys ``field``, ``issue``, ``fix``. Empty list
        means all checks passed.
    """
    errors: list[dict] = []

    try:
        import dhfkit.api as _api  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return [{
            "field": "environment",
            "issue": f"Could not import dhfkit.api: {exc}",
            "fix": "Ensure medharness is installed and dhfkit is on the Python path.",
        }]

    # --- Schema -----------------------------------------------------------------
    try:
        schema_result = _api.validate_schema(dhf_path)
    except Exception as exc:  # noqa: BLE001
        errors.append({
            "field": "schema",
            "issue": f"Schema validation raised: {exc}",
            "fix": "Inspect DHF/items/ for malformed YAML and fix the offending file.",
        })
        schema_result = {"valid": False, "errors": []}

    if not schema_result.get("valid"):
        for msg in schema_result.get("errors", []) or [
            "Schema validation failed without a specific message."
        ]:
            errors.append({
                "field": "schema",
                "issue": str(msg),
                "fix": "Fix the offending DHF item via "
                       "`medharness --dhf DHF dhf item update <ITEM_ID> --data '<JSON>'`.",
            })

    # --- Traceability -----------------------------------------------------------
    try:
        trace_result = _api.validate_traceability(dhf_path)
    except Exception as exc:  # noqa: BLE001
        errors.append({
            "field": "traceability",
            "issue": f"Traceability validation raised: {exc}",
            "fix": "Run `medharness --dhf DHF dhf validate traceability` locally to reproduce.",
        })
        trace_result = {"passed": True}

    if not trace_result.get("passed", True):
        required = trace_result.get("required") or {}
        for f in required.get("failures", []) or []:
            errors.append({
                "field": f"traceability.required.{f.get('field', 'links')}",
                "issue": (
                    f"{f.get('id')}: {f.get('issue', 'required traceability missing')}"
                ),
                "fix": (
                    f"Update {f.get('id')} so its `{f.get('field')}` "
                    f"references a {f.get('target_type')} item "
                    f"(need at least {f.get('min_count', 1)})."
                ),
            })

        for o in trace_result.get("orphans", []) or []:
            errors.append({
                "field": "traceability.orphan",
                "issue": f"{o.get('id')}: {o.get('issue', 'orphan item')}",
                "fix": (
                    f"Add a link from {o.get('id')} to one of "
                    f"{o.get('required_parents')} via `dhf item update`."
                ),
            })

        for c in trace_result.get("coverage", []) or []:
            if c.get("passed"):
                continue
            for uncovered in c.get("uncovered", []) or []:
                errors.append({
                    "field": f"traceability.coverage.{c.get('parent_type')}",
                    "issue": (
                        f"{uncovered} ({c.get('parent_type')}) has no covering "
                        f"{c.get('child_type')} child."
                    ),
                    "fix": (
                        f"Create a {c.get('child_type')} item linked to "
                        f"{uncovered}, or remove {uncovered} if it should not exist."
                    ),
                })

    # --- Affected items present -------------------------------------------------
    fm = read_spec_json(spec_path) or parse_spec_frontmatter(spec_path)
    if fm:
        try:
            listed_items = _api.list_items(dhf_path)
            existing_ids = {it["id"] for it in listed_items}
        except Exception as exc:  # noqa: BLE001
            errors.append({
                "field": "affected_items",
                "issue": f"Could not enumerate DHF items to verify spec expectations: {exc}",
                "fix": "Run `medharness --dhf DHF dhf item list` locally to debug.",
            })
            listed_items = []
            existing_ids = set()

        affected = fm.get("affected_items")
        if isinstance(affected, list) and affected:
            for uid in affected:
                if uid not in existing_ids:
                    errors.append({
                        "field": "affected_items",
                        "issue": (
                            f"Spec lists '{uid}' in affected_items but the design "
                            f"output does not contain it."
                        ),
                        "fix": (
                            f"Either create '{uid}' via `dhf item create`, or "
                            f"remove it from the spec affected_items if it is no "
                            f"longer in scope."
                        ),
                    })

        proposed = fm.get("proposed_new_items")
        if isinstance(proposed, list) and proposed:
            by_type_title = {
                (
                    str(item.get("type", "") or ""),
                    str(item.get("title", "") or "").strip(),
                )
                for item in listed_items
            }
            for idx, item in enumerate(proposed):
                if not isinstance(item, dict):
                    continue
                item_type = str(item.get("type", "") or "")
                title = str(item.get("title", "") or "").strip()
                if not item_type or not title:
                    continue
                if (item_type, title) not in by_type_title:
                    errors.append({
                        "field": f"proposed_new_items[{idx}]",
                        "issue": (
                            f"Spec proposes a new {item_type} item titled '{title}', "
                            "but the design output does not contain it."
                        ),
                        "fix": (
                            f"Create a new {item_type} item with title '{title}', or "
                            "remove/update the proposed_new_items entry in the spec if "
                            "the plan changed."
                        ),
                    })

    return errors
