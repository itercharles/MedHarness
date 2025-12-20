"""Sample automated tests for CompliantFlow.

Test function names should include the test case ID for mapping:
- test_TC_SYS_001_...
- test_tc_sys_001_...
"""

import pytest


def test_TC_SYS_001_core_initialization():
    """TC-SYS-001: Verify CompliantFlowCore initializes correctly."""
    from pathlib import Path
    from traceability.compliant_flow_core import CompliantFlowCore
    
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    assert core is not None
    assert core.config is not None
    assert len(core.config.doc_types) > 0


def test_TC_SYS_002_load_all_items():
    """TC-SYS-002: Verify system can load all DHF items."""
    from pathlib import Path
    from traceability.compliant_flow_core import CompliantFlowCore
    
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    items = core.get_all_items()
    assert len(items) > 0
    
    # Verify items have required fields
    for item in items:
        assert 'id' in item
        assert 'title' in item or 'content' in item


def test_TC_SYS_003_traceability_matrix_config():
    """TC-SYS-003: Verify traceability matrices are configured."""
    from pathlib import Path
    from traceability.compliant_flow_core import CompliantFlowCore
    
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    assert hasattr(core.config, 'traceability_matrices')
    assert len(core.config.traceability_matrices) > 0
    
    # Verify matrix structure
    for matrix in core.config.traceability_matrices:
        assert hasattr(matrix, 'name')
        assert hasattr(matrix, 'path')
        assert len(matrix.path) >= 2  # At least 2 levels


# Example of a failing test (for demonstration)
@pytest.mark.skip(reason="Example of skipped test")
def test_TC_SYS_999_example_skip():
    """TC-SYS-999: Example of a skipped test."""
    pass
