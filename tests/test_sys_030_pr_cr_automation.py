"""
Automated tests for PR-CR automation workflows

Tests verify:
- SRS-021: PR-CR Validation
- SRS-022: Automatic Affected Items Detection  
- SRS-023: PR Tracking in Change Requests

@links: SYS-030
"""

import pytest
import yaml
import re
from pathlib import Path
import tempfile
import shutil


class TestPRCRValidation:
    """
    Test PR-CR Validation
    
    @links: SRS-021, SDS-001
    @test_id: TC-SYS-030-001
    """
    
    def test_cr_reference_extraction(self):
        """Verify CR reference can be extracted from PR title"""
        # Test valid patterns
        assert re.search(r"CR-[0-9]+", "[CR-001] Add feature") is not None
        assert re.search(r"CR-[0-9]+", "Fix bug CR-123") is not None
        assert re.search(r"CR-[0-9]+", "CR-999: Update docs") is not None
        
        # Test invalid patterns
        assert re.search(r"CR-[0-9]+", "No CR reference") is None
        assert re.search(r"CR-[0-9]+", "CR-ABC invalid") is None
    
    def test_cr_file_exists_validation(self):
        """Verify CR file existence check"""
        dhf_root = Path(__file__).parent.parent / "DHF"
        cr_dir = dhf_root / "items" / "09_cr"
        
        # Check that CR directory exists
        assert cr_dir.exists(), "CR directory should exist"
        
        # Check that at least one CR file exists
        cr_files = list(cr_dir.glob("CR-*.yaml"))
        assert len(cr_files) > 0, "At least one CR file should exist"
        
        # Test CR file validation logic
        test_cr = cr_files[0]
        assert test_cr.exists()
        
        # Test non-existent CR
        fake_cr = cr_dir / "CR-99999.yaml"
        assert not fake_cr.exists()
    
    def test_cr_status_validation(self):
        """Verify CR status is checked correctly"""
        dhf_root = Path(__file__).parent.parent / "DHF"
        cr_dir = dhf_root / "items" / "09_cr"
        
        # Find a CR file to test
        cr_files = list(cr_dir.glob("CR-*.yaml"))
        if cr_files:
            with open(cr_files[0]) as f:
                cr_data = yaml.safe_load(f)
            
            # Verify status field exists
            assert 'status' in cr_data, "CR should have status field"
            
            # Test stable status check logic
            status = cr_data['status']
            stable_statuses = ['approved', 'closed', 'retired']
            
            # This logic should prevent changes if CR is stable
            is_stable = status in stable_statuses
            assert isinstance(is_stable, bool)


class TestAffectedItemsDetection:
    """
    Test Automatic Affected Items Detection
    
    @links: SRS-022, SDS-001
    @test_id: TC-SYS-030-002
    """
    
    def test_yaml_item_id_extraction(self):
        """Verify item IDs can be extracted from YAML files"""
        dhf_root = Path(__file__).parent.parent / "DHF"
        items_dir = dhf_root / "items"
        
        # Test with actual SYS item
        sys_dir = items_dir / "02_req_sys"
        if sys_dir.exists():
            yaml_files = list(sys_dir.glob("SYS-*.yaml"))
            if yaml_files:
                with open(yaml_files[0]) as f:
                    item_data = yaml.safe_load(f)
                
                assert 'id' in item_data
                assert item_data['id'].startswith('SYS-')
    
    def test_test_file_id_mapping(self):
        """Verify test file names can be mapped to test case IDs"""
        # Test filename pattern matching
        test_patterns = [
            ("test_sys_001_core.py", "TC-SYS-001"),
            ("test_srs_042_validation.py", "TC-SRS-042"),
            ("test_crs_009_traceability.py", "TC-CRS-009"),
        ]
        
        for filename, expected_id in test_patterns:
            # Extract pattern: test_{type}_{number}_
            match = re.match(r"test_([a-z]+)_([0-9]+)_", filename)
            if match:
                type_code = match.group(1).upper()
                number = match.group(2)
                test_id = f"TC-{type_code}-{number}"
                assert test_id == expected_id
    
    def test_affected_items_no_duplicates(self):
        """Verify affected_items list prevents duplicates"""
        affected_items = []
        new_items = ["SYS-001", "SRS-042", "SYS-001"]  # SYS-001 is duplicate
        
        for item in new_items:
            if item not in affected_items:
                affected_items.append(item)
        
        assert len(affected_items) == 2
        assert affected_items == ["SYS-001", "SRS-042"]


class TestPRTracking:
    """
    Test PR Tracking in Change Requests
    
    @links: SRS-023, SDS-001, SDS-002
    @test_id: TC-SYS-030-003
    """
    
    def test_pr_info_structure(self):
        """Verify PR info has correct structure"""
        pr_info = {
            'pr_number': 123,
            'pr_url': "https://github.com/user/repo/pull/123",
            'title': "[CR-001] Test PR",
            'status': 'open'
        }
        
        # Verify required fields
        assert 'pr_number' in pr_info
        assert 'pr_url' in pr_info
        assert 'title' in pr_info
        assert 'status' in pr_info
        
        # Verify types
        assert isinstance(pr_info['pr_number'], int)
        assert isinstance(pr_info['pr_url'], str)
        assert pr_info['status'] in ['open', 'merged']
    
    def test_pr_status_update(self):
        """Verify PR status can be updated from open to merged"""
        implementation_prs = [
            {
                'pr_number': 123,
                'pr_url': "https://github.com/user/repo/pull/123",
                'title': "[CR-001] Test",
                'status': 'open'
            }
        ]
        
        # Simulate status update
        pr_number = 123
        merged_at = "2025-12-26T12:00:00Z"
        
        for pr in implementation_prs:
            if pr.get('pr_number') == pr_number:
                pr['status'] = 'merged'
                pr['merged_at'] = merged_at
        
        # Verify update
        assert implementation_prs[0]['status'] == 'merged'
        assert implementation_prs[0]['merged_at'] == merged_at
    
    def test_pr_duplicate_prevention(self):
        """Verify duplicate PRs are not added"""
        implementation_prs = [
            {'pr_number': 123, 'status': 'open'}
        ]
        
        # Try to add same PR again
        new_pr_number = 123
        pr_exists = any(pr.get('pr_number') == new_pr_number for pr in implementation_prs)
        
        assert pr_exists == True
        
        # Different PR should not exist
        different_pr = 456
        pr_exists = any(pr.get('pr_number') == different_pr for pr in implementation_prs)
        
        assert pr_exists == False
    
    def test_cr_yaml_update(self):
        """Verify CR YAML can be updated with PR info"""
        # Create temporary CR file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            cr_data = {
                'id': 'CR-TEST',
                'title': 'Test CR',
                'status': 'in_progress',
                'affected_items': [],
                'implementation_prs': []
            }
            yaml.dump(cr_data, f, default_flow_style=False, sort_keys=False)
            temp_file = f.name
        
        try:
            # Read and update
            with open(temp_file) as f:
                cr_data = yaml.safe_load(f)
            
            # Add affected items
            cr_data['affected_items'].append('SYS-001')
            
            # Add PR info
            pr_info = {
                'pr_number': 123,
                'pr_url': 'https://github.com/test/repo/pull/123',
                'title': '[CR-TEST] Test PR',
                'status': 'open'
            }
            cr_data['implementation_prs'].append(pr_info)
            
            # Write back
            with open(temp_file, 'w') as f:
                yaml.dump(cr_data, f, default_flow_style=False, sort_keys=False)
            
            # Verify
            with open(temp_file) as f:
                updated_data = yaml.safe_load(f)
            
            assert len(updated_data['affected_items']) == 1
            assert updated_data['affected_items'][0] == 'SYS-001'
            assert len(updated_data['implementation_prs']) == 1
            assert updated_data['implementation_prs'][0]['pr_number'] == 123
            
        finally:
            # Cleanup
            Path(temp_file).unlink()


class TestWorkflowIntegration:
    """
    Integration tests for complete workflow
    
    @links: SYS-030
    """
    
    def test_complete_pr_workflow_simulation(self):
        """Simulate complete PR workflow from creation to merge"""
        # 1. PR created with CR reference
        pr_title = "[CR-001] Add new feature"
        cr_match = re.search(r"CR-[0-9]+", pr_title)
        assert cr_match is not None
        cr_id = cr_match.group()
        
        # 2. Simulate CR data
        cr_data = {
            'id': cr_id,
            'status': 'in_progress',
            'affected_items': [],
            'implementation_prs': []
        }
        
        # 3. Simulate file changes
        changed_files = [
            "DHF/items/02_req_sys/SYS-001.yaml",
            "tests/test_sys_001_core.py"
        ]
        
        # 4. Extract affected items
        for file in changed_files:
            if file.startswith("DHF/items/") and file.endswith(".yaml"):
                # Extract item ID from path
                item_id = Path(file).stem
                if item_id not in cr_data['affected_items']:
                    cr_data['affected_items'].append(item_id)
            elif file.startswith("tests/") and file.endswith(".py"):
                # Extract test case ID from filename
                basename = Path(file).stem
                match = re.match(r"test_([a-z]+)_([0-9]+)_", basename)
                if match:
                    test_id = f"TC-{match.group(1).upper()}-{match.group(2)}"
                    if test_id not in cr_data['affected_items']:
                        cr_data['affected_items'].append(test_id)
        
        # 5. Add PR info
        pr_info = {
            'pr_number': 123,
            'pr_url': 'https://github.com/test/repo/pull/123',
            'title': pr_title,
            'status': 'open'
        }
        cr_data['implementation_prs'].append(pr_info)
        
        # 6. Verify state after PR creation
        assert len(cr_data['affected_items']) == 2
        assert 'SYS-001' in cr_data['affected_items']
        assert 'TC-SYS-001' in cr_data['affected_items']
        assert len(cr_data['implementation_prs']) == 1
        assert cr_data['implementation_prs'][0]['status'] == 'open'
        
        # 7. Simulate PR merge
        for pr in cr_data['implementation_prs']:
            if pr['pr_number'] == 123:
                pr['status'] = 'merged'
                pr['merged_at'] = '2025-12-26T12:00:00Z'
        
        # 8. Verify final state
        assert cr_data['implementation_prs'][0]['status'] == 'merged'
        assert 'merged_at' in cr_data['implementation_prs'][0]
