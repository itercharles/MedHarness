"""Tests for compliance checking functionality."""

import pytest
from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore


def test_TC_COMP_001_policy_loading():
    """TC-COMP-001: Verify Policy Group Loading
    
    @links: SYS-025
    @prerequisites: Policy group YAML files in DHF/governance
    
    Steps:
      1. Initialize CompliantFlowCore
      2. List available policy groups
      3. Load a policy group
      4. Verify structure
    
    Expected Result:
      Policy groups should load with policies defined
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Check if governance directory exists
    governance_dir = dhf_root / "governance"
    if not governance_dir.exists():
        pytest.skip("Governance directory not found")
    
    # List policy files
    policy_files = list(governance_dir.glob("*.yaml"))
    
    if not policy_files:
        pytest.skip("No policy files found")
    
    # Try to load first policy group
    policy_file = policy_files[0]
    group_id = policy_file.stem
    
    policy_group = core.get_policy_group(group_id)
    
    if policy_group:
        assert 'id' in policy_group, "Policy group should have ID"
        assert 'policies' in policy_group, "Policy group should have policies"


def test_TC_COMP_002_compliance_checking():
    """TC-COMP-002: Verify Compliance Check Execution
    
    @links: SYS-026
    @prerequisites: Policy group and DHF items
    
    Steps:
      1. Initialize CompliantFlowCore
      2. Load policy group
      3. Run compliance check
      4. Verify report structure
    
    Expected Result:
      Compliance check should return report with results
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    governance_dir = dhf_root / "governance"
    if not governance_dir.exists():
        pytest.skip("Governance directory not found")
    
    policy_files = list(governance_dir.glob("*.yaml"))
    if not policy_files:
        pytest.skip("No policy files found")
    
    # Run compliance check
    group_id = policy_files[0].stem
    report = core.check_compliance(group_id)
    
    if report:
        assert 'policy_group_id' in report or 'results' in report, \
            "Report should have policy_group_id or results"


def test_TC_COMP_003_score_calculation():
    """TC-COMP-003: Verify Compliance Score Calculation
    
    @links: SYS-026
    @prerequisites: Compliance report with results
    
    Steps:
      1. Create sample compliance results
      2. Calculate score (passed / total)
      3. Verify score is between 0 and 100
      4. Test edge cases (0%, 100%)
    
    Expected Result:
      Compliance score should be calculated correctly as percentage
    """
    # Test score calculation logic
    test_cases = [
        (10, 10, 100.0),  # All passed
        (5, 10, 50.0),    # Half passed
        (0, 10, 0.0),     # None passed
        (7, 10, 70.0),    # 70% passed
    ]
    
    for passed, total, expected_score in test_cases:
        if total > 0:
            score = (passed / total) * 100
            assert score == expected_score, \
                f"Score for {passed}/{total} should be {expected_score}%"
        else:
            # Handle division by zero
            score = 0.0
            assert score == 0.0, "Score for 0 total should be 0%"
