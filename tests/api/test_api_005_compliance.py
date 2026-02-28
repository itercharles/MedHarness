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

from traceability.compliant_flow_core import CompliantFlowCore


def test_TC_SYS_005_001_load_policy_groups(test_dhf_root):
    """
    TC-SYS-005-001: Load Policy Groups (API)

    @links: SYS-005
    @test_id: TC-SYS-005-001

    Verify system can load compliance policy groups.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get available policy groups
    governance_dir = core.repo_root / "governance"

    # Should have governance directory
    assert governance_dir.exists(), "Governance directory should exist"

    # Should have at least one policy group
    policy_files = list(governance_dir.glob("*.yaml"))
    assert len(policy_files) > 0, "Should have at least one policy group"

    # Load a policy group
    policy_group = core.get_policy_group("IEC_62304")

    assert policy_group is not None, "Should load IEC_62304 policy group"
    assert 'title' in policy_group
    assert 'policies' in policy_group


def test_TC_SYS_005_002_view_policies(test_dhf_root):
    """
    TC-SYS-005-002: View Policy Definitions (API)

    @links: SYS-005
    @test_id: TC-SYS-005-002

    Verify system can retrieve policy definitions.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Load policy group
    policy_group = core.get_policy_group("IEC_62304")

    assert policy_group is not None
    assert 'policies' in policy_group

    policies = policy_group['policies']

    # Should have multiple policies
    assert len(policies) > 0, "Policy group should have policies"

    # Each policy should have required fields
    for policy in policies:
        assert 'id' in policy, "Policy should have id"
        assert 'text' in policy, "Policy should have text/description"
        assert 'status' in policy, "Policy should have status"


def test_TC_SYS_005_003_run_compliance_check(test_dhf_root):
    """
    TC-SYS-005-003: Run Compliance Assessment (API)

    @links: SYS-005
    @test_id: TC-SYS-005-003

    Verify system can run compliance checks and produce results.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Run compliance check
    report = core.check_compliance("IEC_62304")

    # Verify report structure
    assert report is not None, "Should generate compliance report"
    assert 'score' in report, "Report should have compliance score"
    assert 'results' in report, "Report should have detailed results"

    # Verify score is valid
    score = report['score']
    assert 0 <= score <= 100, "Compliance score should be 0-100"

    # Verify results contain policy checks
    results = report['results']
    assert len(results) > 0, "Should have policy check results"

    # Each result should have required fields
    for result in results:
        assert 'policy_id' in result
        assert 'passed' in result
        assert 'details' in result


def test_TC_SYS_005_004_compliance_score_calculation(test_dhf_root):
    """
    TC-SYS-005-004: Compliance Score Calculation (API)

    @links: SYS-005
    @test_id: TC-SYS-005-004

    Verify compliance score is calculated correctly.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Run compliance check
    report = core.check_compliance("IEC_62304")

    # Count passed/failed policies
    results = report['results']
    total_policies = len(results)
    passed_policies = sum(1 for r in results if r['passed'])

    # Calculate expected score
    expected_score = (passed_policies / total_policies * 100) if total_policies > 0 else 0

    # Verify score matches calculation
    actual_score = report['score']
    assert abs(actual_score - expected_score) < 0.1, \
        f"Score should be {expected_score:.1f}, got {actual_score:.1f}"


def test_TC_SYS_005_005_policy_validation_details(test_dhf_root):
    """
    TC-SYS-005-005: Policy Validation Details (API)

    @links: SYS-005
    @test_id: TC-SYS-005-005

    Verify compliance check provides detailed validation information.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Run compliance check
    report = core.check_compliance("IEC_62304")

    # Check that results have detailed information
    results = report['results']

    for result in results:
        # Should have policy ID
        assert result['policy_id'], "Should have policy ID"

        # Should have pass/fail status
        assert isinstance(result['passed'], bool), "Should have boolean pass/fail"

        # Should have details explaining the result
        assert result['details'], "Should have validation details"

        # May have evidence
        if 'evidence' in result:
            assert result['evidence'] is not None
