"""YAML file loader for items."""

from pathlib import Path
import yaml
from typing import List, Optional
from ..models.item import Item


class ItemLoader:
    """Load items from YAML files."""
    
    def __init__(self, specs_dir: Path):
        """
        Initialize loader.
        
        Args:
            specs_dir: Path to specifications directory
        """
        self.specs_dir = specs_dir
    
    def load_all(self) -> List[Item]:
        """
        Load all items from specifications directory.
        
        Returns:
            List of loaded items
        """
        items = []
        
        if not self.specs_dir.exists():
            print(f"Warning: Specifications directory {self.specs_dir} does not exist")
            return items
        
        for yaml_file in self.specs_dir.rglob("*.yaml"):
            item = self.load_file(yaml_file)
            if item:
                items.append(item)
        
        # Also check for .yml extension
        for yml_file in self.specs_dir.rglob("*.yml"):
            item = self.load_file(yml_file)
            if item:
                items.append(item)
        
        return items
    
    def load_file(self, file_path: Path) -> Optional[Item]:
        """
        Load a single item from a YAML file.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Loaded item or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            # Pydantic v2 validation
            # The model will handle 'id' -> 'uid' and 'content' -> 'text' aliases
            item = Item.model_validate(data)
            
            # Add file_path as an extra field (model allows extra fields)
            # Store as string for JSON serialization
            item.file_path = str(file_path.absolute())  # type: ignore
            
            return item
            
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    
    def load_by_prefix(self, prefix: str) -> List[Item]:
        """
        Load items with a specific prefix.
        
        Args:
            prefix: Item prefix (e.g., 'SYS-')
            
        Returns:
            List of items with matching prefix
        """
        all_items = self.load_all()
        return [item for item in all_items if item.uid.startswith(prefix)]
    
    def load_by_uid(self, uid: str) -> Optional[Item]:
        """
        Load a specific item by UID.
        
        Args:
            uid: Item UID
            
        Returns:
            Item or None if not found
        """
        all_items = self.load_all()
        for item in all_items:
            if item.uid == uid:
                return item
        return None
