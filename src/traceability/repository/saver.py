"""YAML file saver for items."""

from pathlib import Path
import yaml
from typing import Optional, Dict, Any
from ..models.item import Item
from .git import GitRepository


class ItemSaver:
    """Save items to YAML files."""
    
    def __init__(
        self,
        specs_dir: Path,
        git_repo: Optional[GitRepository] = None,
        project_config: Optional[Any] = None
    ):
        """
        Initialize saver.
        
        Args:
            specs_dir: Path to specifications directory
            git_repo: Optional Git repository for auto-commits
            project_config: Optional ProjectConfig for directory mapping
        """
        self.specs_dir = specs_dir
        self.git_repo = git_repo
        self.project_config = project_config
        self._prefix_map = None
    
    def save(
        self,
        item: Item,
        subdirectory: Optional[str] = None,
        author: Optional[str] = None,
        cr_id: Optional[str] = None
    ) -> Path:
        """
        Save an item to a YAML file.
        
        Args:
            item: Item to save
            subdirectory: Optional subdirectory within specs_dir
            author: Optional author name for git commit
            cr_id: Optional Change Request ID for git commit reference
            
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
        # Use by_alias=True to use 'id' and 'content' instead of 'uid' and 'text'
        # Use mode='json' to properly serialize enums and other types
        # Use exclude_unset=True to only save fields that were explicitly set
        # This prevents default fields (active, history) from being added
        data = item.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude_unset=True,
            mode='json'  # This converts enums to their values
        )
        
        # Remove the original field names if they exist (uid, text)
        # since we're using aliases (id, content)
        data.pop('uid', None)
        data.pop('text', None)

        # Remove runtime-only fields that must never be persisted to YAML
        data.pop('file_path', None)

        # Remove fields with default values to keep YAML files clean
        # These are Item model defaults that shouldn't be in the files
        if data.get('active') == True:
            data.pop('active', None)
        if data.get('history') == []:
            data.pop('history', None)
        
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
                author=author,
                cr_id=cr_id
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
    
    def _build_prefix_map(self) -> Dict[str, str]:
        """
        Build prefix-to-directory mapping from project config.
        
        Returns:
            Dictionary mapping prefixes to directory names
        """
        if self._prefix_map is not None:
            return self._prefix_map
        
        prefix_map = {}
        
        if self.project_config and hasattr(self.project_config, 'doc_types'):
            # Build mapping from project config
            # Directory name is derived from prefix by removing trailing dash
            for doc_type in self.project_config.doc_types:
                prefix = doc_type.prefix
                # Use directory if specified, otherwise derive from prefix
                directory = doc_type.directory if doc_type.directory else prefix.rstrip('-')
                prefix_map[prefix] = directory
        else:
            # Fallback: derive directory from prefix
            # This shouldn't normally be needed if config is loaded
            pass
        
        self._prefix_map = prefix_map
        return prefix_map
    
    def _get_directory_for_prefix(self, prefix: str) -> Path:
        """
        Get appropriate directory for a prefix.
        Uses longest prefix matching to handle cases like SDS-DEF- matching SDS-.
        
        Args:
            prefix: Item prefix (e.g., 'SDS-DEF-', 'TC-SYS-')
            
        Returns:
            Directory path
        """
        prefix_map = self._build_prefix_map()
        
        # Try exact match first
        if prefix in prefix_map:
            subdir = prefix_map[prefix]
        else:
            # Try longest prefix match
            # Sort by length descending to match longest first
            matched_prefix = None
            for config_prefix in sorted(prefix_map.keys(), key=len, reverse=True):
                if prefix.startswith(config_prefix):
                    matched_prefix = config_prefix
                    break
            
            if matched_prefix:
                subdir = prefix_map[matched_prefix]
            else:
                subdir = 'other'
        
        return self.specs_dir / subdir
