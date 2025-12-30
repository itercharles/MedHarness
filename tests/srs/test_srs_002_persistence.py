"""
Automated tests for SRS-002: Structured File Persistence
Verifies: Software shall store each DHF item as a separate structured text file
"""

import pytest
from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.repository.loader import ItemLoader
from traceability.repository.saver import ItemSaver

# Path to DHF items
SPECS_DIR = Path(__file__).parent.parent.parent / "DHF" / "items"


class TestFilePersistence:
    """Tests for SRS-002: Structured File Persistence"""
    
    def test_items_stored_as_separate_files(self):
        """Verify each DHF item is stored as a separate file"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        # Each item should have come from a separate file
        # DHF currently has 64 items across all types
        assert len(items) >= 60, \
            f"Expected at least 60 items in DHF, got {len(items)}"
        
        # Verify each item has unique ID
        item_ids = [item.uid for item in items]
        assert len(item_ids) == len(set(item_ids)), \
            f"Each item must have unique ID. Found {len(item_ids)} items but {len(set(item_ids))} unique IDs"
    
    def test_filename_matches_item_id(self):
        """Verify item ID is used as filename"""
        dhf_items_dir = Path(__file__).parent.parent.parent / "DHF" / "items"
        
        # Check a few item directories
        for subdir in dhf_items_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                yaml_files = list(subdir.glob("*.yaml"))
                
                for yaml_file in yaml_files:
                    # Load the item
                    with open(yaml_file) as f:
                        item_data = yaml.safe_load(f)
                    
                    if item_data and 'id' in item_data:
                        # Verify filename matches ID
                        expected_filename = f"{item_data['id']}.yaml"
                        assert yaml_file.name == expected_filename, \
                            f"File {yaml_file.name} should be named {expected_filename}"
    
    def test_files_organized_by_type(self):
        """Verify files are organized in subdirectories by document type"""
        dhf_items_dir = Path(__file__).parent.parent.parent / "DHF" / "items"
        
        # Check that subdirectories exist (DHF has 11 document type directories)
        subdirs = [d for d in dhf_items_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        assert len(subdirs) >= 10, \
            f"Expected at least 10 document type subdirectories, got {len(subdirs)}"
        
        # Verify items in each directory have consistent prefix
        for subdir in subdirs:
            yaml_files = list(subdir.glob("*.yaml"))
            if yaml_files:
                # Get prefix from first file
                first_file = yaml_files[0]
                with open(first_file) as f:
                    item_data = yaml.safe_load(f)
                
                if item_data and 'id' in item_data:
                    prefix = item_data['id'].split('-')[0]
                    
                    # All files in this directory should have same prefix
                    for yaml_file in yaml_files:
                        with open(yaml_file) as f:
                            data = yaml.safe_load(f)
                        if data and 'id' in data:
                            assert data['id'].startswith(prefix), \
                                f"All items in {subdir.name} should have prefix {prefix}"
    
    def test_data_validation_on_load(self):
        """Verify data is validated when loading"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        # All loaded items should have required fields
        for item in items:
            assert hasattr(item, 'uid'), "Item must have id field"
            assert hasattr(item, 'title'), "Item must have title field"
            assert item.uid, "Item id must not be empty"
            assert item.title, "Item title must not be empty"
    
    def test_structured_text_format(self):
        """Verify files use structured text format (YAML)"""
        dhf_items_dir = Path(__file__).parent.parent.parent / "DHF" / "items"
        
        yaml_files = list(dhf_items_dir.rglob("*.yaml"))
        assert len(yaml_files) >= 60, \
            f"Expected at least 60 YAML files in DHF, got {len(yaml_files)}"
        
        # Verify files are valid YAML
        for yaml_file in yaml_files[:10]:  # Check first 10
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            assert isinstance(data, dict), f"{yaml_file} must contain valid YAML dict"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
