"""CompliantFlow product facade.

Single entry point for all business logic. Tests and CLI interact only
through this class. Accepts any DHFAdapter implementation.
"""

import networkx as nx
from pathlib import Path
from typing import List, Optional, Dict, Any

from compliantflow.domain.schema import ProjectSchema
from compliantflow.graph import GraphEngine


class CompliantFlowCore:
    """
    Core CompliantFlow library — read-only analysis facade.

    Provides traceability analysis, compliance checking, and graph
    queries over a DHF. All data mutations go through the DHFAdapter
    (and the utils CLI) directly.
    """

    def __init__(self, adapter):
        """
        Args:
            adapter: A DHFAdapter instance (e.g. LocalDHFAdapter from
                     utils.local_adapter, or any custom implementation).
        """
        self._adapter = adapter
        self.config: ProjectSchema = adapter.get_project_config()
        self.graph = GraphEngine(config=self.config)

        self.refresh()

    def refresh(self):
        """Reload all items, rebuild graph, and recompute verification status."""
        raw_items = self._adapter.list_items()
        tc_items = self._adapter.get_test_result_items()
        self.graph.build_from_items(raw_items + tc_items)
        self._refresh_verification_status()

    def get_config(self) -> Optional[Dict[str, Any]]:
        """Return project configuration as a dict."""
        return self.config.model_dump() if self.config else None

    # ------------------------------------------------------------------
    # Verification status (derived, in-memory only)
    # ------------------------------------------------------------------

    def _refresh_verification_status(self) -> None:
        all_results = self._adapter.get_all_test_results()
        if not all_results:
            return
        verifiable_ids = {
            node_id
            for node_id in self.graph.graph.nodes
            if self.config and (
                cfg := self.config.get_type_by_prefix(node_id.split("-")[0] + "-")
            ) and cfg.has_verification
        }
        self._inject_verification_status(verifiable_ids)

    def _inject_verification_status(self, item_ids: set) -> None:
        all_results = self._adapter.get_all_test_results()
        for item_id in item_ids:
            if not self.graph.graph.has_node(item_id):
                continue
            prefix = item_id.split("-")[0] + "-"
            doc_type_cfg = self.config.get_type_by_prefix(prefix) if self.config else None
            if not doc_type_cfg or not doc_type_cfg.has_verification:
                continue
            linked = [
                rec for rec in all_results.values()
                if item_id in (rec.get("links") or [])
                and rec.get("testing_status") in ("PASS", "FAIL")
            ]
            if not linked:
                new_status = "not_verified"
            elif any(r["testing_status"] == "FAIL" for r in linked):
                new_status = "failed"
            else:
                new_status = "verified"
            self.graph.graph.nodes[item_id]["item"]["verification_status"] = new_status

    # ------------------------------------------------------------------
    # Item read access
    # ------------------------------------------------------------------

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Return all items (YAML + TC items) as dicts."""
        return [
            dict(self.graph.graph.nodes[node_id]['item'])
            for node_id in self.graph.graph.nodes
        ]

    def get_item(self, uid: str) -> Optional[Dict[str, Any]]:
        """Return a single item by UID, or None if not found."""
        if not self.graph.graph.has_node(uid):
            return None
        return dict(self.graph.graph.nodes[uid]['item'])

    # ------------------------------------------------------------------
    # Traceability
    # ------------------------------------------------------------------

    def _get_item_type_name(self, item_id: str) -> str:
        """Return the domain type name for item_id based on configured prefixes."""
        if self.config:
            prefix = item_id.split('-')[0] + '-'
            item_type = self.config.get_type_by_prefix(prefix)
            if item_type:
                return item_type.name
        return "OTHER"

    def build_traceability_chains(self, path: List[str]) -> List[Dict[str, Any]]:
        """Build traceability chains for a multi-level path of doc-type codes."""
        all_items = self.get_all_items()
        chains: List[Dict[str, Any]] = []
        if not path:
            return chains

        prefix_map: Dict[str, str] = {}
        if self.config:
            for it in self.config.item_types:
                prefix_map[it.name] = it.id_prefix

        def get_code(item_id: str) -> str:
            for name, prefix in prefix_map.items():
                if item_id.startswith(prefix):
                    return name
            return "OTHER"

        def _recurse(level: int, current_chain: Dict[str, Any]) -> None:
            if level >= len(path) - 1:
                chain_row: Dict[str, Any] = {code: current_chain.get(code) for code in path}
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
                chain_row = {code: current_chain.get(code) for code in path}
                chain_row["is_orphan"] = False
                chain_row["orphan_level"] = None
                chain_row["is_complete"] = False
                chains.append(chain_row)

        start_code = path[0]
        for start_item in [i for i in all_items if get_code(i["id"]) == start_code]:
            _recurse(0, {start_code: start_item})

        items_in_chains: Dict[str, set] = {code: set() for code in path}
        for chain in chains:
            for code in path:
                if chain.get(code) is not None:
                    items_in_chains[code].add(chain[code]["id"])

        for code in path:
            for item in [i for i in all_items if get_code(i["id"]) == code]:
                if item["id"] not in items_in_chains[code]:
                    chain_row = {c: None for c in path}
                    chain_row[code] = item
                    chain_row["is_orphan"] = True
                    chain_row["orphan_level"] = code
                    chain_row["is_complete"] = False
                    chains.append(chain_row)

        return chains

    def build_traceability_matrix(self, doc_types: List[str]) -> Dict[str, Any]:
        """
        Return a traceability matrix for an ordered list of doc-type codes.

        Returns:
            {
                "columns": ["CRS", "SYS", "TC-SYS"],
                "rows": [{"CRS": "CRS-001", "SYS": "SYS-001", ...,
                          "is_orphan": False, "orphan_type": None, "is_complete": True}]
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

        Returns:
            None if item not found, otherwise:
            {"root": "SYS-001", "nodes": {"SYS-001": {"id", "title", "status",
             "type", "upstream": [...], "downstream": [...]}, ...}}

        Note: graph edges go child→parent, so G.successors = upstream,
              G.predecessors = downstream.
        """
        G = self.graph.graph
        if item_id not in G:
            return None

        connected: set = {item_id}
        connected.update(nx.descendants(G, item_id))
        connected.update(nx.ancestors(G, item_id))

        nodes: Dict[str, Any] = {}
        for node_id in connected:
            item = self.get_item(node_id)
            if not item:
                continue
            nodes[node_id] = {
                "id":         node_id,
                "title":      item.get("title", ""),
                "status":     item.get("status"),
                "type":       self._get_item_type_name(node_id),
                "upstream":   [n for n in G.successors(node_id)   if n in connected],
                "downstream": [n for n in G.predecessors(node_id) if n in connected],
            }

        return {"root": item_id, "nodes": nodes}

    def validate(self) -> Dict[str, Any]:
        return self.graph.validate()

    # ------------------------------------------------------------------
    # Compliance
    # ------------------------------------------------------------------

    def get_policy_group(self, group_id: str, governance_dir: Path) -> Optional[Dict[str, Any]]:
        """Load a policy group without running checks."""
        from compliantflow.policy import PolicyEngine
        engine = PolicyEngine(self)
        path = Path(governance_dir) / f"{group_id}.yaml"
        group = engine.load_policy_group(path)
        return group.model_dump() if group else None

    def check_compliance(self, group_id: str, governance_dir: Path) -> Optional[Dict[str, Any]]:
        """Check compliance against a policy group and return the report."""
        from compliantflow.policy import PolicyEngine
        engine = PolicyEngine(self)
        path = Path(governance_dir) / f"{group_id}.yaml"
        group = engine.load_policy_group(path)
        if not group:
            return None
        return engine.check_compliance(group).model_dump()
