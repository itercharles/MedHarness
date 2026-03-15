"""Compliance Policy Engine."""

import yaml
from pathlib import Path
from typing import Dict, Any, Callable, Tuple, Optional
from compliantflow.domain.compliance import PolicyGroup, ComplianceReport, PolicyResult, Policy

class PolicyEngine:
    """Executes compliance policies against the project graph."""

    def __init__(self, core_api):
        self.core = core_api
        self.checks: Dict[str, Callable] = {
            'item_existence': self._check_item_existence,
            'file_existence': self._check_file_existence,
            'trace_coverage': self._check_trace_coverage,
            'attribute_presence': self._check_attribute_presence,
            'all_tests_passing': self._check_all_tests_passing,
            'verification_complete': self._check_verification_complete,
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
        """Run all automated checks for a policy group."""
        results = []
        passed_count = 0

        for policy in group.policies:
            if not policy.automation:
                passed = policy.status == 'approved'
                result = PolicyResult(
                    policy_id=policy.id,
                    passed=passed,
                    details=f"Manual policy (status: {policy.status})",
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
        """Check if a file exists relative to repo root."""
        full_path = self.core.repo_root / path
        if full_path.exists():
            return True, f"File exists: {path}", {"path": str(full_path)}
        return False, f"File missing: {path}", {"path": str(full_path)}

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
