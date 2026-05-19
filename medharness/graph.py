"""NetworkX-based graph engine and analysis utilities for traceability."""

import networkx as nx
from typing import List, Set, Dict, Any, Optional, Callable


class GraphEngine:
    """NetworkX-based traceability graph.

    Items are stored as plain dicts (including ``all_linked_uids``).
    ``get_type_info`` is a callable ``(prefix: str) -> dict | None`` that returns
    item type metadata from the adapter.
    """

    def __init__(self, get_type_info: Optional[Callable[[str], Optional[dict]]] = None):
        self.graph = nx.DiGraph()
        self._get_type_info = get_type_info

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build_from_items(self, items: List[dict]):
        """Edge direction: child → parent (successors = upstream parents)."""
        self.graph.clear()

        for item in items:
            self.graph.add_node(item['id'], item=item)

        for item in items:
            for parent_uid in item.get('all_linked_uids') or []:
                if self.graph.has_node(parent_uid):
                    self.graph.add_edge(item['id'], parent_uid)

    # ------------------------------------------------------------------
    # Orphans
    # ------------------------------------------------------------------

    def find_orphans(self) -> List[Dict[str, Any]]:
        orphans = []
        for n in self.graph.nodes:
            if self.graph.in_degree(n) == 0 and self.graph.out_degree(n) == 0:
                item = self.graph.nodes[n].get("item", {})
                orphans.append({
                    "uid": n,
                    "type": item.get("type", n.split("-")[0]),
                    "issue": f"Item {n} has no links to any other item",
                })
        return sorted(orphans, key=lambda o: o["uid"])

    # ------------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------------

    def calculate_coverage(self, parent_type: str, child_type: str) -> Dict[str, Any]:
        parent_prefix = f"{parent_type}-"
        child_prefix = f"{child_type}-"

        parents = [n for n in self.graph.nodes if n.startswith(parent_prefix)]
        if not parents:
            return {"parent_type": parent_type, "child_type": child_type,
                    "covered": 0, "total": 0, "coverage_pct": 100.0, "uncovered": []}

        covered = []
        uncovered = []
        for p in parents:
            preds = [n for n in self.graph.predecessors(p) if n.startswith(child_prefix)]
            if preds:
                covered.append(p)
            else:
                uncovered.append(p)

        total = len(parents)
        pct = round(len(covered) / total * 100, 1) if total else 100.0
        return {"parent_type": parent_type, "child_type": child_type,
                "covered": len(covered), "total": total, "coverage_pct": pct,
                "uncovered": uncovered}

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def node_counts(self) -> dict:
        counts: dict = {}
        for n in self.graph.nodes:
            prefix = n.split('-')[0] + '-'
            counts[prefix] = counts.get(prefix, 0) + 1
        return counts

    def stats(self) -> dict:
        return {"nodes": len(self.graph.nodes), "edges": len(self.graph.edges),
                "orphans": len(self.find_orphans()), "counts": self.node_counts()}

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def get_upstream(self, node_id: str) -> List[str]:
        if node_id not in self.graph:
            return []
        return list(nx.descendants(self.graph, node_id))

    def get_downstream(self, node_id: str) -> List[str]:
        if node_id not in self.graph:
            return []
        return list(nx.ancestors(self.graph, node_id))

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    def validate_for_cycles(self) -> List[List[str]]:
        try:
            cycles = list(nx.simple_cycles(self.graph))
        except nx.NetworkXNoCycle:
            cycles = []
        return cycles

    def validate(self) -> dict:
        orphans = self.find_orphans()
        cycles = self.validate_for_cycles()
        return {
            "valid": len(orphans) == 0 and len(cycles) == 0,
            "orphans": len(orphans),
            "cycles": len(cycles),
            "orphan_details": orphans,
            "cycle_details": cycles,
        }


