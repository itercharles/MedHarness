"""Workflow criteria checker for validating workflow transitions."""

from pathlib import Path
from typing import Dict, Any, List, Tuple
import yaml


class WorkflowCriteriaChecker:
    """
    Checks if items meet criteria for workflow transitions.
    
    Criteria are defined in DHF/config/workflow_criteria.yaml
    """
    
    def __init__(self, config_path: Path, core):
        """
        Initialize criteria checker.
        
        Args:
            config_path: Path to release_criteria.yaml
            core: CompliantFlowCore instance
        """
        self.config_path = Path(config_path)
        self.core = core
        self.criteria = self._load_criteria()
    
    def _load_criteria(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load criteria from YAML config."""
        if not self.config_path.exists():
            print(f"Warning: Release criteria config not found at {self.config_path}")
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading release criteria: {e}")
            return {}
    
    def check_transition_criteria(
        self,
        release: Dict[str, Any],
        from_status: str,
        to_status: str
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Check if release meets criteria for status transition.
        
        Args:
            release: Release data
            from_status: Current status
            to_status: Target status
            
        Returns:
            Tuple of (can_transition, criteria_results)
        """
        # Get criteria for this transition
        transition_key = f"{from_status}_to_{to_status}"
        criteria_list = self.criteria.get(transition_key, [])
        
        if not criteria_list:
            # No criteria defined, allow transition
            return True, []
        
        results = []
        all_required_pass = True
        
        for criterion in criteria_list:
            passed, message = self._check_criterion(release, criterion)
            
            result = {
                'id': criterion.get('id'),
                'name': criterion.get('name'),
                'description': criterion.get('description'),
                'check_type': criterion.get('check_type'),  # Add check_type to result
                'passed': passed,
                'message': message,
                'required': criterion.get('required', True),
                'severity': criterion.get('severity', 'error')
            }
            results.append(result)
            
            # Check if required criterion failed
            if not passed and criterion.get('required', True):
                all_required_pass = False
        
        return all_required_pass, results
    
    def _check_criterion(
        self,
        release: Dict[str, Any],
        criterion: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Check a single criterion.
        
        Returns:
            Tuple of (passed, message)
        """
        check_type = criterion.get('check_type')
        
        if check_type == 'change_requests_count':
            count = len(release.get('included_change_requests', []))
            min_count = criterion.get('min_count', 1)
            if count >= min_count:
                return True, f"{count} change request(s) included"
            return False, f"Only {count} change request(s), need at least {min_count}"
        
        elif check_type == 'field_not_empty':
            field = criterion.get('field')
            value = release.get(field)
            if value:
                return True, f"{field} is set"
            return False, f"{field} is not set"
        
        elif check_type == 'validation_status':
            if release.get('validation_passed'):
                return True, "Validation passed"
            return False, "Validation has not passed"
        
        elif check_type == 'change_requests_approved':
            report = release.get('validation_report', {})
            cr_report = report.get('change_requests', {})
            not_approved = cr_report.get('not_approved', 0)
            if not_approved == 0:
                approved = cr_report.get('approved', 0)
                return True, f"All {approved} change request(s) approved"
            return False, f"{not_approved} change request(s) not approved"
        
        elif check_type == 'requirement_coverage':
            report = release.get('validation_report', {})
            cov_report = report.get('requirement_coverage', {})
            percentage = cov_report.get('coverage_percentage', 0)
            min_pct = criterion.get('min_percentage', 100)
            if percentage >= min_pct:
                return True, f"{percentage:.1f}% coverage"
            return False, f"Only {percentage:.1f}% coverage, need {min_pct}%"
        
        elif check_type == 'test_status':
            report = release.get('validation_report', {})
            test_report = report.get('test_status', {})
            percentage = test_report.get('pass_percentage', 0)
            min_pct = criterion.get('min_percentage', 100)
            if percentage >= min_pct:
                return True, f"{percentage:.1f}% tests passing"
            return False, f"Only {percentage:.1f}% tests passing, need {min_pct}%"
        
        elif check_type == 'critical_defects':
            report = release.get('validation_report', {})
            defect_report = report.get('defect_status', {})
            critical_count = defect_report.get('critical_open', 0)
            max_count = criterion.get('max_count', 0)
            if critical_count <= max_count:
                return True, f"{critical_count} critical defect(s) open"
            return False, f"{critical_count} critical defect(s) open, max allowed is {max_count}"
        
        elif check_type == 'manual':
            # Manual checks require human verification
            criterion_id = criterion.get('id')
            manual_verifications = release.get('manual_verifications', {})
            
            if criterion_id in manual_verifications:
                verification = manual_verifications[criterion_id]
                verified_by = verification.get('verified_by', 'Unknown')
                return True, f"Verified by {verified_by}"
            else:
                return False, "Manual verification required"
        
        # Unknown check type
        return True, "Check type not implemented"
