"""Compliance Policy Engine."""

import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Callable, Tuple, Optional
from compliantflow.domain.compliance import PolicyGroup, ComplianceReport, PolicyResult, Policy
from compliantflow.backends.llm import LLMBackend, get_default_backend

_SEMANTIC_MAX_CHARS = 12_000  # truncate very long documents before sending to LLM


class PolicyEngine:
    """Executes compliance policies against the project graph."""

    def __init__(self, core_api, root_dir: Optional[Path] = None, llm_backend: Optional[LLMBackend] = None):
        self.core = core_api
        self.root_dir = root_dir
        self._llm: Optional[LLMBackend] = llm_backend if llm_backend is not None else get_default_backend()
        self.checks: Dict[str, Callable] = {
            'item_existence': self._check_item_existence,
            'file_existence': self._check_file_existence,
            'document_content': self._check_document_content,
            'document_semantic': self._check_document_semantic,
            'trace_coverage': self._check_trace_coverage,
            'attribute_presence': self._check_attribute_presence,
            'attribute_value': self._check_attribute_value,
            'all_tests_passing': self._check_all_tests_passing,
            'verification_complete': self._check_verification_complete,
            'cr_git_evidence': self._check_cr_git_evidence,
            'no_open_defects': self._check_no_open_defects,
        }

    def load_policy_group(self, path: Path) -> Optional[PolicyGroup]:
        """Load a policy group from a YAML file."""
        if not path.exists():
            return None
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
            return PolicyGroup.model_validate(data)
        except Exception as e:
            print(f"Error loading policy group {path}: {e}")
            return None

    def check_compliance(self, group: PolicyGroup) -> ComplianceReport:
        """Run all automated checks for a policy group.

        ``document_semantic`` checks are batched by document: all policies
        that evaluate the same doc_id are sent to the LLM in a single request,
        each receiving its own pass/fail and rationale.
        """
        # Pre-compute all document_semantic results (one LLM call per document)
        semantic_results = self._run_semantic_batch(group.policies)

        results = []
        passed_count = 0

        for policy in group.policies:
            if not policy.automation:
                passed = policy.status == 'approved'
                details = f"Manual policy (status: {policy.status})"
                if policy.evidence_guidance:
                    details += f" — {policy.evidence_guidance}"
                result = PolicyResult(
                    policy_id=policy.id,
                    passed=passed,
                    details=details,
                    policy_text=policy.text,
                )
            else:
                if policy.status != 'approved':
                    result = PolicyResult(
                        policy_id=policy.id,
                        passed=False,
                        details=f"Policy not approved (status: {policy.status})",
                        policy_text=policy.text,
                    )
                elif policy.automation.check == 'document_semantic':
                    passed, details, evidence = semantic_results.get(
                        policy.id, (False, "Semantic batch did not return a result", {})
                    )
                    result = PolicyResult(
                        policy_id=policy.id,
                        passed=passed,
                        details=details,
                        evidence=evidence,
                        policy_text=policy.text,
                    )
                else:
                    check_name = policy.automation.check
                    params = policy.automation.params
                    check_func = self.checks.get(check_name)
                    if check_func:
                        try:
                            passed, details, evidence = check_func(**params)
                            result = PolicyResult(
                                policy_id=policy.id,
                                passed=passed,
                                details=details,
                                evidence=evidence,
                                policy_text=policy.text,
                            )
                        except Exception as e:
                            result = PolicyResult(
                                policy_id=policy.id,
                                passed=False,
                                details=f"Check error: {str(e)}",
                                policy_text=policy.text,
                            )
                    else:
                        result = PolicyResult(
                            policy_id=policy.id,
                            passed=False,
                            details=f"Unknown check: {check_name}",
                            policy_text=policy.text,
                        )

            if result.passed:
                passed_count += 1
            results.append(result)

        score = (passed_count / len(group.policies) * 100) if group.policies else 0.0

        return ComplianceReport(
            source_id=group.id,
            total_policies=len(group.policies),
            passed_policies=passed_count,
            results=results,
            score=round(score, 2)
        )

    def _run_semantic_batch(self, policies) -> Dict[str, Tuple[bool, str, Optional[Dict]]]:
        """Batch all document_semantic checks: one LLM call per unique doc_id.

        Returns a dict mapping policy_id → (passed, details, evidence).
        """
        # Group by doc_id
        from collections import defaultdict
        groups: Dict[str, list] = defaultdict(list)  # doc_id → [(policy_id, requirement)]
        for policy in policies:
            if policy.automation and policy.automation.check == 'document_semantic':
                if policy.status == 'approved':
                    groups[policy.automation.params['doc_id']].append(
                        (policy.id, policy.automation.params['requirement'])
                    )

        if not groups:
            return {}

        if self._llm is None:
            return {
                pid: (False, "No LLM backend configured", {"doc_id": doc_id})
                for doc_id, items in groups.items()
                for pid, _ in items
            }

        out: Dict[str, Tuple[bool, str, Optional[Dict]]] = {}

        for doc_id, items in groups.items():
            content = self.core._adapter.get_document(doc_id)
            if content is None:
                for pid, _ in items:
                    out[pid] = (False, f"Document not found: '{doc_id}'", {"doc_id": doc_id})
                continue

            truncated = len(content) > _SEMANTIC_MAX_CHARS
            content_for_llm = content[:_SEMANTIC_MAX_CHARS] + ("\n[... truncated ...]" if truncated else "")

            requirements_block = "\n".join(
                f'[{pid}] {req}' for pid, req in items
            )

            prompt = (
                "You are a medical device software compliance auditor evaluating documentation "
                "against IEC 62304.\n\n"
                f"DOCUMENT ({doc_id}):\n{content_for_llm}\n\n"
                "Evaluate whether the document satisfies EACH of the following requirements. "
                "Assess intent and substance, not just keyword presence.\n\n"
                f"REQUIREMENTS:\n{requirements_block}\n\n"
                "Respond with ONLY a valid JSON array — no markdown, no text outside the JSON. "
                "One object per requirement, in the same order:\n"
                '[{"policy_id": "<id>", "passed": true or false, "rationale": "one or two sentences"}, ...]'
            )

            try:
                text = self._llm.generate(prompt)
                if text.startswith("```"):
                    text = text.split("```")[1].lstrip("json").strip()
                items_result = json.loads(text)
                for entry in items_result:
                    pid = entry.get("policy_id", "")
                    passed = bool(entry.get("passed", False))
                    rationale = str(entry.get("rationale", ""))
                    details = f"{'PASS' if passed else 'FAIL'} (semantic) — {rationale}"
                    evidence = {"doc_id": doc_id, "rationale": rationale, "truncated": truncated}
                    out[pid] = (passed, details, evidence)
            except Exception as e:
                for pid, _ in items:
                    out[pid] = (False, f"Semantic check error: {e}", {"doc_id": doc_id})

        return out

    # --- Helpers ---

    def _get_prefix(self, type_code: str) -> Optional[str]:
        """Resolve ID prefix for a type code. Falls back to '{type_code}-' if not in config."""
        if self.core.config:
            item_type = self.core.config.get_type(type_code)
            if item_type:
                return item_type.id_prefix
        return f"{type_code}-"

    def _nodes_for_type(self, type_code: str):
        """Return all graph node IDs whose prefix matches type_code."""
        prefix = self._get_prefix(type_code)
        return [n for n in self.core.graph.graph.nodes if n.startswith(prefix)]

    # --- Check Implementations ---

    def _check_item_existence(self, type_code: str) -> Tuple[bool, str, Optional[Dict]]:
        """Check if any items of the given type exist."""
        nodes = self._nodes_for_type(type_code)
        count = len(nodes)
        if count > 0:
            return True, f"Found {count} item(s) of type '{type_code}'", {"count": count}
        return False, f"No items found of type '{type_code}'", {"count": 0}

    def _check_file_existence(self, path: str) -> Tuple[bool, str, Optional[Dict]]:
        """Check if a file exists relative to root_dir (DHF root)."""
        if self.root_dir is None:
            return False, "root_dir not set; cannot check file existence", {}
        full_path = self.root_dir / path
        if full_path.exists():
            return True, f"File exists: {path}", {"path": str(full_path)}
        return False, f"File missing: {path}", {"path": str(full_path)}

    def _check_document_content(
        self,
        doc_id: str,
        keywords: list,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Check that a DHF document exists and contains all specified keywords.

        Args:
            doc_id:   Logical document ID (filename stem, e.g. 'development_plan').
            keywords: List of strings that must all appear in the document (case-insensitive).
        """
        content = self.core._adapter.get_document(doc_id)
        if content is None:
            return False, f"Document not found: '{doc_id}'", {"doc_id": doc_id}

        content_lower = content.lower()
        missing = [kw for kw in keywords if kw.lower() not in content_lower]
        if missing:
            return (
                False,
                f"Document '{doc_id}' missing keywords: {missing}",
                {"doc_id": doc_id, "missing_keywords": missing, "found_keywords": [kw for kw in keywords if kw.lower() in content_lower]},
            )
        return (
            True,
            f"Document '{doc_id}' contains all required keywords",
            {"doc_id": doc_id, "keywords": keywords},
        )

    def _check_trace_coverage(
        self,
        source_type: str,
        target_type: str,
        min_coverage: float = 1.0,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Check that source items link to target items with sufficient coverage.

        Checks both edge directions (source→target and target→source) so it works
        regardless of which item holds the link.
        """
        s_prefix = self._get_prefix(source_type)
        t_prefix = self._get_prefix(target_type)

        source_items = self._nodes_for_type(source_type)
        total = len(source_items)
        if total == 0:
            return False, f"No items of type '{source_type}'", {"total": 0}

        covered = 0
        uncovered = []

        for uid in source_items:
            is_connected = any(
                s.startswith(t_prefix)
                for s in self.core.graph.graph.successors(uid)
            ) or any(
                p.startswith(t_prefix)
                for p in self.core.graph.graph.predecessors(uid)
            )
            if is_connected:
                covered += 1
            else:
                uncovered.append(uid)

        coverage = covered / total
        passed = coverage >= min_coverage
        details = f"Coverage {coverage:.1%} ({covered}/{total} items link to '{target_type}')"
        evidence = {
            "total": total,
            "covered": covered,
            "coverage": round(coverage, 4),
            "uncovered_items": uncovered,
        }
        return passed, details, evidence

    def _check_attribute_presence(
        self,
        type_code: Any,
        attribute: str,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Check if all items of given type(s) have a specific attribute set."""
        type_codes = [type_code] if isinstance(type_code, str) else type_code

        total_items = 0
        missing_items = []

        for code in type_codes:
            for uid in self._nodes_for_type(code):
                total_items += 1
                item = self.core.graph.graph.nodes[uid].get('item') or {}
                if not item.get(attribute):
                    missing_items.append(uid)

        if total_items == 0:
            return True, f"No items found for type(s) {type_codes}", {"total": 0}

        passed = len(missing_items) == 0
        details = (
            f"{total_items - len(missing_items)}/{total_items} items "
            f"have attribute '{attribute}'"
        )
        evidence = {
            "total": total_items,
            "missing": len(missing_items),
            "missing_items": missing_items,
        }
        return passed, details, evidence

    def _check_attribute_value(
        self,
        type_code: Any,
        attribute: str,
        expected_value: Any,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Check that all items of the given type have a specific attribute value."""
        type_codes = [type_code] if isinstance(type_code, str) else type_code

        total_items = 0
        non_matching = []

        for code in type_codes:
            for uid in self._nodes_for_type(code):
                total_items += 1
                item = self.core.graph.graph.nodes[uid].get('item') or {}
                if item.get(attribute) != expected_value:
                    non_matching.append({
                        "uid": uid,
                        "actual": item.get(attribute),
                    })

        if total_items == 0:
            return True, f"No items found for type(s) {type_codes}", {"total": 0}

        passed = len(non_matching) == 0
        matching = total_items - len(non_matching)
        details = (
            f"{matching}/{total_items} '{type_code}' items "
            f"have {attribute} == '{expected_value}'"
        )
        evidence = {
            "total": total_items,
            "matching": matching,
            "non_matching": non_matching,
        }
        return passed, details, evidence

    def _check_all_tests_passing(self, type_code: str) -> Tuple[bool, str, Optional[Dict]]:
        """Check that all test cases linked to items of type_code have PASS status.

        Looks at TC items in the graph that are connected (via any edge direction)
        to items of the given type.
        """
        target_nodes = set(self._nodes_for_type(type_code))
        if not target_nodes:
            return False, f"No items of type '{type_code}'", {"total": 0}

        tc_items = [
            n for n in self.core.graph.graph.nodes
            if n.startswith("TC-")
        ]

        linked_tcs: Dict[str, str] = {}  # tc_id → testing_status
        for tc_id in tc_items:
            neighbors = set(self.core.graph.graph.successors(tc_id)) | set(
                self.core.graph.graph.predecessors(tc_id)
            )
            if neighbors & target_nodes:
                item = self.core.graph.graph.nodes[tc_id].get('item') or {}
                linked_tcs[tc_id] = item.get('testing_status', 'UNKNOWN')

        if not linked_tcs:
            return False, f"No test cases linked to '{type_code}' items", {"total": 0}

        failing = [tc for tc, status in linked_tcs.items() if status != 'PASS']
        passed = len(failing) == 0
        total = len(linked_tcs)
        passing = total - len(failing)
        details = f"{passing}/{total} test cases passing for '{type_code}' items"
        evidence = {
            "total": total,
            "passing": passing,
            "failing": failing,
            "results": linked_tcs,
        }
        return passed, details, evidence

    def _check_document_semantic(
        self,
        doc_id: str,
        requirement: str,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Use an LLM to evaluate whether a document satisfies a natural-language requirement.

        Delegates to the configured LLM backend (see :attr:`_llm`).  When called
        directly (outside the batch path) it issues a single-policy batch so the
        prompt format stays consistent.

        Args:
            doc_id:      Logical document ID (filename stem, e.g. 'development_plan').
            requirement: Plain-English description of what the document must contain/demonstrate.
        """
        if self._llm is None:
            return False, "No LLM backend configured", {"doc_id": doc_id}

        content = self.core._adapter.get_document(doc_id)
        if content is None:
            return False, f"Document not found: '{doc_id}'", {"doc_id": doc_id}

        truncated = len(content) > _SEMANTIC_MAX_CHARS
        content_for_llm = content[:_SEMANTIC_MAX_CHARS] + ("\n[... truncated ...]" if truncated else "")

        prompt = (
            "You are a medical device software compliance auditor evaluating documentation "
            "against IEC 62304.\n\n"
            f"REQUIREMENT:\n{requirement}\n\n"
            f"DOCUMENT ({doc_id}):\n{content_for_llm}\n\n"
            "Does the document satisfy the requirement above? "
            "Evaluate intent and substance, not just keyword presence.\n\n"
            'Respond with ONLY valid JSON — no markdown, no explanation outside the JSON:\n'
            '{"passed": true or false, "rationale": "one or two sentences"}'
        )

        try:
            text = self._llm.generate(prompt)
            # Strip markdown code fences if the model adds them
            if text.startswith("```"):
                text = text.split("```")[1].lstrip("json").strip()
            result = json.loads(text)
            passed = bool(result.get("passed", False))
            rationale = str(result.get("rationale", ""))
            details = f"{'PASS' if passed else 'FAIL'} (semantic) — {rationale}"
            evidence = {"doc_id": doc_id, "requirement": requirement, "rationale": rationale, "truncated": truncated}
            return passed, details, evidence
        except Exception as e:
            return False, f"Semantic check error: {e}", {"doc_id": doc_id}

    def _check_cr_git_evidence(
        self,
        report_path: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Check that a CR-PR report JSON file contains at least one linked commit.

        The report JSON is read from:
          1. ``report_path`` parameter (if provided)
          2. ``COMPLIANTFLOW_CR_REPORT_PATH`` environment variable
          3. Falls back to FAIL if neither is set.

        The JSON is expected to have a ``commits`` list (non-empty = pass).

        Args:
            report_path: Optional explicit path to the CR report JSON artifact.
        """
        path_str = report_path or os.environ.get("COMPLIANTFLOW_CR_REPORT_PATH")
        if not path_str:
            return (
                False,
                "CR report path not set (no report_path param or COMPLIANTFLOW_CR_REPORT_PATH env var)",
                {},
            )
        try:
            with open(path_str, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return False, f"CR report file not found: {path_str}", {"path": path_str}
        except json.JSONDecodeError as exc:
            return False, f"CR report JSON parse error: {exc}", {"path": path_str}

        commits = data.get("commits", [])
        cr_id = data.get("cr_id", "")
        if commits:
            return (
                True,
                f"CR {cr_id!r} has {len(commits)} linked commit(s)",
                {"cr_id": cr_id, "commit_count": len(commits), "commits": commits},
            )
        return (
            False,
            f"CR {cr_id!r} has no linked commits in report",
            {"cr_id": cr_id, "commit_count": 0, "path": path_str},
        )

    def _check_no_open_defects(
        self,
        severity_threshold: list,
        block_states: Optional[list] = None,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Check that no DEF items with the given severities are in a blocking state.

        Args:
            severity_threshold: List of severity values that are blocking, e.g.
                ['Critical', 'High'].
            block_states: DEF lifecycle states that constitute an open defect.
                Defaults to ['open', 'in_progress'].
        """
        if block_states is None:
            block_states = ['open', 'in_progress']

        blocking = []
        for uid in self._nodes_for_type('DEF'):
            item = self.core.graph.graph.nodes[uid].get('item') or {}
            if item.get('status') in block_states and item.get('severity') in severity_threshold:
                blocking.append({
                    'uid': uid,
                    'severity': item.get('severity'),
                    'status': item.get('status'),
                    'title': item.get('title', ''),
                })

        passed = len(blocking) == 0
        if passed:
            details = (
                f"No open defects with severity in {severity_threshold}"
            )
        else:
            ids = ', '.join(b['uid'] for b in blocking)
            details = (
                f"{len(blocking)} open defect(s) with severity in "
                f"{severity_threshold}: {ids}"
            )
        evidence = {
            'severity_threshold': severity_threshold,
            'block_states': block_states,
            'blocking_defects': blocking,
        }
        return passed, details, evidence

    def _check_verification_complete(self, type_code: str) -> Tuple[bool, str, Optional[Dict]]:
        """Check that all items of type_code have verification_status == 'verified'."""
        nodes = self._nodes_for_type(type_code)
        if not nodes:
            return False, f"No items of type '{type_code}'", {"total": 0}

        not_verified = []
        statuses: Dict[str, str] = {}

        for uid in nodes:
            item = self.core.graph.graph.nodes[uid].get('item') or {}
            vs = item.get('verification_status', 'not_verified')
            statuses[uid] = vs
            if vs != 'verified':
                not_verified.append(uid)

        passed = len(not_verified) == 0
        total = len(nodes)
        verified_count = total - len(not_verified)
        details = f"{verified_count}/{total} '{type_code}' items fully verified"
        evidence = {
            "total": total,
            "verified": verified_count,
            "not_verified_items": not_verified,
            "statuses": statuses,
        }
        return passed, details, evidence
