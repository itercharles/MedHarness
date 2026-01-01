"""
Tests for SRS-008: Configurable Workflow Engine

Verifies that the software enforces configurable lifecycle workflows for items,
validates state transitions, and executes transition criteria.

@links: SRS-008
"""
import pytest
from pathlib import Path


class TestWorkflowTransitions:
    """Test workflow state transitions.
    
    @links: SRS-008
    """
    
    def test_submit_requirement_for_review(self, test_core, draft_sys_item):
        """
        User transitions requirement from draft to under_review.
        
        @links: SRS-008
        """
        
        # Verify transition is available using core
        test_item = {'id': 'SYS-002', 'status': 'draft'}
        transitions = test_core.get_available_transitions(test_item)
        transition_targets = [t.get('to_state') for t in transitions]
        assert 'under_review' in transition_targets, \
            f"Expected 'under_review' in available transitions, got {transition_targets}"
        
        # Perform transition using draft item (SYS-002)
        item = test_core.get_item('SYS-002')
        item['status'] = 'under_review'
        
        result = test_core.update_item('SYS-002', item)
        
        # Verify new status
        assert result['status'] == 'under_review'
    
    def test_approve_requirement(self, test_core):
        """
        User approves a requirement under review.
        
        @links: SRS-008
        """
        
        # Create item under review
        item_data = {
            'id': 'SYS-APPROVE-TEST',
            'title': 'Test Requirement',
            'content': 'Test content',
            'status': 'under_review'
        }
        test_core.create_item(item_data)
        
        # Verify can approve using core
        test_item = {'id': 'SYS-APPROVE-TEST', 'status': 'under_review'}
        transitions = test_core.get_available_transitions(test_item)
        transition_targets = [t.get('to_state') for t in transitions]
        assert 'approved' in transition_targets, \
            f"Expected 'approved' in available transitions from under_review, got {transition_targets}"
        
        # Approve
        item = test_core.get_item('SYS-APPROVE-TEST')
        item['status'] = 'approved'
        item['approved_by'] = 'test_user'
        
        result = test_core.update_item('SYS-APPROVE-TEST', item)
        
        # Verify approval
        assert result['status'] == 'approved'
        assert result['approved_by'] == 'test_user'
    
    def test_reject_requirement(self, test_core):
        """
        User rejects a requirement, sending it back to draft.
        
        @links: SRS-008
        """
        # Create item under review
        item_data = {
            'id': 'SYS-REJECT-TEST',
            'title': 'Test Requirement',
            'content': 'Test content',
            'status': 'under_review'
        }
        test_core.create_item(item_data)
        
        # Reject (transition to draft)
        item = test_core.get_item('SYS-REJECT-TEST')
        item['status'] = 'draft'
        
        result = test_core.update_item('SYS-REJECT-TEST', item)
        
        # Verify back to draft
        assert result['status'] == 'draft'
    
    def test_prevent_invalid_transitions(self, test_core, draft_sys_item):
        """
        Workflow should only allow valid state transitions.
        
        @links: SRS-008
        """
        
        # Get available transitions from draft using core
        test_item = {'id': 'SYS-001', 'status': 'draft'}
        transitions = test_core.get_available_transitions(test_item)
        transition_targets = [t.get('to_state') for t in transitions]
        
        # Should be able to go to under_review
        assert 'under_review' in transition_targets
        
        # Should NOT be able to jump directly to approved from draft
        assert 'approved' not in transition_targets
    
    def test_stable_state_detection(self, test_core, approved_sys_item):
        """
        Workflow should correctly identify stable states.
        
        @links: SRS-008
        """
        
        # Get state info using core
        approved_state = test_core.get_state_info('approved')
        draft_state = test_core.get_state_info('draft')
        
        # Approved should be stable
        assert approved_state.get('is_stable', False) is True
        
        # Draft should not be stable
        assert draft_state.get('is_stable', False) is False


class TestChangeRequestWorkflow:
    """Test Change Request workflow scenarios.
    
    @links: SRS-008
    """
    
    def test_create_and_approve_cr(self, test_core):
        """
        Complete CR workflow: create -> review -> approve.
        
        @links: SRS-008
        """
        # 1. Create CR (status will be auto-initialized)
        cr_data = {
            'id': 'CR-WORKFLOW-001',
            'title': 'Test Change Request',
            'description': 'Test CR workflow',
            'justification': 'Testing'
        }
        
        created = test_core.create_item(cr_data)
        # Status should be auto-initialized to draft
        assert 'status' in created
        
        # 2. Move to under review
        cr = test_core.get_item('CR-WORKFLOW-001')
        cr['status'] = 'under_review'
        updated = test_core.update_item('CR-WORKFLOW-001', cr)
        assert updated['status'] == 'under_review'
        
        # 3. Approve
        cr = test_core.get_item('CR-WORKFLOW-001')
        cr['status'] = 'approved'
        cr['approved_by'] = 'test_user'
        final = test_core.update_item('CR-WORKFLOW-001', cr)
        
        assert final['status'] == 'approved'
        assert final['approved_by'] == 'test_user'
    
    def test_modify_stable_item_via_cr(self, test_core, approved_sys_item):
        """
        User modifies an approved (stable) requirement via Change Request.
        The item should reset to draft status.
        
        @links: SRS-008
        """
        # Create CR
        cr_data = {
            'id': 'CR-MODIFY-001',
            'title': 'Modify SYS-002',
            'description': 'Update approved requirement',
            'affected_items': ['SYS-001']
        }
        test_core.create_item(cr_data)
        
        # Modify stable item (first make it approved)
        item = test_core.get_item('SYS-001')
        item['status'] = 'approved'
        item['approved_by'] = 'test_user'
        test_core.update_item('SYS-001', item)
        
        # Now get it again to verify it's approved
        item = test_core.get_item('SYS-001')
        assert item['status'] == 'approved'
        
        item['content'] = 'Modified via CR'
        
        # Update with CR reference
        result = test_core.update_item('SYS-001', item, cr_id='CR-MODIFY-001')
        
        # Verify status reset
        assert result['status'] == 'draft'
        assert 'approved_by' not in result


class TestCRUDWorkflows:
    """Test CRUD (Create, Read, Update, Delete) workflows.
    
    @links: SRS-008
    """
    
    def test_create_sys_requirement(self, test_core):
        """
        User creates a new SYS requirement.
        
        @links: SRS-008
        """
        form_data = {
            'id': 'SYS-100',
            'title': 'New System Requirement',
            'content': 'The system shall validate user input',
            'category': 'Functional'
        }
        
        created = test_core.create_item(form_data)
        
        assert created is not None
        assert created['id'] == 'SYS-100'
        assert created['title'] == 'New System Requirement'
        
        # Verify item was persisted
        retrieved = test_core.get_item('SYS-100')
        assert retrieved is not None
        assert retrieved['id'] == 'SYS-100'
    
    def test_create_change_request(self, test_core):
        """
        User creates a new Change Request.
        
        @links: SRS-008
        """
        cr_data = {
            'id': 'CR-001',
            'title': 'Update system requirements',
            'description': 'Need to add new validation rules',
            'justification': 'Customer requirement change'
        }
        
        created = test_core.create_item(cr_data)
        
        assert created is not None
        assert created['id'] == 'CR-001'
        
        # Verify CR can be retrieved
        retrieved = test_core.get_item('CR-001')
        assert retrieved is not None
    
    def test_create_with_relationship(self, test_core, draft_sys_item):
        """
        User creates SRS requirement linked to parent SYS requirement.
        
        @links: SRS-008
        """
        srs_data = {
            'id': 'SRS-001',
            'title': 'Software Requirement',
            'content': 'Software shall implement validation',
            'derives_from': ['SYS-001']
        }
        
        created = test_core.create_item(srs_data)
        
        assert created is not None
        assert 'SYS-001' in created.get('derives_from', [])
        
        # Verify relationship exists in graph
        assert test_core.graph.graph.has_edge('SRS-001', 'SYS-001')
    
    def test_edit_draft_requirement(self, test_core, draft_sys_item):
        """
        User edits a draft requirement.
        
        @links: SRS-008
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
    
    def test_edit_approved_requirement_resets_status(self, test_core, approved_sys_item):
        """
        User edits an approved (stable) requirement.
        Status should reset to draft.
        
        @links: SRS-008
        """
        # First make SYS-001 approved
        item = test_core.get_item('SYS-001')
        item['status'] = 'approved'
        item['approved_by'] = 'test_user'
        test_core.update_item('SYS-001', item)
        
        # Now get it again to verify it's approved
        item = test_core.get_item('SYS-001')
        assert item['status'] == 'approved'
        assert 'approved_by' in item
        
        updated_data = item.copy()
        updated_data['content'] = 'Modified content'
        
        result = test_core.update_item('SYS-001', updated_data)
        
        # Verify status was reset to draft
        assert result['status'] == 'draft'
        assert 'approved_by' not in result
