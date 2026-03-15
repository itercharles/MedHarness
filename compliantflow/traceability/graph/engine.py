"""NetworkX-based graph engine for traceability analysis."""

import networkx as nx
from typing import List, Set, Dict, Any, Optional, Tuple

from compliantflow.domain.schema import ProjectSchema


class GraphEngine:
    """
    NetworkX-based traceability graph.

    Items are stored as plain dicts (including ``all_linked_uids``).
    Config is a :class:`~compliantflow.domain.schema.ProjectSchema`.
    """

    def __init__(self, config: Optional[ProjectSchema] = None):
        self.graph = nx.DiGraph()
        self.config = config

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build_from_items(self, items: List[dict]):
        """Build graph from item dicts.

        Each dict must contain ``id`` and ``all_linked_uids``.
        Edge direction: child → parent (so ``successors`` = upstream parents).
        """
        self.graph.clear()

        for item in items:
            self.graph.add_node(item['id'], item=item)

        for item in items:
            for parent_uid in item.get('all_linked_uids') or []:
                if self.graph.has_node(parent_uid):
                    relation_label = "traces"

                    if self.config:
                        src_prefix = item['id'].split('-')[0] + '-'
                        tgt_prefix = parent_uid.split('-')[0] + '-'
                        src_type = self.config.get_type_by_prefix(src_prefix)
                        tgt_type = self.config.get_type_by_prefix(tgt_prefix)

                        if src_type and tgt_type:
                            # Use parent_type label if available (fallback: "traces")
                            pass  # relation_label stays "traces" — no labels in new schema

                    self.graph.add_edge(item['id'], parent_uid, type=relation_label)
                else:
                    print(f"Warning: Link target {parent_uid} not found for item {item['id']}")

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def find_orphans(self) -> List[Dict[str, Any]]:
        """Find items missing required parent links."""
        if not self.config:
            return []

        orphans = []

        for node_id in self.graph.nodes:
            item: dict = self.graph.nodes[node_id]['item']
            prefix = node_id.split('-')[0] + '-'

            item_type = self.config.get_type_by_prefix(prefix)
            if not item_type or not item_type.parent_types:
                continue

            parents = list(self.graph.successors(node_id))

            if not parents:
                orphans.append({
                    "uid": node_id,
                    "type": item_type.name,
                    "issue": f"Missing parent of type {item_type.parent_types}",
                    "required_parents": item_type.parent_types,
                })
                continue

            has_valid_parent = False
            for parent_uid in parents:
                parent_prefix = parent_uid.split('-')[0] + '-'
                parent_type = self.config.get_type_by_prefix(parent_prefix)
                if parent_type and parent_type.name in item_type.parent_types:
                    has_valid_parent = True
                    break

            if not has_valid_parent:
                orphans.append({
                    "uid": node_id,
                    "type": item_type.name,
                    "issue": f"No valid parent of type {item_type.parent_types}",
                    "required_parents": item_type.parent_types,
                })

        return orphans

    def calculate_coverage(self, type_name: str) -> Dict[str, Any]:
        """Calculate test coverage for an item type."""
        if not self.config:
            return {"coverage": 0.0, "total": 0, "covered": 0}

        item_type = self.config.get_type(type_name)
        if not item_type:
            return {"coverage": 0.0, "total": 0, "covered": 0}

        prefix = item_type.id_prefix
        reqs = [n for n in self.graph.nodes if n.startswith(prefix)]
        total = len(reqs)

        if total == 0:
            return {"coverage": 0.0, "total": 0, "covered": 0}

        covered = 0
        uncovered_items = []

        for req_uid in reqs:
            predecessors = list(self.graph.predecessors(req_uid))
            is_covered = any(
                (self.config.get_type_by_prefix(p.split('-')[0] + '-') or {})
                for p in predecessors
            )
            if predecessors:
                covered += 1
            else:
                uncovered_items.append(req_uid)

        coverage_pct = (covered / total) * 100

        return {
            "coverage": round(coverage_pct, 2),
            "total": total,
            "covered": covered,
            "uncovered": uncovered_items,
        }

    def get_downstream(self, uid: str) -> Set[str]:
        """Get all downstream (children) items."""
        if not self.graph.has_node(uid):
            return set()
        return set(nx.ancestors(self.graph, uid))

    def get_upstream(self, uid: str) -> Set[str]:
        """Get all upstream (parents) items."""
        if not self.graph.has_node(uid):
            return set()
        return set(nx.descendants(self.graph, uid))

    def get_impact_analysis(self, uid: str) -> Dict[str, Any]:
        if not self.graph.has_node(uid):
            return {"error": "Item not found"}
        downstream = self.get_downstream(uid)
        upstream = self.get_upstream(uid)
        return {
            "uid": uid,
            "downstream_count": len(downstream),
            "upstream_count": len(upstream),
            "downstream_items": list(downstream),
            "upstream_items": list(upstream),
            "total_impact": len(downstream) + len(upstream),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "orphans_count": len(self.find_orphans()),
        }

    def validate(self) -> Dict[str, Any]:
        issues = []

        orphans = self.find_orphans()
        if orphans:
            issues.append({"type": "orphans", "count": len(orphans), "items": orphans})

        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                issues.append({"type": "cycles", "count": len(cycles), "cycles": cycles})
        except Exception:
            pass

        isolated = list(nx.isolates(self.graph))
        if isolated:
            issues.append({"type": "isolated", "count": len(isolated), "items": isolated})

        return {"valid": len(issues) == 0, "issue_count": len(issues), "issues": issues}
