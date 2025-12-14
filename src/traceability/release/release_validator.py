"""Release validator for checking release readiness."""

from typing import Dict, Any, List, Tuple
from pathlib import Path

from ..models.release import Release


class ReleaseValidator:
    """
    Validates release readiness.
    
    Checks requirement coverage, test status, and defect status.
    """
    
    def __init__(self, core):
        """
        Initialize release validator.
        
        Args:
            core: CompliantFlowCore instance for accessing items and tests
        """
        self.core = core
    
    def validate_release(self, release: Release) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a release for approval.
        
        Args:
            release: Release to validate
            
        Returns:
            Tuple of (is_valid, validation_report)
        """
        report = {
            'change_requests': {},
            'requirement_coverage': {},
            'test_status': {},
            'defect_status': {},
            'overall_status': 'PASS',
            'issues': []
        }
        
        # Get all items affected by change requests
        affected_items = self._get_items_from_change_requests(release.included_change_requests)
        
        # Check change request status
        cr_ok, cr_report = self.check_change_requests(release.included_change_requests)
        report['change_requests'] = cr_report
        if not cr_ok:
            report['overall_status'] = 'FAIL'
            report['issues'].append("Some change requests are not approved")
        
        # Check requirement coverage for affected items
        coverage_ok, coverage_report = self.check_requirement_coverage(affected_items)
        report['requirement_coverage'] = coverage_report
        if not coverage_ok:
            report['overall_status'] = 'FAIL'
            report['issues'].append("Some requirements lack test coverage")
        
        # Check test status for affected items
        tests_ok, test_report = self.check_test_status(affected_items)
        report['test_status'] = test_report
        if not tests_ok:
            report['overall_status'] = 'FAIL'
            report['issues'].append("Some tests are failing")
        
        # Check defects
        defects_ok, defect_report = self.check_defects()
        report['defect_status'] = defect_report
        if not defects_ok:
            report['overall_status'] = 'WARN'
            report['issues'].append("Open critical defects exist")
        
        is_valid = report['overall_status'] == 'PASS'
        
        return is_valid, report
    
    def _get_items_from_change_requests(self, cr_ids: List[str]) -> List[str]:
        """
        Get all items affected by change requests.
        
        Args:
            cr_ids: List of change request IDs
            
        Returns:
            List of affected item IDs
        """
        all_items = self.core.get_all_items()
        affected_items = set()
        
        for cr_id in cr_ids:
            # Find the change request
            cr = next((item for item in all_items if item['id'] == cr_id), None)
            if cr and 'affected_items' in cr:
                affected_items.update(cr['affected_items'])
        
        return list(affected_items)
    
    def check_change_requests(self, cr_ids: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check that all change requests are approved.
        
        Args:
            cr_ids: List of change request IDs
            
        Returns:
            Tuple of (all_approved, cr_report)
        """
        try:
            all_crs = self.core.list_change_requests()
        except:
            return True, {'message': 'Change request tracking not available'}
        
        included_crs = [cr for cr in all_crs if cr['id'] in cr_ids]
        
        approved = []
        not_approved = []
        
        for cr in included_crs:
            if cr.get('status') == 'approved':
                approved.append(cr['id'])
            else:
                not_approved.append({'id': cr['id'], 'status': cr.get('status', 'unknown')})
        
        report = {
            'total_change_requests': len(cr_ids),
            'approved': len(approved),
            'not_approved': len(not_approved),
            'not_approved_details': not_approved
        }
        
        return len(not_approved) == 0, report
    
    def check_requirement_coverage(self, included_items: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check that all requirements have tests.
        
        Args:
            included_items: List of item IDs in the release
            
        Returns:
            Tuple of (all_covered, coverage_report)
        """
        all_items = self.core.get_all_items()
        
        # Filter to requirements in this release
        requirements = [
            item for item in all_items
            if item['id'] in included_items and item['id'].startswith(('SYS-', 'CRS-', 'SDS-'))
        ]
        
        # Check each requirement has tests
        uncovered = []
        covered = []
        
        for req in requirements:
            req_id = req['id']
            # Find tests that verify this requirement
            tests = [
                item for item in all_items
                if item['id'].startswith('TC-') and req_id in item.get('links', [])
            ]
            
            if tests:
                covered.append(req_id)
            else:
                uncovered.append(req_id)
        
        report = {
            'total_requirements': len(requirements),
            'covered': len(covered),
            'uncovered': len(uncovered),
            'uncovered_items': uncovered,
            'coverage_percentage': (len(covered) / len(requirements) * 100) if requirements else 100
        }
        
        return len(uncovered) == 0, report
    
    def check_test_status(self, included_items: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check that all tests pass.
        
        Args:
            included_items: List of item IDs in the release
            
        Returns:
            Tuple of (all_pass, test_report)
        """
        all_items = self.core.get_all_items()
        
        # Filter to tests in this release
        tests = [
            item for item in all_items
            if item['id'] in included_items and item['id'].startswith('TC-')
        ]
        
        passed = []
        failed = []
        not_run = []
        
        for test in tests:
            status = test.get('verification_status', 'NOT_RUN')
            if str(status) == 'VerificationStatus.PASS' or status == 'PASS':
                passed.append(test['id'])
            elif str(status) == 'VerificationStatus.FAIL' or status == 'FAIL':
                failed.append(test['id'])
            else:
                not_run.append(test['id'])
        
        report = {
            'total_tests': len(tests),
            'passed': len(passed),
            'failed': len(failed),
            'not_run': len(not_run),
            'failed_tests': failed,
            'not_run_tests': not_run,
            'pass_percentage': (len(passed) / len(tests) * 100) if tests else 100
        }
        
        return len(failed) == 0 and len(not_run) == 0, report
    
    def check_defects(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check defect status.
        
        Returns:
            Tuple of (no_critical_open, defect_report)
        """
        try:
            defects = self.core.list_defects()
        except:
            # If defect tracking not available, skip check
            return True, {'message': 'Defect tracking not available'}
        
        open_defects = [d for d in defects if d['status'] in ['open', 'investigating', 'reopened']]
        critical_open = [d for d in open_defects if d['severity'] == 'critical']
        
        report = {
            'total_defects': len(defects),
            'open_defects': len(open_defects),
            'critical_open': len(critical_open),
            'critical_open_ids': [d['id'] for d in critical_open]
        }
        
        # Warning if critical defects are open, but don't block release
        return len(critical_open) == 0, report
