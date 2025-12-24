"""
Tests for git history tracking functionality (SRS-019).

These tests verify that status changes and other field changes can be
extracted from git history for audit and traceability purposes.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.git_history import (
    get_item_history,
    get_status_changes,
    get_field_changes,
    format_history_table
)


class TestSRS019_GitHistoryTracking:
    """Tests for SRS-019: Git History Tracking for Item Changes."""
    
    @pytest.fixture
    def dhf_root(self):
        """Get DHF root directory."""
        return Path(__file__).parent.parent / "DHF"
    
    @pytest.fixture
    def sys_001_path(self, dhf_root):
        """Get path to SYS-001 item."""
        return dhf_root / "items" / "02_req_sys" / "SYS-001.yaml"
    
    def test_get_item_history_exists(self):
        """Verify get_item_history function exists and is callable."""
        assert callable(get_item_history), "get_item_history should be callable"
    
    def test_get_status_changes_exists(self):
        """Verify get_status_changes function exists and is callable."""
        assert callable(get_status_changes), "get_status_changes should be callable"
    
    def test_get_item_history_returns_commits(self, sys_001_path, dhf_root):
        """Verify get_item_history returns commit history."""
        commits = get_item_history(sys_001_path, dhf_root)
        
        assert isinstance(commits, list), "Should return a list"
        if commits:  # If there's git history
            commit = commits[0]
            assert 'commit_hash' in commit, "Should have commit_hash"
            assert 'author_name' in commit, "Should have author_name"
            assert 'author_email' in commit, "Should have author_email"
            assert 'timestamp' in commit, "Should have timestamp"
            assert 'message' in commit, "Should have message"
    
    def test_get_status_changes_returns_changes(self, sys_001_path, dhf_root):
        """Verify get_status_changes returns status change history."""
        changes = get_status_changes(sys_001_path, dhf_root)
        
        assert isinstance(changes, list), "Should return a list"
        if changes:  # If there are status changes
            change = changes[0]
            assert 'to_status' in change, "Should have to_status"
            assert 'author_name' in change, "Should have author_name"
            assert 'timestamp' in change, "Should have timestamp"
            assert 'commit_hash' in change, "Should have commit_hash"
    
    def test_get_field_changes_for_title(self, sys_001_path, dhf_root):
        """Verify get_field_changes can track title changes."""
        changes = get_field_changes(sys_001_path, dhf_root, "title")
        
        assert isinstance(changes, list), "Should return a list"
        if changes:  # If there are title changes
            change = changes[0]
            assert 'to_value' in change, "Should have to_value"
            assert 'author_name' in change, "Should have author_name"
            assert 'timestamp' in change, "Should have timestamp"
    
    def test_format_history_table_creates_markdown(self):
        """Verify format_history_table creates markdown table."""
        test_changes = [
            {
                'timestamp': '2025-12-23 18:53:15 +0200',
                'author_name': 'Test Author',
                'from_status': 'draft',
                'to_status': 'approved',
                'commit_hash': 'abc1234567890',
                'message': 'Test commit message'
            }
        ]
        
        result = format_history_table(test_changes, "status")
        
        assert isinstance(result, str), "Should return a string"
        assert '|' in result, "Should contain table separators"
        assert 'Test Author' in result, "Should contain author name"
        assert 'draft' in result, "Should contain from status"
        assert 'approved' in result, "Should contain to status"
    
    def test_format_history_table_handles_empty_list(self):
        """Verify format_history_table handles empty change list."""
        result = format_history_table([], "status")
        
        assert isinstance(result, str), "Should return a string"
        assert "No status changes found" in result, "Should indicate no changes"


class TestGitHistoryIntegration:
    """Integration tests for git history with CompliantFlowCore."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        from traceability.compliant_flow_core import CompliantFlowCore
        dhf_root = Path(__file__).parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_items_have_file_path(self, core):
        """Verify loaded items include file_path metadata."""
        all_items = core.get_all_items()
        
        assert len(all_items) > 0, "Should have items"
        
        # Check that at least some items have file_path
        items_with_path = [item for item in all_items if 'file_path' in item]
        assert len(items_with_path) > 0, "Some items should have file_path"
        
        # Verify file_path format
        if items_with_path:
            item = items_with_path[0]
            assert isinstance(item['file_path'], str), "file_path should be a string"
            assert item['file_path'].endswith('.yaml') or item['file_path'].endswith('.yml'), \
                "file_path should point to YAML file"
    
    def test_get_item_includes_file_path(self, core):
        """Verify get_item returns file_path for individual items."""
        # Get a known item
        item = core.get_item("SYS-001")
        
        if item:
            assert 'file_path' in item, "Item should have file_path"
            assert isinstance(item['file_path'], str), "file_path should be a string"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
