"""Test workflow transition user scenarios.

These tests verify that users can transition items through their lifecycle states
and that business rules are enforced correctly.
"""
import pytest
from src.traceability.workflow_engine import DynamicWorkflowEngine


class TestWorkflowTransitions:
    """Test workflow state transitions as users would perform them."""
    
    def test_user_submits_requirement_for_review(self, test_core, draft_sys_item):
        """User transitions requirement from draft to under_review."""
        # Get workflow engine
        doc_config = test_core.config.get_doc_type('SYS')
        workflow = DynamicWorkflowEngine(doc_config.model_dump(), test_core)
        
        # Verify transition is available
        transitions = workflow.get_available_transitions('draft')
        assert any(t['to'] == 'under_review' for t in transitions)
        
        # Perform transition
        item = test_core.get_item('SYS-001')
        item['status'] = 'under_review'
        
        result = test_core.update_item('SYS-001', item)
        
        # Verify new status
        assert result['status'] == 'under_review'
    
    def test_user_approves_requirement(self, test_core):
        """User approves a requirement under review."""
        # Create item under review
        item_data = {
            'id': 'SYS-APPROVE-TEST',
            'title': 'Test Requirement',
            'content': 'Test content',
            'status': 'under_review'
        }
        test_core.create_item(item_data)
        
        # Get workflow
        doc_config = test_core.config.get_doc_type('SYS')
        workflow = DynamicWorkflowEngine(doc_config.model_dump(), test_core)
        
        # Verify can approve
        transitions = workflow.get_available_transitions('under_review')
        assert any(t['to'] == 'approved' for t in transitions)
        
        # Approve
        item = test_core.get_item('SYS-APPROVE-TEST')
        item['status'] = 'approved'
        item['approved_by'] = 'test_user'
        
        result = test_core.update_item('SYS-APPROVE-TEST', item)
        
        # Verify approval
        assert result['status'] == 'approved'
        assert result['approved_by'] == 'test_user'
    
    def test_user_rejects_requirement(self, test_core):
        """User rejects a requirement, sending it back to draft."""
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


class TestChangeRequestWorkflow:
    """Test Change Request workflow scenarios."""
    
    def test_user_creates_and_approves_cr(self, test_core):
        """Complete CR workflow: create -> review -> approve."""
        # 1. Create CR
        cr_data = {
            'id': 'CR-WORKFLOW-001',
            'title': 'Test Change Request',
            'description': 'Test CR workflow',
            'justification': 'Testing',
            'status': 'submitted'
        }
        
        created = test_core.create_item(cr_data)
        assert created['status'] == 'submitted'  # Initial state
        
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
    
    def test_user_modifies_stable_item_via_cr(self, test_core, approved_sys_item):
        """
        User modifies an approved (stable) requirement via Change Request.
        The item should reset to draft status.
        """
        # Create CR
        cr_data = {
            'id': 'CR-MODIFY-001',
            'title': 'Modify SYS-002',
            'description': 'Update approved requirement',
            'affected_items': ['SYS-002']
        }
        test_core.create_item(cr_data)
        
        # Modify stable item
        item = test_core.get_item('SYS-002')
        assert item['status'] == 'approved'  # Verify it's stable
        
        item['content'] = 'Modified via CR'
        
        # Update with CR reference
        result = test_core.update_item('SYS-002', item, cr_id='CR-MODIFY-001')
        
        # Verify status reset
        assert result['status'] == 'draft', "Modifying stable item should reset status"
        assert 'approved_by' not in result, "Approval metadata should be cleared"


class TestWorkflowValidation:
    """Test that workflow rules are enforced."""
    
    def test_workflow_prevents_invalid_transitions(self, test_core, draft_sys_item):
        """Workflow should only allow valid state transitions."""
        doc_config = test_core.config.get_doc_type('SYS')
        workflow = DynamicWorkflowEngine(doc_config.model_dump(), test_core)
        
        # Get available transitions from draft
        transitions = workflow.get_available_transitions('draft')
        transition_targets = [t['to'] for t in transitions]
        
        # Should be able to go to under_review
        assert 'under_review' in transition_targets
        
        # Should NOT be able to jump directly to approved from draft
        # (must go through under_review first based on config)
        assert 'approved' not in transition_targets
    
    def test_stable_state_detection(self, test_core, approved_sys_item):
        """Workflow should correctly identify stable states."""
        doc_config = test_core.config.get_doc_type('SYS')
        workflow = DynamicWorkflowEngine(doc_config.model_dump(), test_core)
        
        # Get state info
        approved_state = workflow.get_state_info('approved')
        draft_state = workflow.get_state_info('draft')
        
        # Approved should be stable
        assert approved_state.get('is_stable', False) is True
        
        # Draft should not be stable
        assert draft_state.get('is_stable', False) is False
