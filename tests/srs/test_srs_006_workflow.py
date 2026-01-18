"""
Automated tests for SRS-006: Configuration-Driven Workflow Engine
Verifies: Software shall provide lifecycle management via CompliantFlowCore methods.
"""
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore


class TestSRS006_WorkflowMethods:
    """Tests for SRS-006: Workflow methods provided by CompliantFlowCore."""
    
    def test_get_initial_state(self, test_core):
        """Verify get_initial_state returns valid initial states for document types."""
        # Test for a known type like 'SYS'
        initial_state = test_core.get_initial_state('SYS')
        assert initial_state == 'draft', "SYS items should start in 'draft' state"
        
        # Test for another known type
        initial_state_crs = test_core.get_initial_state('CRS')
        assert initial_state_crs == 'draft', "CRS items should start in 'draft' state"

    def test_get_available_transitions(self, test_core):
        """Verify get_available_transitions returns correct next states."""
        # Case 1: Draft item
        draft_item = {'id': 'SYS-TEST-001', 'status': 'draft'}
        transitions = test_core.get_available_transitions(draft_item)
        target_states = [t.get('to_state') for t in transitions]
        
        # Should be able to go to 'approved' (defined in SYS lifecycle directly from draft)
        assert 'approved' in target_states, f"Draft SYS items should be able to move to 'approved', got {target_states}"
        
        # Case 2: Under review item moving to Approved
        under_review_item = {'id': 'SYS-TEST-002', 'status': 'under_review'}
        transitions = test_core.get_available_transitions(under_review_item)
        target_states = [t.get('to_state') for t in transitions]
        
        assert 'approved' in target_states, "Under review items should be able to move to 'approved'"

    def test_is_stable_state(self, test_core):
        """Verify get_state_info correctly identifies stable states."""
        # Retired/Closed should be stable based on project_config.yaml
        retired_info = test_core.get_state_info('retired')
        assert retired_info.get('is_stable') is True, "'retired' state should be stable"
        
        # Draft/Approved should not be stable (in current config approved is not stable)
        draft_info = test_core.get_state_info('draft')
        assert draft_info.get('is_stable') is False, "'draft' state should not be stable"
        
        approved_info = test_core.get_state_info('approved')
        # Note: In test fixture, approved IS marked stable
        assert approved_info.get('is_stable', False) is True, "'approved' state is stable in test fixture"

    def test_perform_transition(self, test_core):
        """Verify performing a valid state transition updates status."""
        # Create a new SYS item (Draft)
        item_data = {
            'id': 'SYS-TRANS-001',
            'title': 'Transition Test',
            'content': 'Testing transitions',
            'category': 'Functional'
        }
        # Note: create_item automatically sets initial status (draft for SYS)
        created = test_core.create_item(item_data)
        assert created['status'] == 'draft', "New SYS item should be draft"
        
        # Perform transition: Draft -> Approved
        # Based on config, this requires content & title (provided) + criteria
        # Note: Criteria validation logic is inside update_item or should be handled by caller
        # For this test, we assume core allows the update if valid
        
        # Update status to 'approved'
        update_data = {
            'status': 'approved',
            'approved_by': 'tester',
            'approved_date': '2025-01-01'
        }
        
        updated = test_core.update_item('SYS-TRANS-001', update_data)
        
        assert updated is not None, "Update should succeed"
        assert updated['status'] == 'approved', "Status should be updated to approved"
        assert updated['approved_by'] == 'tester', "Should update additional fields"

    def test_transitions_respect_global_config(self, test_core):
        """Verify that transitions respect the global configuration loaded by test_core."""
        # Just ensure that we are not getting empty transitions for valid states
        item = {'id': 'SYS-001', 'status': 'draft'}
        transitions = test_core.get_available_transitions(item)
        assert len(transitions) > 0, "Should find transitions from draft for initialized core"

    def test_invalid_state_handling(self, test_core):
        """Verify behavior when querying invalid states."""
        # Item with unknown status
        item = {'id': 'SYS-001', 'status': 'unknown_state'}
        transitions = test_core.get_available_transitions(item)
        # Should return empty list or defaults, but not crash
        assert isinstance(transitions, list)
        
        # Info for unknown state
        with pytest.raises(ValueError, match="not found"):
            test_core.get_state_info('non_existent_state')
