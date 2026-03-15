"""Traceability mixin — graph/traceability operations."""

from typing import List, Dict, Any, Optional

from compliantflow.traceability.graph.analysis import generate_traceability_matrix


class _TraceabilityMixin:

    def get_doc_type_code(self, item_id: str) -> str:
        """Return the document type code for *item_id* based on configured prefixes."""
        if self.config:
            for doc_type in self.config.doc_types:
                if item_id.startswith(doc_type.prefix):
                    return doc_type.code
        return "OTHER"

    def get_vertical_view_items(
        self,
        focus_type: str,
        show_upstream: bool = True,
        show_downstream: bool = True,
    ) -> Dict[str, Dict]:
        """
        Return all items to display in the vertical traceability view.

        Args:
            focus_type:      Document type code to focus on (e.g. "SYS").
            show_upstream:   Include items whose links point TO the focus items.
            show_downstream: Include items that the focus items link TO.

        Returns:
            Dict mapping item_id → item_dict for every item that should appear
            in the view.  Focus items are always included.
        """
        all_items = self.get_all_items()
        focus_items = [i for i in all_items if self.get_doc_type_code(i["id"]) == focus_type]

        if not focus_items:
            return {}

        items_to_show: Dict[str, Dict] = {item["id"]: item for item in focus_items}

        if show_upstream:
            focus_ids = set(items_to_show)
            for item in all_items:
                if any(link in focus_ids for link in (item.get("all_linked_uids") or [])):
                    items_to_show[item["id"]] = item

        if show_downstream:
            item_map = {i["id"]: i for i in all_items}
            for focus_item in focus_items:
                for link in focus_item.get("all_linked_uids") or []:
                    if link in item_map:
                        items_to_show[link] = item_map[link]

        return items_to_show

    def build_traceability_chains(self, path: List[str]) -> List[Dict[str, Any]]:
        """
        Build traceability chains for a multi-level path of document type codes.

        Args:
            path: Ordered list of doc-type codes, e.g. ['CRS', 'SYS', 'SRS'].

        Returns:
            List of chain dicts (no UI formatting; no icon strings).
        """
        all_items = self.get_all_items()
        chains: List[Dict[str, Any]] = []

        if not path:
            return chains

        prefix_map: Dict[str, str] = {}
        if self.config:
            for dt in self.config.doc_types:
                prefix_map[dt.code] = dt.prefix

        def get_code(item_id: str) -> str:
            for code, prefix in prefix_map.items():
                if item_id.startswith(prefix):
                    return code
            return "OTHER"

        def _recurse(level: int, current_chain: Dict[str, Any]) -> None:
            if level >= len(path) - 1:
                chain_row: Dict[str, Any] = {}
                for code in path:
                    chain_row[code] = current_chain.get(code)
                chain_row["is_orphan"] = False
                chain_row["orphan_level"] = None
                chain_row["is_complete"] = len(current_chain) == len(path)
                chains.append(chain_row)
                return

            current_code = path[level]
            next_code = path[level + 1]
            current_item = current_chain[current_code]

            next_items = [
                i for i in all_items
                if get_code(i["id"]) == next_code
                and current_item["id"] in i.get("all_linked_uids", [])
            ]

            if next_items:
                for next_item in next_items:
                    new_chain = current_chain.copy()
                    new_chain[next_code] = next_item
                    _recurse(level + 1, new_chain)
            else:
                chain_row = {}
                for code in path:
                    chain_row[code] = current_chain.get(code)
                chain_row["is_orphan"] = False
                chain_row["orphan_level"] = None
                chain_row["is_complete"] = False
                chains.append(chain_row)

        start_code = path[0]
        start_items = [i for i in all_items if get_code(i["id"]) == start_code]
        for start_item in start_items:
            _recurse(0, {start_code: start_item})

        items_in_chains: Dict[str, set] = {code: set() for code in path}
        for chain in chains:
            for code in path:
                if chain.get(code) is not None:
                    items_in_chains[code].add(chain[code]["id"])

        for code in path:
            level_items = [i for i in all_items if get_code(i["id"]) == code]
            for item in level_items:
                if item["id"] not in items_in_chains[code]:
                    chain_row = {c: None for c in path}
                    chain_row[code] = item
                    chain_row["is_orphan"] = True
                    chain_row["orphan_level"] = code
                    chain_row["is_complete"] = False
                    chains.append(chain_row)

        return chains

    def get_traceability_matrix(self, source_type: str, target_type: str) -> List[Dict[str, Any]]:
        """
        Generate traceability matrix.

        Args:
            source_type: Source document type code (e.g., 'TC')
            target_type: Target document type code (e.g., 'SYS')

        Returns:
            List of traceability relationships
        """
        if not self.config:
            return []

        source_doc = self.config.get_doc_type(source_type)
        target_doc = self.config.get_doc_type(target_type)

        if not source_doc or not target_doc:
            return []

        return generate_traceability_matrix(
            self.graph,
            source_doc.prefix,
            target_doc.prefix,
        )

    def build_traceability_matrix(self, doc_types: List[str]) -> Dict[str, Any]:
        """
        Return a traceability matrix for an ordered list of document type codes.

        Each row represents one chain slot.  Orphaned items (not connected in
        the path) are included as rows where only their own column is filled.

        Args:
            doc_types: Ordered list of doc-type codes, e.g. ['CRS', 'SYS', 'TC-SYS'].
                       The order determines which items are considered "connected":
                       each level must link to the next.

        Returns:
            {
                "columns": ["CRS", "SYS", "TC-SYS"],
                "rows": [
                    {
                        "CRS": "CRS-001",      # item ID, or None when slot is empty
                        "SYS": "SYS-001",
                        "TC-SYS": "TC-SYS-001",
                        "is_orphan": False,    # True when only one column is filled
                        "orphan_type": None,   # doc-type code of the orphaned item
                        "is_complete": True    # True when every column is filled
                    },
                    ...
                ]
            }
        """
        chains = self.build_traceability_chains(doc_types)
        rows = []
        for chain in chains:
            row: Dict[str, Any] = {
                dt: (chain[dt]["id"] if chain.get(dt) is not None else None)
                for dt in doc_types
            }
            row["is_orphan"] = chain["is_orphan"]
            row["orphan_type"] = chain["orphan_level"]
            row["is_complete"] = chain["is_complete"]
            rows.append(row)
        return {"columns": list(doc_types), "rows": rows}

    def get_item_chain(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the full connected subgraph for a single item.

        Traverses all traceability links in both directions (upstream and
        downstream) transitively from *item_id*, then returns every reachable
        item together with its direct neighbours.

        Args:
            item_id: The item UID to start from.

        Returns:
            None if the item does not exist in the graph, otherwise:
            {
                "root": "SYS-001",
                "nodes": {
                    "SYS-001": {
                        "id":         "SYS-001",
                        "title":      "System shall...",
                        "status":     "approved",
                        "doc_type":   "SYS",
                        "upstream":   ["CRS-001"],        # direct parents only
                        "downstream": ["SRS-001", "SRS-002"]  # direct children only
                    },
                    "CRS-001": { ... },
                    "SRS-001": { ... },
                    "SRS-002": { ... }
                }
            }

        Notes:
            - ``upstream`` / ``downstream`` contain **direct** neighbours only;
              the full transitive closure is represented by the ``nodes`` dict.
            - Graph edges go child→parent, so ``G.successors`` = upstream parents
              and ``G.predecessors`` = downstream children.
        """
        import networkx as nx

        G = self.graph.graph
        if item_id not in G:
            return None

        # Collect every node reachable from item_id in either direction.
        connected: set = {item_id}
        connected.update(nx.descendants(G, item_id))  # business upstream (graph descendants)
        connected.update(nx.ancestors(G, item_id))    # business downstream (graph ancestors)

        nodes: Dict[str, Any] = {}
        for node_id in connected:
            item = self.get_item(node_id)
            if not item:
                continue
            nodes[node_id] = {
                "id":         node_id,
                "title":      item.get("title", ""),
                "status":     item.get("status"),
                "doc_type":   self.get_doc_type_code(node_id),
                # Direct neighbours only (edges: child→parent).
                "upstream":   [n for n in G.successors(node_id)   if n in connected],
                "downstream": [n for n in G.predecessors(node_id) if n in connected],
            }

        return {"root": item_id, "nodes": nodes}

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return self.graph.get_stats()

    def validate(self) -> Dict[str, Any]:
        """Validate the project."""
        return self.graph.validate()
