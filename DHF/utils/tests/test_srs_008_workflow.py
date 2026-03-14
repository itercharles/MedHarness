"""
Tests for SRS-008: Configurable Workflow Engine

Verifies that the software enforces configurable lifecycle workflows for items,
validates state transitions, and executes transition criteria.

Only CR, REL, and DEF retain explicit lifecycle; requirement items use the
GitOps approval model (no status field).
"""
import pytest
from pathlib import Path


class TestWorkflowTransitions:
    """Test workflow state transitions using CR (which retains explicit lifecycle).
    """

    def test_cr_draft_to_approved_transition_available(self, test_core):
        """
        CR item in draft state has 'approved' as an available transition.
        """
        cr = test_core.get_item('CR-001')
        assert cr is not None
        assert cr.get('status') == 'draft'

        transitions = test_core.get_available_transitions(cr)
        transition_targets = [t.get('to_state') for t in transitions]
        assert 'approved' in transition_targets, \
            f"Expected 'approved' in available transitions from draft, got {transition_targets}"

    def test_approve_cr(self, test_core):
        """
        User approves a CR.
        """
        cr_data = {
            'id': 'CR-098',
            'title': 'Test Change Request',
            'description': 'Test CR workflow',
            'justification': 'Testing',
        }
        test_core.create_item(cr_data)

        cr = test_core.get_item('CR-098')
        cr['status'] = 'approved'
        cr['approved_by'] = 'test_user'

        result = test_core.update_item('CR-098', cr)

        assert result['status'] == 'approved'
        assert result['approved_by'] == 'test_user'

    def test_stable_state_detection(self, test_core):
        """
        Workflow correctly identifies stable states from global lifecycle config.
        """
        approved_state = test_core.get_state_info('approved')
        draft_state = test_core.get_state_info('draft')

        # Approved is marked stable in the test fixture config
        assert approved_state.get('is_stable', False) is True

        # Draft is not stable
        assert draft_state.get('is_stable', False) is False

    def test_requirement_items_have_no_lifecycle(self, test_core):
        """
        Requirement items (SYS, SRS, etc.) have no lifecycle and no status.
        """
        sys_item = test_core.get_item('SYS-001')
        assert sys_item is not None
        assert 'status' not in sys_item, \
            "SYS items should not have a status field (GitOps model)"

        srs_item = test_core.get_item('SRS-001')
        assert srs_item is not None
        assert 'status' not in srs_item, \
            "SRS items should not have a status field (GitOps model)"

        # No transitions available for requirement items
        transitions = test_core.get_available_transitions(sys_item)
        assert transitions == [], \
            f"SYS items should have no transitions, got {transitions}"


class TestChangeRequestWorkflow:
    """Test Change Request workflow scenarios.
    """

    def test_create_and_approve_cr(self, test_core):
        """
        Complete CR workflow: create -> approve.
        """
        # 1. Create CR (status auto-initialized to draft)
        cr_data = {
            'id': 'CR-097',
            'title': 'Test Change Request',
            'description': 'Test CR workflow',
            'justification': 'Testing',
        }

        created = test_core.create_item(cr_data)
        assert 'status' in created
        assert created['status'] == 'draft'

        # 2. Approve
        cr = test_core.get_item('CR-097')
        cr['status'] = 'approved'
        cr['approved_by'] = 'test_user'
        final = test_core.update_item('CR-097', cr)

        assert final['status'] == 'approved'
        assert final['approved_by'] == 'test_user'

    def test_modify_stable_cr_resets_status(self, test_core):
        """
        Modifying an approved (stable) CR resets status to draft.
        """
        # Create and approve a CR (use simple numeric ID for correct prefix matching)
        cr_data = {
            'id': 'CR-099',
            'title': 'Stable CR',
            'description': 'Will be approved then modified',
            'justification': 'Testing stable-state reset',
        }
        test_core.create_item(cr_data)

        cr = test_core.get_item('CR-099')
        cr['status'] = 'approved'
        cr['approved_by'] = 'test_user'
        approved = test_core.update_item('CR-099', cr)
        assert approved['status'] == 'approved'

        # Now modify — status should reset to draft
        cr = test_core.get_item('CR-099')
        cr['description'] = 'Modified via test'
        result = test_core.update_item('CR-099', cr)

        assert result['status'] == 'draft'
        assert 'approved_by' not in result


class TestCRUDWorkflows:
    """Test CRUD (Create, Read, Update, Delete) workflows.
    """

    def test_create_sys_requirement(self, test_core):
        """
        User creates a new SYS requirement (no status field).
        """
        form_data = {
            'id': 'SYS-100',
            'title': 'New System Requirement',
            'content': 'The system shall validate user input',
            'category': 'Functional',
        }

        created = test_core.create_item(form_data)

        assert created is not None
        assert created['id'] == 'SYS-100'
        assert created['title'] == 'New System Requirement'
        # SYS has no lifecycle — no status field
        assert 'status' not in created

        # Verify item was persisted
        retrieved = test_core.get_item('SYS-100')
        assert retrieved is not None
        assert retrieved['id'] == 'SYS-100'

    def test_create_change_request(self, test_core):
        """
        User creates a new Change Request (gets draft status automatically).
        """
        cr_data = {
            'id': 'CR-096',
            'title': 'Update system requirements',
            'description': 'Need to add new validation rules',
            'justification': 'Customer requirement change',
        }

        created = test_core.create_item(cr_data)

        assert created is not None
        assert created['id'] == 'CR-096'
        assert created['status'] == 'draft'

        # Verify CR can be retrieved
        retrieved = test_core.get_item('CR-096')
        assert retrieved is not None

    def test_create_with_relationship(self, test_core):
        """
        User creates SRS requirement linked to parent SYS requirement.
        """
        srs_data = {
            'id': 'SRS-CRUD-001',
            'title': 'Software Requirement',
            'content': 'Software shall implement validation',
            'derives_from': ['SYS-001'],
        }

        created = test_core.create_item(srs_data)

        assert created is not None
        assert 'SYS-001' in created.get('derives_from', [])

        # Verify relationship exists in graph
        assert test_core.graph.graph.has_edge('SRS-CRUD-001', 'SYS-001')

    def test_edit_requirement(self, test_core):
        """
        User edits a requirement. No status involved.
        """
        item = test_core.get_item('SYS-001')

        updated_data = item.copy()
        updated_data['content'] = 'Updated: The system shall perform enhanced function X'
        updated_data['category'] = 'Performance'

        result = test_core.update_item('SYS-001', updated_data)

        assert result is not None
        assert result['content'] == 'Updated: The system shall perform enhanced function X'

        # Verify changes persisted
        retrieved = test_core.get_item('SYS-001')
        assert retrieved['content'] == 'Updated: The system shall perform enhanced function X'
