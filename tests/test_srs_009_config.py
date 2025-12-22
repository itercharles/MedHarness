"""
Automated tests for SRS-009: Project Configuration Validation
Verifies: Software shall validate project_config.yaml on startup
"""

import pytest
from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestConfigValidation:
    """Tests for SRS-009: Project Configuration Validation"""
    
    def test_config_file_exists(self):
        """Verify project_config.yaml exists"""
        config_path = Path(__file__).parent.parent / "DHF" / "config" / "project_config.yaml"
        assert config_path.exists(), "project_config.yaml must exist"
    
    def test_config_is_valid_yaml(self):
        """Verify configuration is valid YAML"""
        config_path = Path(__file__).parent.parent / "DHF" / "config" / "project_config.yaml"
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        assert isinstance(config, dict), "Configuration must be a dictionary"
    
    def test_config_has_doc_types(self):
        """Verify configuration defines document types"""
        config_path = Path(__file__).parent.parent / "DHF" / "config" / "project_config.yaml"
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        assert 'doc_types' in config, "Configuration must define doc_types"
        assert isinstance(config['doc_types'], list), "doc_types must be a list"
        assert len(config['doc_types']) > 0, "Must have at least one document type"
    
    def test_doc_types_have_required_fields(self):
        """Verify each document type has required fields"""
        config_path = Path(__file__).parent.parent / "DHF" / "config" / "project_config.yaml"
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        required_fields = ['code', 'name', 'prefix']  # directory is optional for some types
        
        for doc_type in config['doc_types']:
            for field in required_fields:
                assert field in doc_type, f"Document type must have '{field}' field"
                assert doc_type[field], f"Document type '{field}' must not be empty"
    
    def test_new_doc_types_present(self):
        """Verify new document types (UC, SRS, SWAD, SWDD, SYS_ARCH) are in config"""
        config_path = Path(__file__).parent.parent / "DHF" / "config" / "project_config.yaml"
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        doc_type_codes = [dt['code'] for dt in config['doc_types']]
        
        new_types = ['UC', 'SRS', 'SWAD', 'SWDD', 'SYS_ARCH']
        for new_type in new_types:
            assert new_type in doc_type_codes, f"Configuration must include {new_type} document type"
    
    def test_config_schema_validation(self):
        """Verify configuration follows expected schema"""
        config_path = Path(__file__).parent.parent / "DHF" / "config" / "project_config.yaml"
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Check top-level structure
        assert 'doc_types' in config, "Must have doc_types"
        
        # Check each doc_type has lifecycle if specified
        for doc_type in config['doc_types']:
            if 'lifecycle' in doc_type:
                assert 'states' in doc_type['lifecycle'], "Lifecycle must have states"
                assert 'transitions' in doc_type['lifecycle'], "Lifecycle must have transitions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
