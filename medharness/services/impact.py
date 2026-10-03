"""What a change reaches: the items that depend on the ones it changed.

Pure, like `traceability`: items and a config in, a mapping out. The graph is the
project's own — items whose type sits in a traceability chain, linked through fields that
declare `target_types`. A CR's `affected_items` or `affected_risk_items` is bookkeeping
about a change, not a design dependency, and neither is a defect's list of violated
requirements, so none of them drag the CR into the impact of what it changes.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from medharness.services.traceability import _ids, coverage_matrices


NEAR_DUPLICATE_RATIO = 0.75


def chain_links(items: list[dict], config: Any) -> list[tuple[str, str]]:
    """``(item, target)`` for each typed link an item in a traceability chain carries."""
    chain_types = {code for matrix in coverage_matrices(config) for code in matrix.path}
    links = []
    for item in items:
        doc_type = config.doc_type_of(item["id"])
        if doc_type is None or doc_type.code not in chain_types:
            continue
        for field, allowed in config.link_properties(doc_type.code).items():
            if allowed:
                links.extend((item["id"], target) for target in _ids(item.get(field)))
    return links


def parents(items: list[dict], config: Any) -> dict[str, list[str]]:
    """``{item: [the items it depends on]}``: the edges `dependents` follows, reversed."""
    up: dict[str, list[str]] = {}
    for item, target in chain_links(items, config):
        up.setdefault(item, []).append(target)
    return up


def closest_same_type(item: dict, items: list[dict], excluded: set[str]) -> tuple[str, float] | None:
    """The item of the same type, outside ``excluded``, whose title and content read most like ``item``'s."""
    def text(it: dict) -> str:
        return " ".join(f"{it.get('title', '')} {it.get('content', '')}".lower().split())

    mine = text(item)
    best = None
    for other in items:
        if other["id"] == item["id"] or other["id"] in excluded or other.get("type") != item.get("type"):
            continue
        ratio = SequenceMatcher(None, mine, text(other)).ratio()
        if best is None or ratio > best[1]:
            best = (other["id"], ratio)
    return best


def dependents(items: list[dict], config: Any, changed: set[str], depth: int) -> dict[str, list[str]]:
    """``{dependent: [changed items it depends on]}`` within ``depth`` links of a changed item."""
    depends_on_me: dict[str, list[str]] = {}
    for item, target in chain_links(items, config):
        depends_on_me.setdefault(target, []).append(item)

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
