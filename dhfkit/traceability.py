"""Traceability validation for DHF items.

Checks:
- Required: mandatory links defined by required_traceability rules (or V-model defaults)
- Coverage: every item at a parent level is linked by at least one child
"""

from __future__ import annotations

from typing import Any


def _prefix_of(uid: str) -> str:
    parts = uid.rsplit("-", 1)
    return parts[0] + "-" if len(parts) == 2 else ""


def check_required_traceability(items: list[dict], config: Any) -> dict:
    """Check mandatory traceability rules.

    Uses rules from config.required_traceability when present; falls back to
    the V-model defaults derived from ItemType when the list is empty.

    Args:
        items: List of item dicts with 'id', 'all_linked_uids', and item fields.
        config: ProjectConfig with required_traceability rules.

    Returns:
        {"passed": bool, "failures": [...], "summary": str}
    """
    from dhfkit.item_type import default_traceability_rules

    # None = not configured → use V-model defaults; [] = explicitly empty → no rules
    rules = config.required_traceability
    if rules is None:
        rules = default_traceability_rules()

    if not rules:
        return {"passed": True, "failures": [], "summary": "No required_traceability rules configured."}

    failures = []
    for rule in rules:
        source_dt = config.get_doc_type(rule.source_type)
        if not source_dt:
            continue

        source_items = [it for it in items if it["id"].startswith(source_dt.prefix)]
        target_dt = config.get_doc_type(rule.target_type)
        target_prefix = target_dt.prefix if target_dt else f"{rule.target_type}-"

        for s_item in source_items:
            count = 0
            if rule.direction == "upstream":
                val = s_item.get(rule.field)
                if isinstance(val, list):
                    linked = [uid for uid in val if uid.startswith(target_prefix)]
                    count = len(linked)
                elif isinstance(val, str) and val.startswith(target_prefix):
                    count = 1
            elif rule.direction == "downstream":
                count = sum(
                    1
                    for t_item in items
                    if t_item["id"].startswith(target_prefix)
                    and s_item["id"] in (t_item.get("all_linked_uids") or [])
                )

            if count < rule.min_count:
                direction_label = f"{rule.field} →" if rule.direction == "upstream" else "covered by"
                failures.append({
                    "id": s_item["id"],
                    "type": rule.source_type,
                    "rule": f"{rule.source_type} {direction_label} {rule.target_type}",
                    "target_type": rule.target_type,
                    "field": rule.field,
                    "direction": rule.direction,
                    "current_count": count,
                    "min_count": rule.min_count,
                    "issue": (
                        f"{rule.source_type} {direction_label} {rule.target_type} "
                        f"(count={count}, need ≥{rule.min_count})"
                    ),
                })

    passed = len(failures) == 0
    summary = f"{'PASS' if passed else 'FAIL'} — {len(failures)} required traceability failure(s)"

    return {
        "passed": passed,
        "failures": failures,
        "summary": summary,
    }


def check_traceability(items: list[dict], config: Any) -> dict:
    """
    Run full traceability validation.

    Args:
        items: List of item dicts (each must have 'id' and 'all_linked_uids').
        config: ProjectConfig with doc_types and optional traceability config.

    Returns:
        {
          "passed": bool,
          "orphans": [],
          "coverage": [...],
          "required": {...},
          "deprecation_warnings": [],
          "summary": str,
        }
    """
    from dhfkit.item_type import default_coverage_chains

    by_id = {item["id"]: item for item in items}

    required_result = check_required_traceability(items, config)

    matrices = config.traceability_matrices or []
    if not matrices:
        matrices = default_coverage_chains()

    coverage_results = []
    for matrix in matrices:
        path = matrix.path
        for i in range(len(path) - 1):
            parent_code = path[i]
            child_code = path[i + 1]

            parent_dt = config.get_doc_type(parent_code)
            child_dt = config.get_doc_type(child_code)
            if not parent_dt or not child_dt:
                continue

            parent_items = [it for it in items if it["id"].startswith(parent_dt.prefix)]
            if not parent_items:
                continue

            uncovered = []
            for p_item in parent_items:
                covered = any(
                    p_item["id"] in (by_id.get(c_item["id"], {}).get("all_linked_uids") or [])
                    for c_item in items
                    if c_item["id"].startswith(child_dt.prefix)
                )
                if not covered:
                    uncovered.append(p_item["id"])

            coverage_results.append({
                "matrix": matrix.name,
                "parent_type": parent_code,
                "child_type": child_code,
                "total": len(parent_items),
                "covered": len(parent_items) - len(uncovered),
                "uncovered": uncovered,
                "passed": len(uncovered) == 0,
            })

    passed = required_result["passed"] and all(r["passed"] for r in coverage_results)

    parts = []
    if not required_result["passed"]:
        parts.append(f"{len(required_result['failures'])} required failure(s)")
    uncovered_count = sum(len(r["uncovered"]) for r in coverage_results)
    if uncovered_count:
        parts.append(f"{uncovered_count} uncovered item(s)")
    summary = f"{'PASS' if passed else 'FAIL'} — " + ", ".join(parts) if parts else "All checks passed."

    return {
        "passed": passed,
        "required": required_result,
        "orphans": [],
        "coverage": coverage_results,
        "deprecation_warnings": [],
        "summary": summary,
    }
