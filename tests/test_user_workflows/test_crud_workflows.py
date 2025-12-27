"""Test CRUD (Create, Read, Update, Delete) user workflows.

These tests simulate actual user interactions through the UI,
ensuring that the complete workflow from UI action to data persistence works correctly.

Traceability: Tests are marked with @pytest.mark.verifies() to link to requirements.
"""
import pytest
from pathlib import Path


class TestCreateWorkflows:
    """Test item creation workflows as a user would perform them."""
    
    @pytest.mark.verifies("SYS-012")
    def test_user_creates_sys_requirement(self, test_core):
        """
        User creates a new SYS requirement through the create form.
        
        Verifies: SYS-012 (Requirements management)
        Test Type: Automated
        """
        # Simulate UI form data (what universal_page_template.py collects)
        form_data = {
            'id': 'SYS-100',
            'title': 'New System Requirement',
            'content': 'The system shall validate user input',
            'category': 'Functional'
        }
        
        # This is what the UI does - should use create_item (not update_item)
        created = test_core.create_item(form_data)
        
        # Verify creation succeeded
        assert created is not None, "create_item should return the created item"
        assert created['id'] == 'SYS-100'
        assert created['title'] == 'New System Requirement'
        assert created['content'] == 'The system shall validate user input'
        
        # Verify item was persisted and can be retrieved
        retrieved = test_core.get_item('SYS-100')
        assert retrieved is not None, "Created item should be retrievable"
        assert retrieved['id'] == 'SYS-100'
        assert retrieved['title'] == 'New System Requirement'
    
    @pytest.mark.verifies("SYS-030")
    def test_user_creates_change_request(self, test_core):
        """
        User creates a new Change Request.
        
        Verifies: SYS-030 (PR/CR automation and change control)
        Test Type: Automated
        
        This test would have caught the bug where UI called update_item
        instead of create_item, causing "Item not found" error.
        """
        # Simulate CR creation form data
        cr_data = {
            'id': 'CR-001',
            'title': 'Update system requirements',
            'description': 'Need to add new validation rules',
            'justification': 'Customer requirement change'
        }
        
        # UI calls create_item for new items
        created = test_core.create_item(cr_data)
        
        # Verify CR was created
        assert created is not None, "CR creation should succeed"
        assert created['id'] == 'CR-001'
        assert created['title'] == 'Update system requirements'
        
        # Verify CR can be retrieved (this would fail with the bug)
        retrieved = test_core.get_item('CR-001')
        assert retrieved is not None, "Created CR should be retrievable"
        assert retrieved['description'] == 'Need to add new validation rules'
    
    def test_user_creates_srs_with_relationship(self, test_core, draft_sys_item):
        """
        User creates SRS requirement linked to parent SYS requirement.
        
        Verifies: SYS-012 (Requirements management with traceability)
        Test Type: Automated
        """
        # Create SRS that derives from SYS-001
        srs_data = {
            'id': 'SRS-001',
            'title': 'Software Requirement',
            'content': 'Software shall implement validation',
            'derives_from': ['SYS-001']  # Link to parent
        }
        
        created = test_core.create_item(srs_data)
        
        # Verify relationship was stored
        assert created is not None
        assert 'SYS-001' in created.get('derives_from', [])
        
        # Verify relationship exists in graph
        assert test_core.graph.has_edge('SRS-001', 'SYS-001')
    
    def test_create_item_with_initial_status(self, test_core):
        """New items should get initial workflow status automatically."""
        item_data = {
            'id': 'SYS-200',
            'title': 'Test Requirement',
            'content': 'Test content'
        }
        
        created = test_core.create_item(item_data)
        
        # Should have initial status from workflow
        assert 'status' in created
        assert created['status'] == 'draft'  # Initial state from config


class TestReadWorkflows:
    """Test item retrieval workflows."""
    
    def test_user_views_requirement_details(self, test_core, draft_sys_item):
        """User clicks on requirement to view its details."""
        # Simulate UI retrieving item for display
        item = test_core.get_item('SYS-001')
        
        # Verify all expected fields are present
        assert item is not None
        assert item['id'] == 'SYS-001'
        assert item['title'] == 'Test System Requirement'
        assert item['content'] == 'The system shall perform function X'
        assert item['status'] == 'draft'
    
    def test_user_views_nonexistent_item(self, test_core):
        """User tries to view an item that doesn't exist."""
        item = test_core.get_item('SYS-999')
        
        # Should return None gracefully
        assert item is None
    
    def test_user_lists_all_requirements(self, test_core, multiple_sys_items):
        """User views list of all SYS requirements."""
        # Get all items (what the list page does)
        all_items = test_core.get_all_items()
        
        # Should have all created items
        assert len(all_items) >= 3
        
        # Verify items are in the list
        item_ids = [item['id'] for item in all_items]
        assert 'SYS-001' in item_ids
        assert 'SYS-002' in item_ids
        assert 'SYS-003' in item_ids


class TestUpdateWorkflows:
    """Test item update workflows."""
    
    def test_user_edits_draft_requirement(self, test_core, draft_sys_item):
        """User edits a draft requirement through the edit form."""
        # Get current item
        item = test_core.get_item('SYS-001')
        
        # Simulate user editing content
        updated_data = item.copy()
        updated_data['content'] = 'Updated: The system shall perform enhanced function X'
        updated_data['category'] = 'Performance'
        
        # UI calls update_item for existing items
        result = test_core.update_item('SYS-001', updated_data)
        
        # Verify update succeeded
        assert result is not None
        assert result['content'] == 'Updated: The system shall perform enhanced function X'
        assert result['category'] == 'Performance'
        
        # Verify changes persisted
        retrieved = test_core.get_item('SYS-001')
        assert retrieved['content'] == 'Updated: The system shall perform enhanced function X'
    
    def test_user_edits_approved_requirement_resets_status(self, test_core, approved_sys_item):
        """
        User edits an approved (stable) requirement.
        Status should reset to draft and approval metadata should be cleared.
        """
        # Get approved item
        item = test_core.get_item('SYS-002')
        assert item['status'] == 'approved'
        assert 'approved_by' in item
        
        # User edits the content
        updated_data = item.copy()
        updated_data['content'] = 'Modified content'
        
        # Update should reset status
        result = test_core.update_item('SYS-002', updated_data)
        
        # Verify status was reset to draft
        assert result['status'] == 'draft', "Editing stable item should reset to draft"
        
        # Verify approval metadata was cleared
        assert 'approved_by' not in result, "Approval metadata should be cleared"
        assert 'approved_date' not in result
    
    def test_update_nonexistent_item_fails(self, test_core):
        """Attempting to update non-existent item should fail gracefully."""
        result = test_core.update_item('SYS-999', {'content': 'test'})
        
        # Should return None for non-existent item
        assert result is None
    
    def test_user_adds_relationship_to_existing_item(self, test_core, draft_sys_item):
        """User adds a parent relationship to an existing requirement."""
        # Create parent item first
        parent_data = {
            'id': 'SYS-PARENT',
            'title': 'Parent Requirement',
            'content': 'Parent content'
        }
        test_core.create_item(parent_data)
        
        # Update child to add relationship
        child = test_core.get_item('SYS-001')
        child['derives_from'] = ['SYS-PARENT']
        
        result = test_core.update_item('SYS-001', child)
        
        # Verify relationship was added
        assert 'SYS-PARENT' in result.get('derives_from', [])
        
        # Verify graph was updated
        test_core.refresh()
        assert test_core.graph.has_edge('SYS-001', 'SYS-PARENT')


class TestFileSystemIntegration:
    """Test that CRUD operations properly interact with the file system."""
    
    def test_created_item_has_yaml_file(self, test_core, test_dhf):
        """Created item should have corresponding YAML file on disk."""
        # Create item
        data = {'id': 'SYS-FILE-TEST', 'title': 'Test', 'content': 'Test'}
        test_core.create_item(data)
        
        # Verify file exists
        expected_file = test_dhf / "items" / "01_sys" / "SYS-FILE-TEST.yaml"
        assert expected_file.exists(), "Item YAML file should be created"
        
        # Verify file contains correct data
        import yaml
        with open(expected_file) as f:
            file_data = yaml.safe_load(f)
        
        assert file_data['id'] == 'SYS-FILE-TEST'
        assert file_data['title'] == 'Test'
    
    def test_updated_item_modifies_yaml_file(self, test_core, test_dhf, draft_sys_item):
        """Updating item should modify its YAML file."""
        # Update item
        item = test_core.get_item('SYS-001')
        item['content'] = 'Modified content'
        test_core.update_item('SYS-001', item)
        
        # Verify file was updated
        item_file = test_dhf / "items" / "01_sys" / "SYS-001.yaml"
        
        import yaml
        with open(item_file) as f:
            file_data = yaml.safe_load(f)
        
        assert file_data['content'] == 'Modified content'
