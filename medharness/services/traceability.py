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
well-formed, and each backend answers them its own way; a Jira link cannot point
at a missing issue in the first place. Everything below needs the set.
"""

from __future__ import annotations

from typing import Any, Iterable, List

import networkx as nx

from dhfkit.item_type import ItemType
from dhfkit.traceability import _LINK_FIELDS, _prefix_of, find_dangling_links

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

    # None = not configured → use V-model defaults; [] = explicitly empty → no rules
    rules = config.required_traceability
    using_defaults = rules is None
    if using_defaults:
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
        if target_dt is None and using_defaults:
            # Target type not configured in this project — rule is not applicable.
            # Explicit config rules (using_defaults=False) are always enforced.
            continue
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
    suffix = " (V-model defaults; set required_traceability: [] in global.yaml to opt out)" if using_defaults else ""
    summary = f"{'PASS' if passed else 'FAIL'} — {len(failures)} required traceability failure(s){suffix}"

    return {
        "passed": passed,
        "failures": failures,
        "summary": summary,
        "using_vmodel_defaults": using_defaults,
    }

def build_risk_chain(items: list[dict], config: Any) -> list[dict]:
    """Build a per-RISK summary of linked RCMs and their implemented requirements.

    Returns a list of dicts:
        {
          "risk_id": str,
          "title": str,
          "rcms": [
            {"rcm_id": str, "title": str, "implements": [str]},
            ...
          ],
        }

    Returns an empty list when RISK or RCM doc types are not configured.
    """
    risk_dt = config.get_doc_type("RISK")
    rcm_dt = config.get_doc_type("RCM")
    if not risk_dt or not rcm_dt:
        return []

    risk_prefix = risk_dt.prefix
    rcm_prefix = rcm_dt.prefix

    risk_items = [it for it in items if it["id"].startswith(risk_prefix)]
    rcm_items = [it for it in items if it["id"].startswith(rcm_prefix)]

    chain = []
    for risk in sorted(risk_items, key=lambda x: x["id"]):
        rcms_for_risk = []
        for rcm in sorted(rcm_items, key=lambda x: x["id"]):
            mitigates = rcm.get("mitigates") or []
            if isinstance(mitigates, str):
                mitigates = [mitigates]
            if risk["id"] not in mitigates:
                continue
            implements = rcm.get("implements") or []
            if isinstance(implements, str):
                implements = [implements]
            rcms_for_risk.append({
                "rcm_id": rcm["id"],
                "title": rcm.get("title", ""),
                "implements": sorted(implements),
            })
        chain.append({
            "risk_id": risk["id"],
            "title": risk.get("title", ""),
            "rcms": rcms_for_risk,
        })
    return chain

def find_affected_risks(changed_ids: set[str], items: list[dict], config: Any) -> list[dict]:
    """Return RISK items potentially affected by a set of changed DHF item IDs.

    Traverses the link graph in reverse: changed item → RCMs that implement it
    → RISK items those RCMs mitigate.

    Args:
        changed_ids: Item IDs modified on the branch (any type).
        items: All DHF items with their field data.
        config: ProjectConfig used to identify RISK and RCM doc types.

    Returns:
        Sorted list of dicts: [{"risk_id": str, "title": str, "via_rcms": [str]}, ...]
        Empty when no RISK or RCM doc types are configured, or no overlap found.
    """
    risk_dt = config.get_doc_type("RISK")
    rcm_dt = config.get_doc_type("RCM")
    if not risk_dt or not rcm_dt:
        return []

    risk_prefix = risk_dt.prefix
    rcm_prefix = rcm_dt.prefix

    risk_items = {it["id"]: it for it in items if it["id"].startswith(risk_prefix)}

    affected: dict[str, set[str]] = {}  # risk_id → set of rcm_ids that implicate it
    for it in items:
        if not it["id"].startswith(rcm_prefix):
            continue
        implements = it.get("implements") or []
        if isinstance(implements, str):
            implements = [implements]
        if not any(uid in changed_ids for uid in implements):
            continue
        mitigates = it.get("mitigates") or []
        if isinstance(mitigates, str):
            mitigates = [mitigates]
        for risk_id in mitigates:
            if risk_id in risk_items:
                affected.setdefault(risk_id, set()).add(it["id"])

    return [
        {
            "risk_id": risk_id,
            "title": risk_items[risk_id].get("title", ""),
            "via_rcms": sorted(affected[risk_id]),
        }
        for risk_id in sorted(affected)
    ]

def build_module_map(items: list[dict], config: Any) -> list[dict]:
    """Build a MODULE → SWDD → SRS resolution map for AI implementation context.

    Scans all SWDD items for their ``module`` field (→ MODULE) and ``implements``
    field (→ SRS), then groups them by MODULE to produce a structured map that
    shows which software modules own which design items and requirements.

    Args:
        items: All DHF items with their field data.
        config: ProjectConfig used to identify MODULE and SWDD doc types.

    Returns:
        Sorted list of dicts:
        [
          {
            "module_id": str,
            "title": str,
            "swdds": [{"swdd_id": str, "title": str, "implements": [str]}, ...],
            "all_requirements": [str],   # deduplicated SRS IDs across all SWDDs
          },
          ...
        ]
        Empty when MODULE or SWDD doc types are not configured.
    """
    module_dt = config.get_doc_type("MODULE")
    swdd_dt = config.get_doc_type("SWDD")
    if not module_dt or not swdd_dt:
        return []

    module_prefix = module_dt.prefix
    swdd_prefix = swdd_dt.prefix

    module_items = {it["id"]: it for it in items if it["id"].startswith(module_prefix)}

    by_module: dict[str, list[dict]] = {}
    for it in items:
        if not it["id"].startswith(swdd_prefix):
            continue
        raw_module = it.get("module") or []
        if isinstance(raw_module, str):
            raw_module = [raw_module] if raw_module.strip() else []
        for mod_id in raw_module:
            mod_id = mod_id.strip()
            if mod_id:
                by_module.setdefault(mod_id, []).append(it)

    result = []
    for mod_id in sorted(by_module):
        mod_meta = module_items.get(mod_id, {})
        swdds = []
        all_reqs: list[str] = []
        for swdd in sorted(by_module[mod_id], key=lambda x: x["id"]):
            raw_impl = swdd.get("implements") or []
            if isinstance(raw_impl, str):
                raw_impl = [raw_impl] if raw_impl.strip() else []
            implements = [i.strip() for i in raw_impl if i.strip()]
            swdds.append({
                "swdd_id": swdd["id"],
                "title": swdd.get("title", ""),
                "implements": implements,
            })
            all_reqs.extend(r for r in implements if r not in all_reqs)
        result.append({
            "module_id": mod_id,
            "title": mod_meta.get("title", ""),
            "swdds": swdds,
            "all_requirements": all_reqs,
        })

    for mod_id in sorted(module_items):
        if mod_id not in by_module:
            result.append({
                "module_id": mod_id,
                "title": module_items[mod_id].get("title", ""),
                "swdds": [],
                "all_requirements": [],
            })

    return sorted(result, key=lambda x: x["module_id"])

def find_link_cycles(
    items: list[dict], link_fields: Iterable[str] | None = None
) -> list[list[str]]:
    """Find traceability links that form a cycle.

    The V-model is directed: a customer requirement gives rise to a system
    requirement, which gives rise to a software one. A cycle means two items
    each derive from the other, so neither has an origin and the matrix loses
    the direction that makes it a matrix.

    Returns each cycle as the list of IDs in it, rotated to start at its lowest
    ID so the same cycle reads the same way between runs.
    """
    fields = sorted(set(_LINK_FIELDS) | set(link_fields or ()))
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
          "risk_chain": [...],
          "summary": str,
        }
    """

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

    dangling = find_dangling_links(
        items, getattr(config, "relationship_fields", lambda: ())()
    )
    cycles = find_link_cycles(
        items, getattr(config, "relationship_fields", lambda: ())()
    )
    passed = (
        required_result["passed"]
        and not dangling
        and all(r["passed"] for r in coverage_results)
    )

    parts = []
    if not required_result["passed"]:
        parts.append(f"{len(required_result['failures'])} required failure(s)")
    if dangling:
        parts.append(f"{len(dangling)} dangling link(s)")
    uncovered_count = sum(len(r["uncovered"]) for r in coverage_results)
    if uncovered_count:
        parts.append(f"{uncovered_count} uncovered item(s)")
    summary = f"{'PASS' if passed else 'FAIL'} — " + ", ".join(parts) if parts else "All checks passed."

    return {
        "passed": passed,
        "required": required_result,
        "dangling": dangling,
        "cycles": cycles,
        "coverage": coverage_results,
        "risk_chain": build_risk_chain(items, config),
        "summary": summary,
    }

def format_traceability_report(result: dict) -> str:
    """Render a check_traceability result as a human-readable text report.

    Args:
        result: Dict returned by check_traceability().

    Returns:
        Multi-line string suitable for printing or writing to a file.
    """
    lines: list[str] = []
    lines.append("DHF Traceability Report")
    lines.append("=" * 40)
    lines.append("")

    status = "PASS" if result.get("passed") else "FAIL"
    lines.append(f"Status: {status}")
    lines.append(f"Summary: {result.get('summary', '')}")
    lines.append("")

    required = result.get("required", {})
    lines.append("Required Traceability")
    lines.append("-" * 40)
    failures = required.get("failures", [])
    if not failures:
        lines.append("  All required links satisfied.")
    else:
        for f in failures:
            lines.append(
                f"  FAIL  {f['id']} — {f['rule']} "
                f"(count={f['current_count']}, need ≥{f['min_count']})"
            )
    lines.append("")

    dangling = result.get("dangling", [])
    if dangling:
        lines.append("Dangling Links")
        lines.append("-" * 40)
        for d in dangling:
            lines.append(
                f"  FAIL  {d['source']}.{d['field']} → {d['target']} (target does not exist)"
            )
        lines.append("")

    coverage = result.get("coverage", [])
    lines.append("Coverage Matrix")
    lines.append("-" * 40)
    if not coverage:
        lines.append("  No coverage matrices configured.")
    else:
        col_w = max(len(c.get("matrix", "")) for c in coverage) + 2
        for c in coverage:
            matrix = c.get("matrix", "")
            covered = c.get("covered", 0)
            total = c.get("total", 0)
            status_icon = "PASS" if c.get("passed") else "FAIL"
            pct = f"{int(covered / total * 100)}%" if total else "n/a"
            line = f"  {status_icon}  {matrix:<{col_w}} {covered}/{total} ({pct})"
            lines.append(line)
            for uid in c.get("uncovered", []):
                lines.append(f"         ↳ uncovered: {uid}")
    lines.append("")

    risk_chain = result.get("risk_chain", [])
    if risk_chain:
        lines.append("Risk Chain")
        lines.append("-" * 40)
        for risk in risk_chain:
            lines.append(f"  {risk['risk_id']}  {risk['title']}")
            if not risk["rcms"]:
                lines.append("    (no RCMs linked)")
            else:
                for rcm in risk["rcms"]:
                    impl = ", ".join(rcm["implements"]) if rcm["implements"] else "—"
                    lines.append(f"    {rcm['rcm_id']}  {rcm['title']}")
                    lines.append(f"      implements: {impl}")
        lines.append("")

    return "\n".join(lines)


def analyse(adapter) -> dict:
    """Run the traceability analysis over everything a store holds.

    Takes an adapter rather than a path: the items are the store's to produce
    and the analysis is this project's to perform. `list_items()` already
    returns link fields and `all_linked_uids`, so nothing has to be reshaped —
    the adapter method this replaces did that reshaping *and* called the
    analysis, which is what put analysis inside the storage layer.
    """
    return check_traceability(adapter.list_items(), adapter.config)


def default_traceability_rules() -> List["RequiredTraceabilityRule"]:
    """Generate required traceability rules from ItemType V-model metadata."""
    from dhfkit.models.config import RequiredTraceabilityRule
    rules = []
    for member in ItemType:
        meta = member.value
        for link_field, target_code in meta.required_upstream:
            rules.append(RequiredTraceabilityRule(
                source_type=meta.code,
                direction="upstream",
                field=link_field,
                target_type=target_code,
                min_count=1,
            ))
    return rules

def default_coverage_chains() -> List["TraceabilityMatrix"]:
    """Generate traceability matrices from ItemType coverage_children metadata."""
    from dhfkit.models.config import TraceabilityMatrix
    matrices = []
    for member in ItemType:
        meta = member.value
        for child_code in meta.coverage_children:
            matrices.append(TraceabilityMatrix(
                name=f"{meta.code} → {child_code}",
                description=f"{meta.display_name} covered by {child_code}",
                path=[meta.code, child_code],
            ))
    return matrices