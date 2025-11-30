"""YAML file saver for items."""

from pathlib import Path
import yaml
from typing import Optional
from ..models.item import Item
from .git import GitRepository


class ItemSaver:
    """Save items to YAML files."""
    
    def __init__(
        self,
        specs_dir: Path,
        git_repo: Optional[GitRepository] = None
    ):
        """
        Initialize saver.
        
        Args:
            specs_dir: Path to specifications directory
            git_repo: Optional Git repository for auto-commits
        """
        self.specs_dir = specs_dir
        self.git_repo = git_repo
    
    def save(
        self,
        item: Item,
        subdirectory: Optional[str] = None,
        author: Optional[str] = None
    ) -> Path:
        """
        Save an item to a YAML file.
        
        Args:
            item: Item to save
            subdirectory: Optional subdirectory within specs_dir
            author: Optional author name for git commit
            
        Returns:
            Path to saved file
        """
        # Determine save directory
        if subdirectory:
            save_dir = self.specs_dir / subdirectory
        else:
            # Auto-determine based on prefix
            save_dir = self._get_directory_for_prefix(item.prefix)
        
        # Create directory if needed
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file path
        file_path = save_dir / f"{item.uid}.yaml"
        
        # Convert item to dict for YAML
        # Use model_dump with by_alias=True to convert back to 'id' and 'content'
        data = item.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude_unset=True
        )
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
        
        # Auto-commit if git available
        if self.git_repo and self.git_repo.is_available():
            action = "created" if not file_path.exists() else "updated"
            self.git_repo.commit_item_change(
                item.uid,
                file_path,
                action=action,
                author=author
            )
        
        return file_path
    
    def delete(self, uid: str, author: Optional[str] = None) -> bool:
        """
        Delete an item file.
        
        Args:
            uid: Item UID
            author: Optional author name for git commit
            
        Returns:
            True if deleted successfully
        """
        # Find the file
        for yaml_file in self.specs_dir.rglob(f"{uid}.yaml"):
            try:
                # Commit deletion if git available
                if self.git_repo and self.git_repo.is_available():
                    self.git_repo.commit_item_change(
                        uid,
                        yaml_file,
                        action="deleted",
                        author=author
                    )
                
                # Delete file
                yaml_file.unlink()
                return True
                
            except Exception as e:
                print(f"Error deleting {yaml_file}: {e}")
                return False
        
        return False
    
    def _get_directory_for_prefix(self, prefix: str) -> Path:
        """
        Get appropriate directory for a prefix.
        
        Args:
            prefix: Item prefix
            
        Returns:
            Directory path
        """
        # Map prefixes to directories
        # This is a simple mapping - could be made configurable
        prefix_map = {
            'USN-': '01_user_needs',
            'RISK-': '00_risks',
            'RCM-': '01_rcm',
            'SYS-': '02_sys_reqs',
            'TC-VER-': '05_test_cases',
            'TC-VAL-': '06_validation_tests',
        }
        
        subdir = prefix_map.get(prefix, 'other')
        return self.specs_dir / subdir
