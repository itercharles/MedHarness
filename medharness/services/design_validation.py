"""Deterministic post-design validation.

Runs structural checks against the DHF state, returning a list of structured
error dicts suitable for assembling a fix-only LLM prompt.

Checks:
- Schema validity of all DHF items
- Required traceability rules, orphans, coverage gaps
- verification_criteria present on verifiable items touched by generate-dhf
"""

from __future__ import annotations

from pathlib import Path

import yaml

from dhfkit.exceptions import ValidationError

_VERIFIABLE_TYPES = frozenset({"CRS", "SYS", "SRS"})

# Maps parent tier code → expected child tier codes.
# If generate-dhf creates a parent item, at least one child-tier item in the
# same CR's changed_items should link back to it.
_CASCADE_CHILDREN: dict[str, list[str]] = {
    "CRS": ["SYS"],
    "SYS": ["SRS", "SYSARCH"],
    "SRS": ["SWDD"],
}


def _load_api():
    try:
        import dhfkit.api as _api
    except ImportError as exc:
        return None, [{
            "field": "environment",
            "issue": f"Could not import dhfkit.api: {exc}",
            "fix": "Ensure medharness is installed and dhfkit is on the Python path.",
        }]
    return _api, []


def _validate_schema_and_traceability(_api, dhf_path: Path) -> list[dict]:
    errors: list[dict] = []

    try:
        schema_result = _api.validate_schema(dhf_path)
    except (FileNotFoundError, ValidationError, ValueError, yaml.YAMLError) as exc:
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

    try:
        trace_result = _api.validate_traceability(dhf_path)
    except (FileNotFoundError, ValidationError, ValueError, yaml.YAMLError) as exc:
        errors.append({
            "field": "traceability",
            "issue": f"Traceability validation raised: {exc}",
            "fix": "Run `medharness --dhf DHF dhf validate traceability` locally to reproduce.",
        })
        trace_result = {"passed": True}

    if not trace_result.get("passed", True):
        required = trace_result.get("required") or {}
        for failure in required.get("failures", []):
            errors.append({
                "field": f"traceability.required.{failure.get('field', 'links')}",
                "issue": (
                    f"{failure.get('id')}: "
                    f"{failure.get('issue', 'required traceability missing')}"
                ),
                "fix": (
                    f"Update {failure.get('id')} so its `{failure.get('field')}` "
                    f"references a {failure.get('target_type')} item "
                    f"(need at least {failure.get('min_count', 1)})."
                ),
            })

        for orphan in trace_result.get("orphans", []):
            errors.append({
                "field": "traceability.orphan",
                "issue": f"{orphan.get('id')}: {orphan.get('issue', 'orphan item')}",
                "fix": (
                    f"Add a link from {orphan.get('id')} to one of "
                    f"{orphan.get('required_parents')} via `dhf item update`."
                ),
            })

        for coverage in trace_result.get("coverage", []):
            if coverage.get("passed"):
                continue
            for uncovered in coverage.get("uncovered", []):
                errors.append({
                    "field": f"traceability.coverage.{coverage.get('parent_type')}",
                    "issue": (
                        f"{uncovered} ({coverage.get('parent_type')}) has no covering "
                        f"{coverage.get('child_type')} child."
                    ),
                    "fix": (
                        f"Create a {coverage.get('child_type')} item linked to "
                        f"{uncovered}, or remove {uncovered} if it should not exist."
                    ),
                })

    return errors


def _list_items(_api, dhf_path: Path, field: str) -> tuple[list[dict], list[dict]]:
    try:
        return _api.list_items(dhf_path), []
    except (FileNotFoundError, ValidationError, ValueError, yaml.YAMLError) as exc:
        return [], [{
            "field": field,
            "issue": f"Could not enumerate DHF items to verify expectations: {exc}",
            "fix": "Run `medharness --dhf DHF dhf item list` locally to debug.",
        }]


def _item_has_verification_criteria(item: dict | None) -> bool:
    return bool(str((item or {}).get("verification_criteria") or "").strip())


def _item_type_from_id(uid: str) -> str:
    return uid.split("-", 1)[0] if uid else ""


_CASCADE_LINK_FIELDS = (
    "derives_from", "implements", "design", "mitigates",
    "satisfies", "guided_by", "informs",
)


def _item_references(item: dict, uid: str) -> bool:
    """Return True if any link field in item contains uid."""
    for field in _CASCADE_LINK_FIELDS:
        val = item.get(field)
        if val is None:
            continue
        if isinstance(val, str):
            if val == uid:
                return True
        elif isinstance(val, list):
            if uid in val:
                return True
    return False


def _validate_cascade_completeness(
    created_ids: list[str],
    by_id: dict[str, dict],
) -> list[dict]:
    """Check that newly created parent-tier items have at least one child-tier
    item anywhere in the current DHF that links back to them.

    Searches by_id (the full post-generate-dhf DHF state) rather than only the
    items touched in this run, so that child items created or updated in the same
    generate-dhf pass are found regardless of how the caller bucketed them.
    """
    errors: list[dict] = []
    child_prefixes_for = {
        code: tuple(f"{c}-" for c in children)
        for code, children in _CASCADE_CHILDREN.items()
    }

    for uid in created_ids:
        parent_type = _item_type_from_id(uid)
        child_prefixes = child_prefixes_for.get(parent_type)
        if not child_prefixes:
            continue

        if by_id.get(uid) is None:
            continue

        covered = any(
            cid.startswith(child_prefixes) and _item_references(item, uid)
            for cid, item in by_id.items()
        )
        if not covered:
            child_codes = _CASCADE_CHILDREN[parent_type]
            errors.append({
                "field": f"cascade.{uid}",
                "issue": (
                    f"'{uid}' ({parent_type}) was created by generate-dhf but no "
                    f"{' or '.join(child_codes)} item in the DHF links back to it."
                ),
                "fix": (
                    f"Create a {' or '.join(child_codes)} item that links to '{uid}', "
                    "or confirm this tier is explicitly out of scope for this CR."
                ),
            })
    return errors


def validate_dhf_structure(dhf_path: Path) -> list[dict]:
    """Run schema and traceability checks only — no item-level or reconciliation logic.

    Used as a pre-flight inside develop-cr to surface structural DHF gaps
    before the LLM runs, without triggering false positives from reconciliation
    checks that require a non-empty created_ids list.
    """
    _api, errors = _load_api()
    if _api is None:
        return errors
    errors.extend(_validate_schema_and_traceability(_api, dhf_path))
    return errors


def validate_generate_dhf(
    cr_id: str,
    dhf_path: Path,
    changed_items: dict[str, list[str]],
) -> list[dict]:
    """Validate generate-dhf output without relying on a spec artifact."""
    _api, errors = _load_api()
    if _api is None:
        return errors

    errors.extend(_validate_schema_and_traceability(_api, dhf_path))

    listed_items, item_errors = _list_items(_api, dhf_path, "changed_items")
    errors.extend(item_errors)
    by_id = {item["id"]: item for item in listed_items}

    created_ids: list[str] = []
    seen_created: set[str] = set()
    for uid in changed_items.get("created", []):
        if uid not in seen_created:
            seen_created.add(uid)
            created_ids.append(uid)

    seen: set[str] = set()
    ordered_changed_ids: list[str] = []
    for bucket in ("created", "updated"):
        for uid in changed_items.get(bucket, []):
            if uid in seen:
                continue
            seen.add(uid)
            ordered_changed_ids.append(uid)

    for idx, uid in enumerate(ordered_changed_ids):
        item = by_id.get(uid)
        if item is None:
            errors.append({
                "field": f"changed_items[{idx}]",
                "issue": (
                    f"`generate-dhf` reported changed item '{uid}', "
                    "but it is not present in the current DHF item list."
                ),
                "fix": (
                    f"Recreate or restore '{uid}', or remove the partial change so the "
                    "branch and DHF state match."
                ),
            })
            continue

        if _item_type_from_id(uid) in _VERIFIABLE_TYPES and not _item_has_verification_criteria(item):
            errors.append({
                "field": f"changed_items[{idx}].verification_criteria",
                "issue": (
                    f"`generate-dhf` changed verifiable item '{uid}', "
                    "but the DHF item has no `verification_criteria`."
                ),
                "fix": (
                    f"Update '{uid}' and add a `verification_criteria` field "
                    "with a measurable pass/fail criterion."
                ),
            })

    errors.extend(_validate_cascade_completeness(created_ids, by_id))
    return errors
