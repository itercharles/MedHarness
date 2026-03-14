"""
Automated tests for SRS-006: Configuration-Driven Workflow Engine
Verifies: Software shall provide lifecycle management via CompliantFlowCore methods.

Only CR, REL, and DEF retain explicit lifecycle in production config.
"""
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from utils.local_adapter import LocalDHFAdapter
from compliantflow.core import CompliantFlowCore


class TestSRS006_WorkflowMethods:
    """Tests for SRS-006: Workflow methods provided by CompliantFlowCore."""

    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore with production config (read-only for tests)."""
        dhf_root = Path(__file__).parent.parent.parent
        return CompliantFlowCore(LocalDHFAdapter(dhf_root))

    def test_get_initial_state_for_cr(self, core):
        """CR items should start in 'draft' state."""
        initial_state = core.get_initial_state('CR')
        assert initial_state == 'draft', "CR items should start in 'draft' state"

    def test_get_initial_state_returns_none_for_requirement_types(self, core):
        """Requirement types (SYS, SRS, CRS) have no lifecycle — initial state is None."""
        assert core.get_initial_state('SYS') is None, \
            "SYS has no lifecycle; initial state should be None"
        assert core.get_initial_state('SRS') is None, \
            "SRS has no lifecycle; initial state should be None"
        assert core.get_initial_state('CRS') is None, \
            "CRS has no lifecycle; initial state should be None"

    def test_get_available_transitions_for_cr(self, core):
        """CR in draft state should offer transitions."""
        draft_cr = {'id': 'CR-TEST', 'status': 'draft'}
        transitions = core.get_available_transitions(draft_cr)
        target_states = [t.get('to_state') for t in transitions]
        assert len(transitions) > 0, "CR in draft should have available transitions"
        assert 'in_review' in target_states or 'approved' in target_states, \
            f"Expected workflow transition from draft for CR; got {target_states}"

    def test_get_available_transitions_empty_for_requirement_items(self, core):
        """Requirement items have no lifecycle — no transitions available."""
        sys_item = {'id': 'SYS-001'}
        transitions = core.get_available_transitions(sys_item)
        assert transitions == [], \
            f"SYS items should have no transitions; got {transitions}"

    def test_is_stable_state(self, core):
        """get_state_info correctly identifies stable states."""
        retired_info = core.get_state_info('retired')
        assert retired_info.get('is_stable') is True, "'retired' state should be stable"

        draft_info = core.get_state_info('draft')
        assert draft_info.get('is_stable') is False, "'draft' state should not be stable"

    def test_perform_cr_transition(self, test_core):
        """Performing a valid state transition on CR updates status.

        Uses the isolated test DHF fixture to avoid writing to the production DHF.
        """
        cr_data = {
            'id': 'CR-SRS006-TEST',
            'title': 'Transition Test CR',
            'description': 'Testing transitions',
            'justification': 'Test',
        }
        created = test_core.create_item(cr_data)
        assert created['status'] == 'draft', "New CR item should be draft"

        # Update status to 'in_review'
        update_data = {'status': 'in_review'}
        updated = test_core.update_item('CR-SRS006-TEST', update_data)

        assert updated is not None, "Update should succeed"
        assert updated['status'] == 'in_review', "Status should be updated to in_review"

    def test_transitions_respect_global_config(self, core):
        """Transitions respect the global configuration loaded by core."""
        cr_item = {'id': 'CR-001', 'status': 'draft'}
        transitions = core.get_available_transitions(cr_item)
        assert len(transitions) > 0, "Should find transitions from draft for CR"

    def test_invalid_state_handling(self, core):
        """Behavior when querying invalid states."""
        item = {'id': 'CR-001', 'status': 'unknown_state'}
        transitions = core.get_available_transitions(item)
        assert isinstance(transitions, list)

        with pytest.raises(ValueError, match="not found"):
            core.get_state_info('non_existent_state')
