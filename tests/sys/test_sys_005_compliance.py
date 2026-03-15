"""
API tests for SYS-005: Compliance Assessment

Verifies: The system shall support compliance assessment against regulatory
policies and standards.

@links: SYS-005

This replaces browser-based tests with direct API testing.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.local_adapter import LocalDHFAdapter
from compliantflow.core import CompliantFlowCore


def test_TC_SYS_005_001_load_policy_groups(test_dhf_root, governance_dir):
    """
    TC-SYS-005-001: Load Policy Groups (API)

    @links: SYS-005
    @test_id: TC-SYS-005-001

    Verify system can load compliance policy groups.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    assert governance_dir.exists(), "Governance directory should exist"

    policy_files = list(governance_dir.glob("*.yaml"))
    assert len(policy_files) > 0, "Should have at least one policy group"

    policy_group = core.get_policy_group("IEC_62304", governance_dir)

    assert policy_group is not None, "Should load IEC_62304 policy group"
    assert 'title' in policy_group
    assert 'policies' in policy_group


def test_TC_SYS_005_002_view_policies(test_dhf_root, governance_dir):
    """
    TC-SYS-005-002: View Policy Definitions (API)

    @links: SYS-005
    @test_id: TC-SYS-005-002

    Verify system can retrieve policy definitions.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    policy_group = core.get_policy_group("IEC_62304", governance_dir)

    assert policy_group is not None
    assert 'policies' in policy_group

    policies = policy_group['policies']

    assert len(policies) > 0, "Policy group should have policies"

    for policy in policies:
        assert 'id' in policy, "Policy should have id"
        assert 'text' in policy, "Policy should have text/description"
        assert 'status' in policy, "Policy should have status"


def test_TC_SYS_005_003_run_compliance_check(test_dhf_root, governance_dir):
    """
    TC-SYS-005-003: Run Compliance Assessment (API)

    @links: SYS-005
    @test_id: TC-SYS-005-003

    Verify system can run compliance checks and produce results.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    report = core.check_compliance("IEC_62304", governance_dir)

    assert report is not None, "Should generate compliance report"
    assert 'score' in report, "Report should have compliance score"
    assert 'results' in report, "Report should have detailed results"

    score = report['score']
    assert 0 <= score <= 100, "Compliance score should be 0-100"

    results = report['results']
    assert len(results) > 0, "Should have policy check results"

    for result in results:
        assert 'policy_id' in result
        assert 'passed' in result
        assert 'details' in result
        assert 'policy_text' in result, "Result should include policy_text from backend"
        assert isinstance(result['policy_text'], str)
        assert len(result['policy_text']) > 0, "policy_text should not be empty"


def test_TC_SYS_005_004_compliance_score_calculation(test_dhf_root, governance_dir):
    """
    TC-SYS-005-004: Compliance Score Calculation (API)

    @links: SYS-005
    @test_id: TC-SYS-005-004

    Verify compliance score is calculated correctly.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    report = core.check_compliance("IEC_62304", governance_dir)

    results = report['results']
    total_policies = len(results)
    passed_policies = sum(1 for r in results if r['passed'])

    expected_score = (passed_policies / total_policies * 100) if total_policies > 0 else 0

    actual_score = report['score']
    assert abs(actual_score - expected_score) < 0.1, \
        f"Score should be {expected_score:.1f}, got {actual_score:.1f}"


def test_TC_SYS_005_005_policy_validation_details(test_dhf_root, governance_dir):
    """
    TC-SYS-005-005: Policy Validation Details (API)

    @links: SYS-005
    @test_id: TC-SYS-005-005

    Verify compliance check provides detailed validation information.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    report = core.check_compliance("IEC_62304", governance_dir)

    results = report['results']

    for result in results:
        assert result['policy_id'], "Should have policy ID"
        assert isinstance(result['passed'], bool), "Should have boolean pass/fail"
        assert result['details'], "Should have validation details"

        if 'evidence' in result and result['evidence'] is not None:
            assert isinstance(result['evidence'], dict)
