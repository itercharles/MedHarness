"""Traceability analysis over the whole item set.

`dhfkit` stores and reads records; a change-controlled organisation may already
store them in Jira, Azure DevOps, or a system of its own, and those handle a
single item well. What none of them do is take the items together and ask
whether the V-model holds: whether every system requirement gives rise to a
software one, whether a chain closes back on itself, which risks a change
touches. That is what this project is for, so it lives here and takes items as
data — not a storage path, not an adapter.

Referential integrity stays with the store. Two files claiming one ID, or a link
naming an item that does not exist, are questions about whether the data is
well-formed, and each adapter answers them its own way; a Jira link cannot point
at a missing issue in the first place. Everything below needs the set.
"""

from __future__ import annotations

from typing import Any, Iterable, List

import networkx as nx

from dhfkit.models.config import TraceabilityMatrix
from dhfkit.traceability import find_dangling_links

def _ids(value: Any) -> list[str]:
    values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    return [v for v in values if isinstance(v, str) and v]


def link_targets(item: dict, config: Any, target_code: str) -> set[str]:
    """The IDs `item` links to through a field that may point at `target_code`.

    A link in a field of another type does not make the item a child of a
    `target_code` item, whatever the ID says: a SWDD listing SRS-002 under
    `module` points at nothing the schema allows. A doc type that declares no link
    fields falls back to every link the item carries.
    """
    doc_type = config.doc_type_of(item["id"])
    declared = config.link_properties(doc_type.code) if doc_type else {}
    if not declared:
        return set(item.get("all_linked_uids") or [])
    found: set[str] = set()
    for field, allowed in declared.items():
        if allowed is None or target_code in allowed:
            found.update(_ids(item.get(field)))
    return found


def find_mistyped_links(items: list[dict], config: Any) -> list[dict]:
    """Links whose target is of a type the field does not allow.

    A field that declares `target_types` (`satisfies` → CRS) accepts nothing else.
    Targets that do not exist are `find_dangling_links`'s, not this one's.
    """
    mistyped = []
    for item in items:
        doc_type = config.doc_type_of(item["id"])
        if doc_type is None:
            continue
        for field, allowed in config.link_properties(doc_type.code).items():
            if not allowed:
                continue
            for target in _ids(item.get(field)):
                target_type = config.doc_type_of(target)
                if target_type is not None and target_type.code not in allowed:
                    mistyped.append({"source": item["id"], "field": field, "target": target,
                                     "found": target_type.code, "expected": list(allowed)})
    return sorted(mistyped, key=lambda m: (m["source"], m["field"], m["target"]))


def check_required_traceability(items: list[dict], config: Any) -> dict:
    """Check mandatory traceability rules.

    Uses the rules in config.required_traceability: the shipped defaults, or the
    project's own list in place of them.

    Args:
        items: List of item dicts with 'id', 'all_linked_uids', and item fields.
        config: ProjectConfig with required_traceability rules.

    Returns:
        {"passed": bool, "failures": [...], "summary": str}
    """

    rules = config.required_traceability
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
                    and s_item["id"] in link_targets(t_item, config, rule.source_type)
                )

            if count < rule.min_count and rule.or_covered_by:
                alternative_dt = config.get_doc_type(rule.or_covered_by)
                alternative_prefix = alternative_dt.prefix if alternative_dt else f"{rule.or_covered_by}-"
                if any(
                    t_item["id"].startswith(alternative_prefix)
                    and s_item["id"] in link_targets(t_item, config, rule.source_type)
                    for t_item in items
                ):
                    continue

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
                        + (f", or covered by {rule.or_covered_by}" if rule.or_covered_by else "")
                    ),
                })

    passed = len(failures) == 0
    summary = f"{'PASS' if passed else 'FAIL'} — {len(failures)} required traceability failure(s)"

    return {
        "passed": passed,
        "failures": failures,
        "summary": summary,
    }


def find_link_cycles(items: list[dict], link_fields: Iterable[str]) -> list[list[str]]:
    """Find traceability links that form a cycle.

    The V-model is directed: a customer requirement gives rise to a system
    requirement, which gives rise to a software one. A cycle means two items
    each derive from the other, so neither has an origin and the matrix loses
    the direction that makes it a matrix.

    Returns each cycle as the list of IDs in it, rotated to start at its lowest
    ID so the same cycle reads the same way between runs.
    """
    fields = sorted(set(link_fields))
    known = {str(i.get("id")) for i in items if i.get("id")}

    graph = nx.DiGraph()
    for item in items:
        source = str(item.get("id") or "")
        if not source:
            continue
        for field in fields:
            value = item.get(field)
            targets = value if isinstance(value, list) else [value] if value else []
            for target in targets:
                if str(target) in known:
                    graph.add_edge(source, str(target))

    cycles = []
    for cycle in nx.simple_cycles(graph):
        start = cycle.index(min(cycle))
        cycles.append(cycle[start:] + cycle[:start])
    return sorted(cycles, key=lambda c: (c[0], c))


def check_traceability(items: list[dict], config: Any) -> dict:
    """
    Run full traceability validation.

    Args:
        items: List of item dicts (each must have 'id' and 'all_linked_uids').
        config: ProjectConfig with doc_types and optional traceability config.

    Returns:
        {
          "passed": bool,
          "coverage": [...],
          "required": {...},
          "summary": str,
        }
    """

    required_result = check_required_traceability(items, config)

    matrices = coverage_matrices(config)

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
                    p_item["id"] in link_targets(c_item, config, parent_code)
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

    link_fields = config.relationship_fields()
    dangling = find_dangling_links(items, link_fields)
    cycles = find_link_cycles(items, link_fields)
    mistyped = find_mistyped_links(items, config)
    passed = (
        required_result["passed"]
        and not dangling
        and not mistyped
        and not cycles
        and all(r["passed"] for r in coverage_results)
    )

    parts = []
    if not required_result["passed"]:
        parts.append(f"{len(required_result['failures'])} required failure(s)")
    if dangling:
        parts.append(f"{len(dangling)} dangling link(s)")
    if mistyped:
        parts.append(f"{len(mistyped)} link(s) to the wrong type")
    if cycles:
        parts.append(f"{len(cycles)} link cycle(s)")
    uncovered_count = sum(len(r["uncovered"]) for r in coverage_results)
    if uncovered_count:
        parts.append(f"{uncovered_count} uncovered item(s)")
    summary = f"{'PASS' if passed else 'FAIL'} — " + ", ".join(parts) if parts else "All checks passed."

    return {
        "passed": passed,
        "required": required_result,
        "dangling": dangling,
        "mistyped": mistyped,
        "cycles": cycles,
        "coverage": coverage_results,
        "summary": summary,
    }



def analyse(adapter) -> dict:
    """Run the traceability analysis over everything a store holds.

    Takes an adapter rather than a path: the items are the store's to produce
    and the analysis is this project's to perform. `list_items()` already
    returns link fields and `all_linked_uids`, so nothing has to be reshaped —
    the adapter method this replaces did that reshaping *and* called the
    analysis, which is what put analysis inside the storage layer.
    """
    return check_traceability(adapter.list_items(), adapter.config)


def coverage_matrices(config: Any) -> List[TraceabilityMatrix]:
    """The chains coverage is checked along: the shipped defaults, or the project's own list in place of them."""
    return list(config.traceability_matrices)
