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
                    self.graph.add_edge(item['id'], parent_uid)

    # ------------------------------------------------------------------
    # Norm utilities moved into _normalize and used everywhere.
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(n: str) -> str:
        """Return the sorted, comma-joined representation of a node set."""
        return ", ".join(sorted(str(x) for x in n)) if isinstance(n, (list, set, tuple)) else str(n)

    # ------------------------------------------------------------------
    # Orphans
    # ------------------------------------------------------------------

    def find_orphans(self) -> List[Dict[str, Any]]:
        """Return node IDs that have no incoming or outgoing edges, with type info."""
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

    def find_orphans_by_root_types(self, root_type_prefixes: List[str]) -> List[Dict[str, Any]]:
        """Return orphans whose type is not in *root_type_prefixes*."""
        all_orphans = self.find_orphans()
        return [o for o in all_orphans
                if any(o["uid"].startswith(p) for p in root_type_prefixes)]


    # ------------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------------

    def calculate_coverage(self, parent_type: str, child_type: str) -> Dict[str, Any]:
        """Return coverage stats: how many *parent_type* items link to at least one *child_type*."""
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
        """Return {prefix: count} for all nodes."""
        counts: dict = {}
        for n in self.graph.nodes:
            prefix = n.split('-')[0] + '-'
            counts[prefix] = counts.get(prefix, 0) + 1
        return counts

    def stats(self) -> dict:
        """Return counts + orphan count."""
        return {"nodes": len(self.graph.nodes), "edges": len(self.graph.edges),
                "orphans": len(self.find_orphans()), "counts": self.node_counts()}

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def get_upstream(self, node_id: str) -> List[str]:
        """Return IDs upstream of *node_id* (following edge direction child→parent)."""
        if node_id not in self.graph:
            return []
        return list(nx.descendants(self.graph, node_id))

    def get_downstream(self, node_id: str) -> List[str]:
        """Return IDs downstream of *node_id* (reverse edge direction)."""
        if node_id not in self.graph:
            return []
        return list(nx.ancestors(self.graph, node_id))

    def get_item_chain(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Return upstream + downstream nodes with item data."""
        if node_id not in self.graph:
            return None
        upstream = self.get_upstream(node_id)
        downstream = self.get_downstream(node_id)
        nodes = {n: self.graph.nodes[n].get('item', {}) for n in [node_id] + upstream + downstream}
        return {"root": node_id, "nodes": nodes, "upstream": upstream, "downstream": downstream}

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    def validate_for_cycles(self) -> List[List[str]]:
        """Return any cycles found in the graph."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
        except nx.NetworkXNoCycle:
            cycles = []
        return cycles

    def validate(self) -> dict:
        """Run all graph validations and return a combined result dict."""
        orphans = self.find_orphans()
        cycles = self.validate_for_cycles()
        return {
            "valid": len(orphans) == 0 and len(cycles) == 0,
            "orphans": len(orphans),
            "cycles": len(cycles),
            "orphan_details": orphans,
            "cycle_details": cycles,
        }


def generate_traceability_matrix(
    graph: nx.DiGraph,
    columns: List[str],
    orphans: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a traceability matrix as a list of rows.

    Each row represents an item from the first column type. Columns map to linked items.
    """
    if not columns:
        return {"columns": [], "rows": []}

    first_col = columns[0]
    first_prefix = f"{first_col}-"
    root_ids = sorted(n for n in graph.nodes if n.startswith(first_prefix))

    rows = []
    for root in root_ids:
        row = {col: _linked_ids_for_column(graph, root, col, columns)
               for col in columns}
        row[first_col] = root
        rows.append(row)

    if orphans:
        for o in orphans:
            prefix = o.split('-')[0] + '-'
            if prefix in columns:
                rows.append({c: "" for c in columns})

    return {"columns": columns, "rows": rows}


def _linked_ids_for_column(graph: nx.DiGraph, root: str, col: str,
                           all_columns: List[str]) -> str:
    """Find linked IDs of type *col* reachable from *root*."""
    target_prefix = f"{col}-"
    root_col = root.split('-')[0]

    col_idx = all_columns.index(col) if col in all_columns else -1
    root_idx = all_columns.index(root_col) if root_col in all_columns else -1

    if col_idx == root_idx:
        return root

    if col_idx < root_idx:
        candidates = list(nx.descendants(graph, root))
    else:
        candidates = list(nx.ancestors(graph, root))

    matches = sorted(set(c for c in candidates if c.startswith(target_prefix)))
    return ", ".join(matches) if matches else ""


def find_gaps(grid: List[List[str]], columns: List[str]) -> List[Dict]:
    """Return rows from *grid* that have empty cells."""
    gaps = []
    for row in grid:
        for col in columns:
            if not row.get(col):
                gaps.append({"id": row.get(columns[0], ""), "missing_column": col})
    return gaps
