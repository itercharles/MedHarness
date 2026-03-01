"""Traceability mixin — graph/traceability operations."""

from typing import List, Dict, Any

from traceability.graph.analysis import generate_traceability_matrix


class _TraceabilityMixin:

    def get_item_neighbors(self, item_id: str) -> Dict[str, List[str]]:
        """
        Return the upstream and downstream neighbors of an item in the traceability graph.

        Args:
            item_id: The item UID to trace from.

        Returns:
            Dictionary with keys:
              "upstream"   – IDs of items that item_id derives from (business parents).
              "downstream" – IDs of items that derive from item_id (business children).
            Returns empty lists when the item is not in the graph.
        """
        import networkx as nx

        G = self.graph.graph
        if item_id not in G:
            return {"upstream": [], "downstream": []}

        upstream = list(nx.descendants(G, item_id))
        downstream = list(nx.ancestors(G, item_id))
        return {"upstream": upstream, "downstream": downstream}

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

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return self.graph.get_stats()

    def validate(self) -> Dict[str, Any]:
        """Validate the project."""
        return self.graph.validate()
