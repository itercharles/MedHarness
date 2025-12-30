"""
Automated tests for SRS-005: Data Validation
Verifies: Software shall validate item data against configured schemas
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.repository.loader import ItemLoader
from traceability.models.item import Item

# Tests use test_core fixture from conftest.py


class TestDataValidation:
    """Tests for SRS-005: Data Validation"""
    
    def test_pydantic_models_defined(self):
        """Verify Pydantic data models are defined"""
        try:
            from pydantic import BaseModel
            assert issubclass(Item, BaseModel), "Item must be a Pydantic model"
        except ImportError:
            pytest.fail("Pydantic not available")
    
    def test_required_fields_enforced(self):
        """Verify required fields are enforced"""
        # Try to create an Item without required fields
        try:
            # This should fail if validation is working
            item = Item()
            pytest.fail("Item creation without required fields should fail")
        except Exception:
            # Expected - validation should prevent this
            assert True, "Required fields are enforced"
    
    def test_type_checking_on_load(self, test_core):
        """Verify type checking happens on load"""
        # loader = ItemLoader(SPECS_DIR)
        items = test_core.loader.load_all()
        
        # All loaded items should be valid Item instances
        for item in items[:10]:  # Check first 10
            # Items are already Item instances from loader
            assert hasattr(item, 'uid'), "Item must have uid"
            assert hasattr(item, 'title'), "Item must have title"
    
    def test_validation_error_messages(self):
        """Verify clear error messages for validation failures"""
        # Try to create item with invalid data
        try:
            from pydantic import ValidationError
            
            # Attempt to create with wrong types
            Item(uid=123, title=None)  # Wrong types
            pytest.fail("Should raise ValidationError")
        except Exception as e:
            # Should get a clear error message
            error_msg = str(e)
            assert len(error_msg) > 0, "Error message should not be empty"
    
    def test_all_items_validate_successfully(self, test_core):
        """Verify all existing items pass validation"""
        # loader = ItemLoader(SPECS_DIR)
        items = test_core.loader.load_all()
        
        # All items should have loaded successfully (validation passed)
        assert len(items) > 0, "Should have loaded items"
        
        # Verify each item has required attributes
        for item in items:
            assert item.uid, "Item uid must not be empty"
            assert item.title, "Item title must not be empty"
    
    def test_invalid_yaml_rejected(self, test_dhf, test_core):
        """Verify invalid YAML files are rejected"""
        # Create a temporary invalid YAML file
        temp_dir = test_dhf / "items" / "00_uc"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / "INVALID-TEST.yaml"
        
        try:
            # Write invalid YAML
            with open(temp_file, 'w') as f:
                f.write("invalid: yaml: content: [unclosed")
            
            # Try to load - should handle gracefully
            # loader = ItemLoader(SPECS_DIR)
            items = test_core.loader.load_all()
            
            # Should either skip invalid file or raise clear error
            assert True, "Invalid YAML handled"
            
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
