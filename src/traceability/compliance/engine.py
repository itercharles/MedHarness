"""Compliance Policy Engine."""

import yaml
from pathlib import Path
from typing import Dict, Any, Callable, Tuple, Optional
from dhf.models.compliance import PolicyGroup, ComplianceReport, PolicyResult, Policy

class PolicyEngine:
    """Executes compliance policies against the project graph."""
    
    def __init__(self, core_api): 
        self.core = core_api
        self.checks: Dict[str, Callable] = {
            'item_existence': self._check_item_existence,
            'file_existence': self._check_file_existence,
            'trace_coverage': self._check_trace_coverage,
            'attribute_presence': self._check_attribute_presence,
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
                # Manual policies pass if approved, fail otherwise?
                # For now, we report "Information" or pass if strictly manual.
                # If status is "rejected", it's a fail.
                passed = policy.status == 'approved'
                result = PolicyResult(
                    policy_id=policy.id,
                    passed=passed,
                    details=f"Manual Policy (Status: {policy.status})",
                    policy_text=policy.text,
                )
            else:
                if policy.status != 'approved':
                    result = PolicyResult(
                        policy_id=policy.id,
                        passed=False,
                        details=f"Policy not approved (Status: {policy.status})",
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
                                details=f"Check Exception: {str(e)}",
                                policy_text=policy.text,
                            )
                    else:
                        result = PolicyResult(
                            policy_id=policy.id,
                            passed=False,
                            details=f"Unknown check function: {check_name}",
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

    # --- Check Implementations ---

    def _check_item_existence(self, type_code: str) -> Tuple[bool, str, Optional[Dict]]:
        """Check if any items of the given type exist."""
        stats = self.core.graph.get_stats() # Assumes we can access graph or items
        # Alternatively, iterate nodes
        
        if not self.core.config:
             return False, "Config not loaded", None
             
        doc_type = self.core.config.get_doc_type(type_code)
        if not doc_type:
            return False, f"Document type {type_code} not defined in project config", None
            
        prefix = doc_type.prefix
        count = 0
        for node in self.core.graph.graph.nodes:
            if node.startswith(prefix):
                count += 1
                
        if count > 0:
            return True, f"Found {count} items of type {type_code}", {"count": count}
        else:
            return False, f"No items found of type {type_code}", {"count": 0}

    def _check_file_existence(self, path: str) -> Tuple[bool, str, Optional[Dict]]:
        """Check if a file exists relative to repo root."""
        full_path = self.core.repo_root / path
        if full_path.exists():
            return True, f"File exists: {path}", {"path": str(full_path)}
        else:
            return False, f"File missing: {path}", {"path": str(full_path)}

    def _check_trace_coverage(self, source_type: str, target_type: str, min_coverage: float = 1.0) -> Tuple[bool, str, Optional[Dict]]:
        """Check if source items trace to target items with sufficient coverage."""
        # Calculate coverage using GraphEngine logic
        # But GraphEngine.calculate_coverage() is slightly different (generic uncovered).
        # We need specific Source -> Target coverage.
        
        if not self.core.config:
             return False, "Config not loaded", None

        s_doc = self.core.config.get_doc_type(source_type)
        t_doc = self.core.config.get_doc_type(target_type)
        
        if not s_doc or not t_doc:
             return False, f"Invalid types: {source_type} -> {target_type}", None
             
        s_prefix = s_doc.prefix
        t_prefix = t_doc.prefix
        
        source_items = [n for n in self.core.graph.graph.nodes if n.startswith(s_prefix)]
        total = len(source_items)
        if total == 0:
            return False, f"No source items of type {source_type}", {"total": 0}
            
        covered = 0
        uncovered = []
        
        for uid in source_items:
            # Check upstream (parents) if target is parent (e.g. USN <- SYS)
            # OR Check downstream (children) if target is child (e.g. SYS <- VER)
            # This depends on direction.
            # Usually: Requirements (Parent) <- Tests (Child). Link is on Child.
            # Graph edge: Child -> Parent.
            # If checking if SYS covers USN: Check if USN has incoming edge from SYS.
            # If checking if VER covers SYS: Check if SYS has incoming edge from VER.
            
            # Use general approach: Check neighbors (both directions) for target prefix
            # More strictly:
            # If we want "SYS traces to USN": SYS links to USN. Edge SYS -> USN.
            # If we want "VER traces to SYS": VER links to SYS. Edge VER -> SYS.
            
            # The check says "System verification tests shall be documented and TRACE to requirements." (5.7.1)
            # This implies VER -> SYS exists.
            # BUT coverage is usually "Requirements are covered by tests".
            # The phrasing "Trace to architecture/requirements" (5.4.2)
            
            # Let's check if the source item is connected to ANY item of target type.
            is_connected = False
            
            # Outgoing (Source -> Target)
            for successor in self.core.graph.graph.successors(uid):
                if successor.startswith(t_prefix):
                    is_connected = True
                    break
            
            # Incoming (Target -> Source)
            if not is_connected:
                for predecessor in self.core.graph.graph.predecessors(uid):
                    if predecessor.startswith(t_prefix):
                        is_connected = True
                        break
                        
            if is_connected:
                covered += 1
            else:
                uncovered.append(uid)
                
        coverage = covered / total
        passed = coverage >= min_coverage
        
        details = f"Coverage {coverage:.1%} (Threshold {min_coverage:.1%}). {covered}/{total} covered."
        evidence = {
            "total": total,
            "covered": covered,
            "coverage": coverage,
            "uncovered_items": uncovered
        }
        
        return passed, details, evidence

    def _check_attribute_presence(self, type_code: Any, attribute: str) -> Tuple[bool, str, Optional[Dict]]:
        """Check if all items of given type(s) have a specific attribute."""
        if not self.core.config:
             return False, "Config not loaded", None

        # type_code can be a string or list of strings
        if isinstance(type_code, str):
            type_codes = [type_code]
        else:
            type_codes = type_code
            
        total_items = 0
        missing_items = []
        
        for code in type_codes:
            doc_type = self.core.config.get_doc_type(code)
            if not doc_type:
                continue
                
            prefix = doc_type.prefix
            
            # Find all nodes with this prefix
            nodes = [n for n in self.core.graph.graph.nodes if n.startswith(prefix)]
            for uid in nodes:
                total_items += 1
                item = self.core.graph.graph.nodes[uid].get('item')
                # Check item data (extra fields are in item.data usually, or just attributes of Item?)
                # Item model has fixed fields and __extra__? 
                # Pydantic v2: model_extra or just getattr
                
                has_attr = False
                if hasattr(item, attribute):
                     if getattr(item, attribute): # Check truthiness? Or just presence? Usually non-empty.
                         has_attr = True
                elif item and item.model_extra and attribute in item.model_extra:
                     if item.model_extra[attribute]:
                         has_attr = True
                         
                if not has_attr:
                    missing_items.append(uid)
                    
        if total_items == 0:
             return True, f"No items found for types {type_codes}", {"total": 0}
             
        passed = len(missing_items) == 0
        details = f"{total_items - len(missing_items)}/{total_items} items have attribute '{attribute}'."
        
        evidence = {
            "total": total_items,
            "missing": len(missing_items),
            "missing_items": missing_items
        }
        
        return passed, details, evidence
