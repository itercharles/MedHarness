"""What a change reaches: the items that depend on the ones it changed.

Pure, like `traceability`: items and a config in, a mapping out. The graph is the
project's own — items whose type sits in a traceability chain, linked through fields that
declare `target_types`. A CR's `affected_items` or `affected_risk_items` is bookkeeping
about a change, not a design dependency, and neither is a defect's list of violated
requirements, so none of them drag the CR into the impact of what it changes.
"""

from __future__ import annotations

from typing import Any

from medharness.services.traceability import _ids, coverage_matrices


def dependents(items: list[dict], config: Any, changed: set[str], depth: int) -> dict[str, list[str]]:
    """``{dependent: [changed items it depends on]}`` within ``depth`` links of a changed item."""
    chain_types = {code for matrix in coverage_matrices(config) for code in matrix.path}
    depends_on_me: dict[str, list[str]] = {}
    for item in items:
        doc_type = config.doc_type_of(item["id"])
        if doc_type is None or doc_type.code not in chain_types:
            continue
        for field, allowed in config.link_properties(doc_type.code).items():
            if allowed:
                for target in _ids(item.get(field)):
                    depends_on_me.setdefault(target, []).append(item["id"])

    reached: dict[str, set[str]] = {}
    for origin in sorted(changed):
        seen, frontier = {origin}, [origin]
        for _ in range(depth):
            frontier = [dep for node in frontier for dep in depends_on_me.get(node, []) if dep not in seen]
            seen.update(frontier)
            for dep in frontier:
                reached.setdefault(dep, set()).add(origin)
    return {dep: sorted(origins) for dep, origins in sorted(reached.items())}


def unreviewed_dependents(store, cr_item: dict | None, dhf_item_changes: dict[str, list[str]]) -> dict[str, list[str]]:
    """Items that depend on one the branch changed, and are neither changed nor reviewed."""
    depth = store.config.impact_depth
    if cr_item is None or depth < 1:
        return {}
    changed = set(dhf_item_changes["created"] + dhf_item_changes["updated"] + dhf_item_changes["deleted"])
    origins = set(dhf_item_changes["updated"]) - {cr_item["id"]}
    reached = dependents(store.list_items(), store.config, origins, depth)
    settled = changed | set(cr_item.get("reviewed_items") or []) | {cr_item["id"]}
    return {dep: origins_ for dep, origins_ in reached.items() if dep not in settled}
