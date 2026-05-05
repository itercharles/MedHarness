"""MedHarness product facade.

Single entry point for all business logic. Tests and CLI interact only
through this class. Accepts any DHFAdapter implementation.
"""

import networkx as nx
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
        all_results = self._adapter.get_all_test_results()
        if not all_results:
            return
        verifiable_ids = {
            node_id
            for node_id in self.graph.graph.nodes
            if (
                cfg := self._adapter.get_item_type(node_id.split("-")[0] + "-")
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
                cfg := self._adapter.get_item_type(node_id.split("-")[0] + "-")
            ) and cfg.get("has_verification")
        }
        for item_id in verifiable_ids:
            if not self.graph.graph.has_node(item_id):
                continue
            statuses = item_statuses.get(item_id, [])
            if not statuses:
                vs = "not_verified"
            elif "FAIL" in statuses:
                vs = "failed"
            else:
                vs = "verified"
            node_item = self.graph.graph.nodes[item_id]["item"]
            node_item["verification_status"] = vs
            node_item["test_cases"] = item_tests.get(item_id, [])

    def _inject_verification_status(self, item_ids: set) -> None:
        all_results = self._adapter.get_all_test_results()
        for item_id in item_ids:
            if not self.graph.graph.has_node(item_id):
                continue
            prefix = item_id.split("-")[0] + "-"
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

    def get_implementation_context(self, cr_id: str) -> Dict[str, Any]:
        """Return DHF-approved context for implementing a CR.

        This is a consumption package for product repositories. It does not
        perform impact analysis; DHF-owned analysis and audit evidence should
        already be represented in the approved CR/spec artifacts.
        """
        return {
            "cr": self._adapter.get_item(cr_id),
            "implementation_spec": self._adapter.get_document(f"{cr_id}-Spec"),
            "dhf_references": [cr_id, f"{cr_id}-Spec"],
        }

    # ------------------------------------------------------------------
    # Traceability
    # ------------------------------------------------------------------

    def _get_item_type_name(self, item_id: str) -> str:
        """Return the domain type name for item_id based on configured prefixes."""
        if True:  # always proceed via adapter
            prefix = item_id.split('-')[0] + '-'
            item_type = self._adapter.get_item_type(prefix)
            if item_type:
                return item_type.get("name", "OTHER")
        return "OTHER"

    def build_traceability_chains(self, path: List[str]) -> List[Dict[str, Any]]:
        """Build traceability chains for a multi-level path of doc-type codes."""
        all_items = self.get_all_items()
        chains: List[Dict[str, Any]] = []
        if not path:
            return chains

        prefix_map: Dict[str, str] = {}
        if True:  # always proceed via adapter
            for it in self._adapter.list_item_types():
                prefix_map[it.get("name", "OTHER")] = it.get("prefix")

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

    def validate_release(self, rel_id: str) -> Dict[str, Any]:
        """Evaluate whether a REL item meets all release criteria.

        Checks:
          1. REL item exists.
          2. All CRs in ``included_items`` are completed.
          3. No open DEF items exist (status in draft/open/in_progress).
          4. All SYS items have ``verification_status == 'verified'``.

        Returns a dict with keys:
          - ``passed`` (bool): True only when all checks pass.
          - ``rel_id`` (str): the REL item ID checked.
          - ``checks`` (list): per-check result dicts with
            ``name``, ``passed``, ``details``, and optionally ``items``.
        """
        checks: List[Dict[str, Any]] = []

        # 1. REL exists and is a REL item
        rel = self.get_item(rel_id)
        if rel is None:
            return {
                "passed": False,
                "rel_id": rel_id,
                "checks": [{"name": "rel_exists", "passed": False,
                             "details": f"REL item '{rel_id}' not found."}],
            }
        if not rel_id.startswith("REL-"):
            return {
                "passed": False,
                "rel_id": rel_id,
                "checks": [{"name": "rel_exists", "passed": False,
                             "details": f"'{rel_id}' is not a REL item. "
                                        f"validate release only accepts REL-* identifiers."}],
            }
        checks.append({"name": "rel_exists", "passed": True,
                        "details": f"REL item '{rel_id}' found (status: {rel.get('status', 'unknown')})."})

        # 2. CRs in included_items are all completed
        included_crs = rel.get("included_items") or []
        open_crs = []
        for cr_id in included_crs:
            cr = self.get_item(cr_id)
            if cr is None or cr.get("status") != "completed":
                actual = cr.get("status", "not found") if cr else "not found"
                open_crs.append({"id": cr_id, "status": actual})
        cr_check: Dict[str, Any] = {
            "name": "crs_completed",
            "passed": len(open_crs) == 0,
            "details": (
                f"All {len(included_crs)} included CR(s) are completed."
                if not open_crs
                else f"{len(open_crs)}/{len(included_crs)} included CR(s) are not completed."
            ),
        }
        if open_crs:
            cr_check["items"] = open_crs
        checks.append(cr_check)

        # 3. No open DEF items
        all_items = self.get_all_items()
        open_defs = self.get_open_defects()
        def_check: Dict[str, Any] = {
            "name": "no_open_defects",
            "passed": len(open_defs) == 0,
            "details": (
                "No open defects found."
                if not open_defs
                else f"{len(open_defs)} open defect(s) must be resolved before release."
            ),
        }
        if open_defs:
            def_check["items"] = open_defs
        checks.append(def_check)

        # 4. All SYS items are verified
        unverified_sys = [
            {"id": i["id"], "verification_status": i.get("verification_status", "not_verified"),
             "title": i.get("title", "")}
            for i in all_items
            if i["id"].startswith("SYS-") and i.get("verification_status") != "verified"
        ]
        sys_check: Dict[str, Any] = {
            "name": "sys_requirements_verified",
            "passed": len(unverified_sys) == 0,
            "details": (
                "All SYS requirements are verified."
                if not unverified_sys
                else f"{len(unverified_sys)} SYS requirement(s) are not verified."
            ),
        }
        if unverified_sys:
            sys_check["items"] = unverified_sys
        checks.append(sys_check)

        passed = all(c["passed"] for c in checks)
        return {"passed": passed, "rel_id": rel_id, "checks": checks}

    def check_coverage(self, pairs: List[tuple]) -> Dict[str, Any]:
        """Check that every item at the parent level is covered by at least one child.

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

    def _get_prefix(self, type_code: str) -> str:
        """Return the ID prefix for a type code."""
        if True:  # always proceed via adapter
            t = self._adapter.get_item_type(type_code)
            if t:
                return t.get("prefix")
        return f"{type_code}-"

    def get_context(
        self,
        governance_dir: Path,
        standard: Optional[str] = None,
        summary: bool = False,
    ) -> Dict[str, Any]:
        """Return a machine-readable context package for AI agent consumption.

        Assembles item type schema (fields, allowed values, ID prefixes),
        global lifecycle states, and compliance policy summaries from governance
        YAML files.  Designed as the pre-flight query an AI coding agent runs
        before generating or editing DHF content.

        Args:
            governance_dir: Directory containing governance ``*.yaml`` files.
            standard:       Filter compliance policies to this standard ID
                            (e.g. ``"IEC_62304"``).  ``None`` returns all.
            summary:        When True, policy entries contain only ``id``,
                            ``section``, and ``text`` — omitting check details.
        """
        # -- Item types -------------------------------------------------------
        item_types = []
        if True:  # always proceed via adapter
            for t in self._adapter.list_item_types():
                entry: Dict[str, Any] = {
                    "name": t.get("name", "OTHER"),
                    "id_prefix": t.get("prefix"),
                    "parent_types": t.get("parent_types", []),
                    "has_verification": t.get("has_verification"),
                    "fields": [f.model_dump() for f in t.fields],
                }
                item_types.append(entry)

        # -- Lifecycle states -------------------------------------------------
        lifecycle: Dict[str, Any] = {"states": []}
        if self._adapter.get_lifecycle_states():
            lifecycle["states"] = [
                {
                    "id": s.get("id"),
                    "label": s.get("label"),
                    "is_stable": s.get("is_stable", False),
                }
                for s in self._adapter.get_lifecycle_states()
            ]

        return {
            "item_types": item_types,
            "lifecycle": lifecycle,
        }

    def validate_draft(
        self,
        item_data: Dict[str, Any],
        type_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate a proposed DHF item against the doc-type field schema.

        Checks required fields and allowed values from the ProjectSchema
        (populated via CR-039 FieldSchema).  Graph-dependent checks such as
        trace_coverage and verification_complete are out of scope.

        Args:
            item_data:  The item dict to validate (e.g. parsed from a YAML file).
            type_name:  Override the type resolution.  When ``None`` the type is
                        inferred from the ``id`` prefix (e.g. ``"SYS-001"`` → ``"SYS"``).

        Returns:
            ``{"valid": bool, "type": str|None, "errors": [...], "warnings": [...]}``

            Each error/warning is a dict with ``field`` and ``message`` keys.
        """
        errors: List[Dict[str, str]] = []
        warnings: List[Dict[str, str]] = []

        # Resolve item type
        resolved_type: Optional[str] = type_name
        item_type_schema = None

        if resolved_type is None:
            item_id = item_data.get("id", "")
            if item_id and "-" in item_id:
                prefix = item_id.split("-")[0] + "-"
                item_type_schema = self._adapter.get_item_type(prefix)
                if item_type_schema:
                    resolved_type = item_type_schema.get("name", "OTHER")
        else:
            item_type_schema = self._adapter.get_item_type(resolved_type)

        if item_type_schema is None:
            if resolved_type:
                warnings.append({"field": "id", "message": f"Unknown type '{resolved_type}' — field constraints not checked"})
            else:
                warnings.append({"field": "id", "message": "Cannot determine item type — provide --type or an id field with a known prefix"})
            return {"valid": True, "type": resolved_type, "errors": errors, "warnings": warnings}

        # Validate against FieldSchema
        for field in item_type_schema.get("fields", []):
            value = item_data.get(field.get("name", "OTHER"))

            # Required check
            if field.get("required") and (value is None or value == "" or value == []):
                fname = field.get("name", "OTHER")
                errors.append({"field": fname, "message": "Required field '%s' is missing or empty" % fname})
                continue

            if value is None:
                continue

            # Allowed values check (select / multiselect / enum)
            field_opts = field.get("options", [])
            field_fmt = field.get("format", "")
            fname = field.get("name", "OTHER")
            if field_opts and field_fmt in ("select", "enum"):
                if value not in field_opts:
                    errors.append({
                        "field": fname,
                        "message": "Invalid value '%s' for '%s'. Allowed: %s" % (value, fname, field_opts),
                    })
            elif field_opts and field_fmt == "multiselect":
                values = value if isinstance(value, list) else [value]
                invalid = [v for v in values if v not in field_opts]
                if invalid:
                    errors.append({
                        "field": fname,
                        "message": "Invalid value(s) for '%s': %s. Allowed: %s" % (fname, invalid, field_opts),
                    })

        return {
            "valid": len(errors) == 0,
            "type": resolved_type,
            "errors": errors,
            "warnings": warnings,
        }

    def get_open_defects(self) -> List[Dict[str, Any]]:
        """Return all DEF items with an open status (draft/open/in_progress)."""
        _OPEN_STATUSES = {"draft", "open", "in_progress"}
        return [
            {"id": i["id"], "status": i.get("status", "unknown"), "title": i.get("title", "")}
            for i in self.get_all_items()
            if i["id"].startswith("DEF-") and i.get("status") in _OPEN_STATUSES
        ]

    def import_test_results(
        self,
        results,
        tester: str = "",
        run_id: str = "",
        run_url: str = "",
        commit_sha: str = "",
    ) -> Dict[str, Any]:
        """Import test results from parsed JUnit records.

        Delegates to the adapter and refreshes the graph so verification
        status is updated immediately.

        Args:
            results:    List of parsed test result objects (from junit_parser).
            tester:     Name of the agent/person who ran the tests.
            run_id:     CI run ID string.
            run_url:    URL to the CI run.
            commit_sha: Git commit SHA.

        Returns:
            dict with keys: imported, skipped, items_updated, failed_tcs.
        """
        imported = []
        skipped = 0
        failed_tcs = []

        for r in results:
            if r.testing_status == "SKIP":
                skipped += 1
                continue
            self._adapter.record_test_result(
                tc_id=r.id,
                testing_status=r.testing_status,
                tester=tester,
                run_id=run_id,
                run_url=run_url,
                commit_sha=commit_sha,
                notes=getattr(r, "error_message", "") or "",
                links=getattr(r, "links", None),
                title=getattr(r, "title", ""),
                reviewer=getattr(r, "reviewer", ""),
                review_date=getattr(r, "review_date", ""),
                review_status=getattr(r, "review_status", ""),
            )
            imported.append(r.id)
            if r.testing_status == "FAIL":
                failed_tcs.append(r.id)

        self.refresh()

        items_updated = []
        for tc_id in imported:
            result_rec = self._adapter.get_test_result(tc_id)
            if result_rec:
                for linked_id in result_rec.get("links") or []:
                    if linked_id not in items_updated:
                        items_updated.append(linked_id)

        return {
            "imported": len(imported),
            "skipped": skipped,
            "items_updated": items_updated,
            "failed_tcs": failed_tcs,
        }

    def get_test_result(self, tc_id: str) -> Optional[Dict[str, Any]]:
        """Return the stored test result for a TC, or None."""
        return self._adapter.get_test_result(tc_id)

    def get_all_test_results(
        self,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return all stored test results, optionally filtered by status."""
        return self._adapter.get_all_test_results(status_filter)
