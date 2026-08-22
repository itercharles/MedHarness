"""MedHarness product facade.

Single entry point for all business logic. Tests and CLI interact only
through this class. Accepts any DHFAdapter implementation.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Dict, Any

from medharness.graph import GraphEngine
from dhfkit.junit_parser import JUNIT_LINKS


class MedHarnessCore:
    """
    Core MedHarness library — read-only analysis facade.

    Provides traceability analysis, compliance checking, and graph
    queries over a DHF. All data mutations go through the DHFAdapter
    (and the utils CLI) directly.
    """

    def __init__(self, adapter):
        """
        Args:
            adapter: A DHFAdapter instance (e.g. LocalDHFAdapter from
                     dhfkit.local_adapter, or any custom implementation).
        """
        self._adapter = adapter
        self.graph = GraphEngine(get_type_info=self._adapter.get_item_type)

        self.refresh()

    def refresh(self):
        """Reload all items, rebuild graph, and recompute verification status."""
        raw_items = self._adapter.list_items()
        tc_items = self._adapter.get_test_result_items()
        self.graph.build_from_items(raw_items + tc_items)
        self._refresh_verification_status()

    # ------------------------------------------------------------------
    # Verification status (derived, in-memory only)
    # ------------------------------------------------------------------

    def _refresh_verification_status(self) -> None:
        # No early return on an empty store: verification_status is derived, so
        # "no evidence" must resolve to not_verified. Returning early left a
        # stale `verification_status: verified` in the YAML standing, and adding
        # one unrelated result then flipped the same item to not_verified.
        verifiable_ids = {
            node_id
            for node_id in self.graph.graph.nodes
            if (
                cfg := self._adapter.get_item_type(node_id.rsplit("-", 1)[0] + "-")
            ) and cfg.get("has_verification")
        }
        self._inject_verification_status(verifiable_ids)

    def inject_junit_results(self, junit_paths: List[Path]) -> None:
        """Inject verification status from JUnit XML files without storing to DHF.

        Reads ``JUNIT_LINKS`` properties directly from each testcase.
        TC IDs are not required. Results are held in-memory only.
        """
        # Build item_id → [(test_name, status)] from all provided JUnit files
        item_statuses: Dict[str, List[str]] = {}
        item_tests: Dict[str, List[Dict[str, str]]] = {}
        for path in junit_paths:
            tree = ET.parse(path)
            for testcase in tree.getroot().iter("testcase"):
                if testcase.find("skipped") is not None:
                    continue
                status = "FAIL" if (
                    testcase.find("failure") is not None
                    or testcase.find("error") is not None
                ) else "PASS"
                # Build a human-readable label: "suite › test name"
                tc_name = testcase.get("name", "")
                tc_class = testcase.get("classname", "")
                label = f"{tc_class} › {tc_name}" if tc_class else tc_name
                props_el = testcase.find("properties")
                if props_el is None:
                    continue
                for prop in props_el.findall("property"):
                    if prop.get("name") == JUNIT_LINKS:
                        for item_id in prop.get("value", "").split(","):
                            item_id = item_id.strip()
                            if item_id:
                                item_statuses.setdefault(item_id, []).append(status)
                                item_tests.setdefault(item_id, []).append(
                                    {"name": label, "status": status}
                                )

        verifiable_ids = {
            node_id
            for node_id in self.graph.graph.nodes
            if (
                cfg := self._adapter.get_item_type(node_id.rsplit("-", 1)[0] + "-")
            ) and cfg.get("has_verification")
        }
        # Merge only what a JUnit run cannot carry. Manual review records live
        # solely in the store and would be wiped by a wholesale replace; ordinary
        # automated results are superseded by the batch, so deleting a test
        # correctly drops the requirement back to not_verified rather than
        # leaving it verified by a stale stored PASS.
        stored = {
            tc_id: rec for tc_id, rec in self._adapter.get_all_test_results().items()
            if str(rec.get("review_status") or "").strip()
            or str(rec.get("reviewer") or "").strip()
        }
        for item_id in verifiable_ids:
            if not self.graph.graph.has_node(item_id):
                continue
            node_item = self.graph.graph.nodes[item_id]["item"]
            statuses = item_statuses.get(item_id, [])

            if statuses:
                vs = "failed" if "FAIL" in statuses else "verified"
                node_item["test_cases"] = item_tests.get(item_id, [])
            else:
                linked = [
                    rec for rec in stored.values()
                    if item_id in (rec.get("links") or [])
                    and rec.get("testing_status") in ("PASS", "FAIL")
                ]
                if not linked:
                    vs = "not_verified"
                elif any(r["testing_status"] == "FAIL" for r in linked):
                    vs = "failed"
                else:
                    vs = "verified"
                node_item.setdefault("test_cases", [])
            node_item["verification_status"] = vs

    def _inject_verification_status(self, item_ids: set) -> None:
        all_results = self._adapter.get_all_test_results()
        for item_id in item_ids:
            if not self.graph.graph.has_node(item_id):
                continue
            prefix = item_id.rsplit("-", 1)[0] + "-"
            doc_type_cfg = self._adapter.get_item_type(prefix)
            if not doc_type_cfg or not doc_type_cfg.get("has_verification"):
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
        prefix = item_id.rsplit("-", 1)[0] + "-"
        item_type = self._adapter.get_item_type(prefix)
        if item_type:
            return item_type.get("display_name", "OTHER")
        return "OTHER"

    def build_traceability_chains(self, path: List[str]) -> List[Dict[str, Any]]:
        """Build traceability chains for a multi-level path of doc-type codes."""
        all_items = self.get_all_items()
        chains: List[Dict[str, Any]] = []
        if not path:
            return chains

        prefix_map: Dict[str, str] = {}
        for it in self._adapter.list_item_types():
            prefix_map[it.get("code", "OTHER")] = it.get("prefix")

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

    def validate(self) -> Dict[str, Any]:
        return self.graph.validate()

    def check_coverage(self, pairs: List[tuple], strict: bool = True) -> Dict[str, Any]:
        """Check that every item at the parent level is covered by at least one child.

        Args:
            strict: When True (user-supplied pairs), an unconfigured document
                type is an error — the caller asked for something that does not
                exist. When False (implicit defaults spanning the full V-model),
                unconfigured layers are skipped, since a project is entitled to
                omit one.

        Args:
            pairs: List of (parent_type, child_type) tuples, e.g.
                   [("UC", "CRS"), ("CRS", "SYS"), ("SYS", "SYSARCH")]

        Returns:
            {"passed": bool, "results": [{"parent_type", "child_type", "passed",
             "total", "covered", "uncovered"}, ...]}

        Note: graph edges go child→parent, so children are G.predecessors(parent).
        """
        G = self.graph.graph
        results = []

        for parent_type, child_type in pairs:
            parent_prefix = self._get_prefix(parent_type)
            child_prefix = self._get_prefix(child_type)

            # An unknown code matches no items, which previously produced
            # total=0 and passed=True — so a typo in --coverage-pair greened
            # the gate instead of reporting itself.
            unknown = [
                code for code, prefix in (
                    (parent_type, parent_prefix), (child_type, child_prefix)
                ) if prefix is None
            ]
            if unknown and not strict:
                # Implicit defaults span the full V-model; a project that does
                # not configure a layer is not in error for omitting it.
                results.append({
                    "parent_type": parent_type,
                    "child_type": child_type,
                    "passed": True,
                    "total": 0,
                    "covered": 0,
                    "uncovered": [],
                    "skipped": f"not configured: {', '.join(unknown)}",
                })
                continue
            if unknown:
                results.append({
                    "parent_type": parent_type,
                    "child_type": child_type,
                    "passed": False,
                    "total": 0,
                    "covered": 0,
                    "uncovered": [],
                    "error": (
                        f"unknown document type(s): {', '.join(unknown)}. "
                        f"Configured: {', '.join(sorted(self._configured_codes()))}"
                    ),
                })
                continue

            parent_nodes = [n for n in G.nodes if n.startswith(parent_prefix)]
            uncovered = [
                n for n in parent_nodes
                if not any(p.startswith(child_prefix) for p in G.predecessors(n))
            ]
            results.append({
                "parent_type": parent_type,
                "child_type": child_type,
                "passed": len(uncovered) == 0,
                "total": len(parent_nodes),
                "covered": len(parent_nodes) - len(uncovered),
                "uncovered": uncovered,
            })

        return {
            "passed": all(r["passed"] for r in results),
            "results": results,
        }

    def _configured_codes(self) -> set:
        return {t.get("code") for t in self._adapter.list_item_types() if t.get("code")}

    def _get_prefix(self, type_code: str) -> Optional[str]:
        """Return the configured prefix for a doc-type code, or None if unknown.

        get_item_type() matches on *prefix*, so passing a code never hit and the
        method always fell through to ``code + "-"``. That is right only when the
        prefix happens to equal the code plus a dash — a project configuring
        ``TC-VER-`` for code ``TCVER`` got ``TCVER-`` and matched nothing.
        """
        for item_type in self._adapter.list_item_types():
            if item_type.get("code") == type_code:
                return item_type.get("prefix")
        return None

    def get_all_test_results(
        self,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return all stored test results, optionally filtered by status."""
        return self._adapter.get_all_test_results(status_filter)
