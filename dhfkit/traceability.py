"""Traceability validation for DHF items.

Checks:
- Required: mandatory links defined by required_traceability rules (new)
- Orphans: items missing required parent links (based on deprecated allowed_parents)
- Coverage: every item at a parent level is linked by at least one child
"""

from __future__ import annotations

from typing import Any


def _prefix_of(uid: str) -> str:
    parts = uid.rsplit("-", 1)
    return parts[0] + "-" if len(parts) == 2 else ""


def _code_for_prefix(prefix: str, config: Any) -> str | None:
    for dt in config.doc_types:
        if dt.prefix == prefix:
            return dt.code
    return None


def check_required_traceability(items: list[dict], config: Any) -> dict:
    """Check mandatory traceability rules from required_traceability config.

    Args:
        items: List of item dicts with 'id', 'all_linked_uids', and item fields.
        config: ProjectConfig with required_traceability rules.

    Returns:
        {"passed": bool, "failures": [...], "summary": str}
    """
    rules = config.required_traceability or []
    if not rules:
        return {"passed": True, "failures": [], "summary": "No required_traceability rules configured."}

    by_id = {item["id"]: item for item in items}

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
                direction_label = f"{rule.field} →" if rule.direction == "upstream" else f"covered by"
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
        config: ProjectConfig with doc_types (each has .code, .prefix, .allowed_parents).

    Returns:
        {
          "passed": bool,
          "orphans": [...],
          "coverage": [...],
          "required": {...},
          "deprecation_warnings": [...],
          "summary": str,
        }
    """
    by_id = {item["id"]: item for item in items}

    # --- Required traceability (new) ------------------------------------------
    required_result = check_required_traceability(items, config)

    # --- Orphan check (deprecated allowed_parents) -----------------------------
    orphans = []
    deprecation_warnings = []
    for item in items:
        uid = item["id"]
        pfx = _prefix_of(uid)
        dt = config.get_doc_type_by_prefix(pfx)
        if not dt or not dt.allowed_parents:
            continue  # no parent requirement for this type

        deprecation_warnings.append(
            f"doc_type '{dt.code}' uses deprecated allowed_parents. "
            f"Migrate to required_traceability in global.yaml."
        )

        linked = item.get("all_linked_uids") or []
        linked_codes = {_code_for_prefix(_prefix_of(p), config) for p in linked if p in by_id}
        linked_codes.discard(None)

        # Skip orphan check for non-Functional items (e.g. Maintainability, Change Control)
        category = item.get("category", "Functional")
        if category and category != "Functional":
            continue

        has_valid_parent = bool(linked_codes & set(dt.allowed_parents))
        if not has_valid_parent:
            orphans.append({
                "id": uid,
                "type": dt.code,
                "required_parents": dt.allowed_parents,
                "linked_to": sorted(linked_codes),
                "issue": f"No link to any of {dt.allowed_parents}",
            })

    # --- Coverage check (per traceability_matrices path) ----------------------
    coverage_results = []
    for matrix in (config.traceability_matrices or []):
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
                # A child covers a parent when the child links to the parent
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

    passed = (
        required_result["passed"]
        and len(orphans) == 0
        and all(r["passed"] for r in coverage_results)
    )

    parts = []
    if not required_result["passed"]:
        parts.append(f"{len(required_result['failures'])} required failure(s)")
    if orphans:
        parts.append(f"{len(orphans)} orphan(s)")
    uncovered_count = sum(len(r["uncovered"]) for r in coverage_results)
    if uncovered_count:
        parts.append(f"{uncovered_count} uncovered item(s)")
    summary = f"{'PASS' if passed else 'FAIL'} — " + ", ".join(parts) if parts else "All checks passed."

    return {
        "passed": passed,
        "required": required_result,
        "orphans": orphans,
        "coverage": coverage_results,
        "deprecation_warnings": deprecation_warnings,
        "summary": summary,
    }
