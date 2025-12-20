"""Sample automated tests for CompliantFlow.

Test function names should include the test case ID for mapping:
- test_TC_SYS_001_...
- test_tc_sys_001_...

Docstring format:
TC-XXX-YYY: Test Title

@links: REQ-001, REQ-002
@prerequisites: Description

Steps:
  1. Step one
  2. Step two

Expected Result:
  Description of expected outcome

Note: Status is not needed - tests are approved when merged to main branch.
"""

import pytest


def test_TC_SYS_001_core_initialization():
    """TC-SYS-001: Verify CompliantFlowCore Initialization
    
    @links: SYS-001
    @prerequisites: DHF directory with valid project_config.yaml
    
    Steps:
      1. Initialize CompliantFlowCore with DHF path
      2. Verify core object is created
      3. Verify config is loaded
      4. Verify doc_types are populated
    
    Expected Result:
      Core initializes successfully with loaded configuration
    """
    from pathlib import Path
    from traceability.compliant_flow_core import CompliantFlowCore
    
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    assert core is not None
    assert core.config is not None
    assert len(core.config.doc_types) > 0


def test_TC_SYS_002_load_all_items():
    """TC-SYS-002: Verify System Can Load All DHF Items
    
    @links: SYS-002
    @prerequisites: DHF directory with sample items
    
    Steps:
      1. Initialize CompliantFlowCore
      2. Call get_all_items()
      3. Verify items are returned
      4. Verify items have required fields
    
    Expected Result:
      All DHF items are loaded with id and title/content fields
    """
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
    """TC-SYS-003: Verify Traceability Matrices Configuration
    
    @links: SYS-003
    @prerequisites: project_config.yaml with traceability_matrices section
    
    Steps:
      1. Initialize CompliantFlowCore
      2. Access config.traceability_matrices
      3. Verify matrices are defined
      4. Verify matrix structure (name, path)
    
    Expected Result:
      Traceability matrices are configured with at least 2-level paths
    """
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


# Example of a skipped test (for demonstration)
@pytest.mark.skip(reason="Example of skipped test")
def test_TC_SYS_999_example_skip():
    """TC-SYS-999: Example of Skipped Test
    
    @links: SYS-999
    
    This test is intentionally skipped for demonstration purposes.
    """
    pass
