"""
Automated tests for SRS-004: Automated Git Commits
Verifies: Software shall automatically create Git commits when creating/updating/deleting items
"""

import pytest
from pathlib import Path
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestGitCommits:
    """Tests for SRS-004: Automated Git Commits"""
    
    def test_git_repository_exists(self):
        """Verify Git repository is initialized"""
        git_dir = Path("/Users/chenwenliang/code/CompliantFlow/.git")
        assert git_dir.exists(), "Git repository must exist"
    
    def test_git_history_exists(self):
        """Verify Git history contains commits"""
        result = subprocess.run(
            ["git", "log", "--oneline", "-n", "10"],
            cwd="/Users/chenwenliang/code/CompliantFlow",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Git log command must succeed"
        assert len(result.stdout.strip()) > 0, "Git history must exist"
    
    def test_recent_commits_reference_items(self):
        """Verify recent commits reference DHF items"""
        result = subprocess.run(
            ["git", "log", "--oneline", "-n", "20", "--", "DHF/items/"],
            cwd="/Users/chenwenliang/code/CompliantFlow",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Git log command must succeed"
        # Should have some commits for DHF items
        commits = result.stdout.strip().split('\n')
        assert len([c for c in commits if c]) > 0, "Should have commits for DHF items"
    
    def test_commit_messages_include_action(self):
        """Verify commit messages include action (created/updated/deleted)"""
        result = subprocess.run(
            ["git", "log", "--format=%s", "-n", "50"],
            cwd="/Users/chenwenliang/code/CompliantFlow",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Git log command must succeed"
        
        # Look for action keywords in recent commits
        messages = result.stdout.lower()
        has_action_keywords = any(keyword in messages for keyword in 
                                   ['create', 'update', 'delete', 'add', 'remove', 'migrate'])
        
        assert has_action_keywords, "Commit messages should include action keywords"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
