"""
Automated tests for SRS-001: Item Persistence and Versioning - Schema Validation
Verifies: Line 13 - "Validate item schema before persistence"
Verifies: Line 19 - "Invalid items are rejected with clear error messages"

Tests the strict schema validation feature that validates YAML files against
the project_config.yaml schema definition.
"""

import pytest
from pathlib import Path
import sys
import tempfile
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.repository.loader import ItemLoader
from traceability.exceptions import ValidationError
from traceability.compliant_flow_core import CompliantFlowCore


class TestSchemaValidation:
    """Tests for SRS-001: Schema Validation Against Project Config"""
    
    def test_unknown_field_rejected(self, test_dhf, test_core):
        """Verify items with unknown fields are rejected"""
        # Create a temporary SYS item with an unknown field
        temp_dir = test_dhf / "items" / "02_req_sys"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / "SYS-TEST-INVALID.yaml"
        
        try:
            # Write item with unknown field
            with open(temp_file, 'w') as f:
                yaml.dump({
                    'id': 'SYS-TEST-INVALID',
                    'title': 'Test System Requirement',
                    'content': 'Valid content',
                    'unknown_field': 'This should cause validation error',
                    'status': 'draft'
                }, f)
            
            # Try to load - should raise ValidationError
            with pytest.raises(ValidationError) as exc_info:
                loader = ItemLoader(test_dhf / "items", project_config=test_core.config)
                loader.load_file(temp_file)
            
            # Verify error message is clear
            error_msg = str(exc_info.value)
            assert 'unknown_field' in error_msg.lower(), "Error should mention the unknown field"
            assert 'SYS-TEST-INVALID.yaml' in error_msg, "Error should mention the file name"
            
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
    
    def test_missing_required_field_rejected(self, test_dhf, test_core):
        """Verify items missing required fields are rejected"""
        # Note: This test depends on having required fields defined in project_config
        # If no fields are marked required, this test will be skipped
        
        # Create a temporary item missing a required field
        temp_dir = test_dhf / "items" / "02_req_sys"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / "SYS-TEST-MISSING.yaml"
        
        try:
            # Write item with missing ID (always required)
            with open(temp_file, 'w') as f:
                yaml.dump({
                    'title': 'Test without ID',
                    'content': 'This should fail',
                    'status': 'draft'
                }, f)
            
            # Try to load - should raise ValidationError
            with pytest.raises(ValidationError) as exc_info:
                loader = ItemLoader(test_dhf / "items", project_config=test_core.config)
                loader.load_file(temp_file)
            
            # Verify error message mentions missing field
            error_msg = str(exc_info.value)
            assert 'id' in error_msg.lower(), "Error should mention the missing 'id' field"
            
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
    
    def test_unknown_doc_type_rejected(self, test_dhf, test_core):
        """Verify items with unknown document type are rejected"""
        temp_dir = test_dhf / "items" / "02_req_sys"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / "INVALID-001.yaml"
        
        try:
            # Write item with unknown doc type prefix
            with open(temp_file, 'w') as f:
                yaml.dump({
                    'id': 'INVALID-001',  # INVALID is not a defined doc type
                    'title': 'Test',
                    'content': 'Test',
                    'status': 'draft'
                }, f)
            
            # Try to load - should raise ValidationError
            with pytest.raises(ValidationError) as exc_info:
                loader = ItemLoader(test_dhf / "items", project_config=test_core.config)
                loader.load_file(temp_file)
            
            # Verify error message mentions unknown doc type
            error_msg = str(exc_info.value)
            assert 'INVALID' in error_msg, "Error should mention the unknown doc type code"
            assert 'unknown' in error_msg.lower() or 'not found' in error_msg.lower(), \
                "Error should indicate doc type is unknown"
            
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
    
    def test_valid_item_passes_validation(self, test_dhf, test_core):
        """Verify valid items pass schema validation"""
        temp_dir = test_dhf / "items" / "02_req_sys"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / "SYS-TEST-VALID.yaml"
        
        try:
            # Write a valid item
            with open(temp_file, 'w') as f:
                yaml.dump({
                    'id': 'SYS-TEST-VALID',
                    'title': 'Valid Test System Requirement',
                    'content': 'This is valid content',
                    'status': 'draft'
                }, f)
            
            # Should load successfully without raising ValidationError
            loader = ItemLoader(test_dhf / "items", project_config=test_core.config)
            item = loader.load_file(temp_file)
            
            # Verify item was loaded
            assert item is not None, "Valid item should load successfully"
            assert item.uid == 'SYS-TEST-VALID', "Item ID should match"
            assert item.title == 'Valid Test System Requirement', "Item title should match"
            
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
    
    def test_validation_error_has_clear_message(self, test_dhf, test_core):
        """Verify ValidationError provides clear, actionable error messages (SRS-001 line 19)"""
        temp_dir = test_dhf / "items" / "02_req_sys"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / "SYS-TEST-ERROR.yaml"
        
        try:
            # Write item with multiple issues
            with open(temp_file, 'w') as f:
                yaml.dump({
                    'id': 'SYS-TEST-ERROR',
                    'title': 'Test',
                    'content': 'Test',
                    'bad_field_1': 'Invalid',
                    'bad_field_2': 'Also invalid',
                    'status': 'draft'
                }, f)
            
            # Try to load
            with pytest.raises(ValidationError) as exc_info:
                loader = ItemLoader(test_dhf / "items", project_config=test_core.config)
                loader.load_file(temp_file)
            
            error_msg = str(exc_info.value)
            
            # Verify error message quality (SRS-001 line 19: "clear error messages")
            assert len(error_msg) > 20, "Error message should be descriptive"
            assert 'SYS-TEST-ERROR.yaml' in error_msg, "Should include filename"
            # Should mention at least one of the bad fields
            assert 'bad_field' in error_msg.lower(), "Should mention the problematic field"
            
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
