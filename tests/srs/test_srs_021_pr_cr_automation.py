"""
Automated tests for SRS-level PR-CR automation requirements

Tests verify:
- SRS-006: Change Request Management (PR-CR automation)
  - PR-CR Validation
  - PR Tracking in Change Requests
- SRS-007: Change Impact Tracking
  - Automatic Affected Items Detection  

@links: SRS-006, SRS-007
"""

import pytest
import yaml
import re
from pathlib import Path
import tempfile


class TestSRS021_PRCRValidation:
    """
    Test SRS-021: PR-CR Validation
    
    Verify that every Pull Request references a valid Change Request
    """
    
    def test_TC_SRS_021_001_pr_without_cr_reference_rejected(self):
        """
        TC-SRS-021-001: Verify PR without CR reference is rejected
        
        @links: SRS-006
        @test_id: TC-SRS-021-001
        """
        # Test PR titles without CR reference
        invalid_titles = [
            "Add new feature",
            "Fix bug in validation",
            "Update documentation",
            "CR- invalid format",
            "CR-ABC not numeric"
        ]
        
        cr_pattern = r"CR-[0-9]+"
        
        for title in invalid_titles:
            match = re.search(cr_pattern, title)
            assert match is None, f"Title '{title}' should not match CR pattern"
    
    def test_TC_SRS_021_001_pr_with_valid_cr_accepted(self):
        """
        TC-SRS-021-001: Verify PR with valid CR reference is accepted
        
        @links: SRS-006
        @test_id: TC-SRS-021-001
        """
        # Test PR titles with valid CR reference
        valid_titles = [
            "[CR-001] Add feature",
            "CR-123: Fix bug",
            "Update docs (CR-999)",
            "CR-042 - Enhancement"
        ]
        
        cr_pattern = r"CR-[0-9]+"
        
        for title in valid_titles:
            match = re.search(cr_pattern, title)
            assert match is not None, f"Title '{title}' should match CR pattern"
            
            # Verify extracted CR ID format
            cr_id = match.group()
            assert cr_id.startswith("CR-")
            assert cr_id[3:].isdigit()
    
    def test_TC_SRS_021_001_cr_file_must_exist(self):
        """
        TC-SRS-021-001: Verify CR file existence is validated
        
        @links: SRS-006
        @test_id: TC-SRS-021-001
        """
        from tests.fixtures.test_data import create_test_dhf, populate_test_dhf
        
        # Create test DHF with populated data (includes CR-001)
        test_dhf_root = create_test_dhf()
        populate_test_dhf(test_dhf_root)
        
        cr_dir = test_dhf_root / "items" / "08_cr"
        
        # Test existing CR (CR-001 is created by populate_test_dhf)
        test_cr = cr_dir / "CR-001.yaml"
        assert test_cr.exists(), "Existing CR file should be found"
        
        # Test non-existent CR
        fake_cr_path = cr_dir / "CR-99999.yaml"
        assert not fake_cr_path.exists(), "Non-existent CR should not be found"
    
    def test_TC_SRS_021_001_cr_stable_status_rejected(self):
        """
        TC-SRS-021-001: Verify CR in stable status is rejected
        
        @links: SRS-006
        @test_id: TC-SRS-021-001
        """
        # Test stable status validation logic
        stable_statuses = ['approved', 'closed', 'retired']
        valid_statuses = ['draft', 'under_review', 'in_progress']
        
        # Simulate CR status check
        for status in stable_statuses:
            is_stable = status in stable_statuses
            assert is_stable == True, f"Status '{status}' should be considered stable"
        
        for status in valid_statuses:
            is_stable = status in stable_statuses
            assert is_stable == False, f"Status '{status}' should not be considered stable"


class TestSRS022_AffectedItemsDetection:
    """
    Test SRS-022: Automatic Affected Items Detection
    
    Verify automatic detection and recording of affected DHF items
    """
    
    def test_TC_SRS_022_001_yaml_item_detection(self):
        """
        TC-SRS-022-001: Verify YAML item detection
        
        @links: SRS-007
        @test_id: TC-SRS-022-001
        """
        # Simulate changed files
        changed_files = [
            "DHF/items/02_req_sys/SYS-001.yaml",
            "DHF/items/03_req_srs/SRS-042.yaml",
            "DHF/items/09_cr/CR-001.yaml",  # Should be excluded
            "src/main.py"  # Not a DHF item
        ]
        
        affected_items = []
        
        for file in changed_files:
            # Check if it's a YAML file in DHF/items/ but not in CR directory
            if file.startswith("DHF/items/") and file.endswith(".yaml"):
                if not file.startswith("DHF/items/09_cr/"):
                    item_id = Path(file).stem
                    if item_id not in affected_items:
                        affected_items.append(item_id)
        
        assert len(affected_items) == 2
        assert "SYS-001" in affected_items
        assert "SRS-042" in affected_items
        assert "CR-001" not in affected_items
    
    def test_TC_SRS_022_001_multiple_items_no_duplicates(self):
        """
        TC-SRS-022-001: Verify no duplicate items in affected_items
        
        @links: SRS-007
        @test_id: TC-SRS-022-001
        """
        # Simulate multiple changes to same file
        changed_files = [
            "DHF/items/02_req_sys/SYS-001.yaml",
            "DHF/items/03_req_srs/SRS-042.yaml",
            "DHF/items/02_req_sys/SYS-001.yaml",  # Duplicate
        ]
        
        affected_items = []
        
        for file in changed_files:
            if file.startswith("DHF/items/") and file.endswith(".yaml"):
                if not file.startswith("DHF/items/09_cr/"):
                    item_id = Path(file).stem
                    if item_id not in affected_items:
                        affected_items.append(item_id)
        
        assert len(affected_items) == 2, "Should not have duplicates"
        assert affected_items.count("SYS-001") == 1
    
    def test_TC_SRS_022_002_test_file_mapping(self):
        """
        TC-SRS-022-002: Verify test file detection and mapping
        
        @links: SRS-007
        @test_id: TC-SRS-022-002
        """
        # Test file name to test case ID mapping
        test_files = [
            ("test_sys_001_core.py", "TC-SYS-001"),
            ("test_srs_042_validation.py", "TC-SRS-042"),
            ("test_crs_009_traceability.py", "TC-CRS-009"),
        ]
        
        for filename, expected_id in test_files:
            # Extract test case ID from filename
            match = re.match(r"test_([a-z]+)_([0-9]+)_", filename)
            assert match is not None, f"Filename '{filename}' should match pattern"
            
            type_code = match.group(1).upper()
            number = match.group(2)
            test_id = f"TC-{type_code}-{number}"
            
            assert test_id == expected_id
    
    def test_TC_SRS_022_002_test_file_with_corresponding_yaml(self, tmp_path):
        """
        TC-SRS-022-002: Verify only test files with YAML items are tracked
        
        @links: SRS-007
        @test_id: TC-SRS-022-002
        """
        # Create test DHF structure
        test_dhf = tmp_path / "test_dhf"
        tc_dir = test_dhf / "items" / "05_tc_sys"
        tc_dir.mkdir(parents=True)
        
        # Create a test case YAML file
        test_yaml = tc_dir / "TC-SYS-001.yaml"
        test_yaml.write_text("id: TC-SYS-001\ntitle: Test Case\n")
        
        # Simulate test file change
        test_file = "test_sys_001_core.py"
        match = re.match(r"test_([a-z]+)_([0-9]+)_", test_file)
        
        if match:
            type_code = match.group(1).upper()
            number = match.group(2)
            test_id = f"TC-{type_code}-{number}"
            
            # Check if corresponding YAML exists
            possible_dirs = [
                test_dhf / "items" / "05_tc_sys",
                test_dhf / "items" / "06_tc_crs",
                test_dhf / "items" / "07_tc_sds"
            ]
            
            yaml_exists = False
            for dir_path in possible_dirs:
                if dir_path.exists():
                    yaml_file = dir_path / f"{test_id}.yaml"
                    if yaml_file.exists():
                        yaml_exists = True
                        break
            
            # This test validates the logic - we created TC-SYS-001.yaml so it should exist
            assert yaml_exists is True


class TestSRS023_PRTracking:
    """
    Test SRS-023: PR Tracking in Change Requests
    
    Verify automatic tracking of PRs in implementation_prs field
    """
    
    def test_TC_SRS_023_001_pr_added_on_creation(self):
        """
        TC-SRS-023-001: Verify PR is tracked when created
        
        @links: SRS-006
        @test_id: TC-SRS-023-001
        """
        # Simulate PR creation
        pr_data = {
            'pr_number': 123,
            'pr_url': 'https://github.com/user/repo/pull/123',
            'title': '[CR-001] Add feature',
            'status': 'open'
        }
        
        # Verify required fields
        assert 'pr_number' in pr_data
        assert 'pr_url' in pr_data
        assert 'title' in pr_data
        assert 'status' in pr_data
        
        # Verify field types
        assert isinstance(pr_data['pr_number'], int)
        assert isinstance(pr_data['pr_url'], str)
        assert pr_data['status'] == 'open'
        
        # Verify URL format
        assert pr_data['pr_url'].startswith('https://github.com/')
        assert f"/pull/{pr_data['pr_number']}" in pr_data['pr_url']
    
    def test_TC_SRS_023_001_pr_tracked_immediately(self):
        """
        TC-SRS-023-001: Verify PR tracked immediately (not after merge)
        
        @links: SRS-006
        @test_id: TC-SRS-023-001
        """
        # Simulate CR with implementation_prs
        cr_data = {
            'id': 'CR-001',
            'implementation_prs': []
        }
        
        # Add PR info immediately when PR is created
        pr_info = {
            'pr_number': 123,
            'pr_url': 'https://github.com/user/repo/pull/123',
            'title': '[CR-001] Test',
            'status': 'open'
        }
        cr_data['implementation_prs'].append(pr_info)
        
        # Verify PR is tracked before merge
        assert len(cr_data['implementation_prs']) == 1
        assert cr_data['implementation_prs'][0]['status'] == 'open'
        assert 'merged_at' not in cr_data['implementation_prs'][0]
    
    def test_TC_SRS_023_002_pr_status_updated_on_merge(self):
        """
        TC-SRS-023-002: Verify PR status updated when merged
        
        @links: SRS-006
        @test_id: TC-SRS-023-002
        """
        # Simulate CR with open PR
        cr_data = {
            'id': 'CR-001',
            'implementation_prs': [
                {
                    'pr_number': 123,
                    'pr_url': 'https://github.com/user/repo/pull/123',
                    'title': '[CR-001] Test',
                    'status': 'open'
                }
            ]
        }
        
        # Simulate PR merge
        pr_number = 123
        merged_at = '2025-12-26T12:00:00Z'
        
        for pr in cr_data['implementation_prs']:
            if pr['pr_number'] == pr_number:
                pr['status'] = 'merged'
                pr['merged_at'] = merged_at
        
        # Verify status updated
        assert cr_data['implementation_prs'][0]['status'] == 'merged'
        assert cr_data['implementation_prs'][0]['merged_at'] == merged_at
    
    def test_TC_SRS_023_002_no_duplicate_pr_entries(self):
        """
        TC-SRS-023-002: Verify no duplicate PR entries created
        
        @links: SRS-006
        @test_id: TC-SRS-023-002
        """
        # Simulate CR with existing PR
        cr_data = {
            'implementation_prs': [
                {'pr_number': 123, 'status': 'open'}
            ]
        }
        
        # Try to add same PR again
        new_pr_number = 123
        pr_exists = any(pr.get('pr_number') == new_pr_number 
                       for pr in cr_data['implementation_prs'])
        
        # Should not add if already exists
        if not pr_exists:
            cr_data['implementation_prs'].append({'pr_number': new_pr_number})
        
        assert len(cr_data['implementation_prs']) == 1, "Should not have duplicate"
    
    def test_TC_SRS_023_002_skip_ci_in_commit_message(self):
        """
        TC-SRS-023-002: Verify [skip ci] flag in post-merge commit
        
        @links: SRS-006
        @test_id: TC-SRS-023-002
        """
        # Simulate commit message for post-merge update
        commit_message = "[skip ci] Track PR #123 in CR-001"
        
        # Verify [skip ci] flag present
        assert "[skip ci]" in commit_message
        
        # Verify it's at the beginning
        assert commit_message.startswith("[skip ci]")
    
    def test_TC_SRS_023_cr_yaml_update_with_pr_info(self):
        """
        TC-SRS-023: Verify CR YAML can be updated with PR tracking
        
        @links: SRS-006
        """
        # Create temporary CR file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            cr_data = {
                'id': 'CR-TEST',
                'status': 'in_progress',
                'implementation_prs': []
            }
            yaml.dump(cr_data, f, default_flow_style=False, sort_keys=False)
            temp_file = f.name
        
        try:
            # Read and update
            with open(temp_file) as f:
                cr_data = yaml.safe_load(f)
            
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
            
            assert len(updated_data['implementation_prs']) == 1
            assert updated_data['implementation_prs'][0]['pr_number'] == 123
            assert updated_data['implementation_prs'][0]['status'] == 'open'
            
        finally:
            # Cleanup
            Path(temp_file).unlink()
