"""
Automated tests for Software Architecture (SWAD) requirements
Verifies SWAD items implement SRS requirements
"""

import pytest
from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

SPECS_DIR = Path("/Users/chenwenliang/code/CompliantFlow/DHF/items")
SWAD_DIR = SPECS_DIR / "04_swad"


class TestSWADRequirements:
    """Tests for Software Architecture requirements"""
    
    def test_all_swad_files_exist(self):
        """Verify all 4 SWAD files exist"""
        expected_swad = ['SWAD-001', 'SWAD-002', 'SWAD-003', 'SWAD-004']
        
        for swad_id in expected_swad:
            swad_file = SWAD_DIR / f"{swad_id}.yaml"
            assert swad_file.exists(), f"{swad_id}.yaml must exist"
    
    def test_swad_structure(self):
        """Verify SWAD files have correct structure"""
        swad_files = list(SWAD_DIR.glob("SWAD-*.yaml"))
        
        for swad_file in swad_files:
            with open(swad_file) as f:
                swad = yaml.safe_load(f)
            
            # Required fields
            assert 'id' in swad, f"{swad_file.name} must have id"
            assert 'title' in swad, f"{swad_file.name} must have title"
            assert 'content' in swad, f"{swad_file.name} must have content"
            assert 'implements' in swad, f"{swad_file.name} must have implements"
    
    def test_swad_implements_srs(self):
        """Verify SWAD items implement SRS requirements"""
        swad_files = list(SWAD_DIR.glob("SWAD-*.yaml"))
        
        for swad_file in swad_files:
            with open(swad_file) as f:
                swad = yaml.safe_load(f)
            
            implements = swad['implements']
            assert isinstance(implements, list), \
                f"{swad['id']} implements must be a list"
            assert len(implements) > 0, \
                f"{swad['id']} must implement at least one SRS"
            
            # Check all links are to SRS
            for link in implements:
                assert link.startswith('SRS-'), \
                    f"{swad['id']} should only implement SRS items, found {link}"
    
    def test_swad_001_layered_architecture(self):
        """Verify SWAD-001: Four-Layer Software Architecture"""
        swad_file = SWAD_DIR / "SWAD-001.yaml"
        with open(swad_file) as f:
            swad = yaml.safe_load(f)
        
        assert swad['id'] == 'SWAD-001'
        assert 'Layer' in swad['title'] or 'Architecture' in swad['title']
        
        # Should describe layers
        content = swad['content']
        assert 'Layer' in content or 'layer' in content
    
    def test_swad_002_core_components(self):
        """Verify SWAD-002: CompliantFlow Core Components"""
        swad_file = SWAD_DIR / "SWAD-002.yaml"
        with open(swad_file) as f:
            swad = yaml.safe_load(f)
        
        assert swad['id'] == 'SWAD-002'
        assert 'Component' in swad['title'] or 'Core' in swad['title']
    
    def test_swad_003_data_access(self):
        """Verify SWAD-003: Data Access Components"""
        swad_file = SWAD_DIR / "SWAD-003.yaml"
        with open(swad_file) as f:
            swad = yaml.safe_load(f)
        
        assert swad['id'] == 'SWAD-003'
        content = swad['content']
        assert 'ItemLoader' in content or 'ItemSaver' in content or 'Loader' in content
    
    def test_swad_004_page_template(self):
        """Verify SWAD-004: Universal Page Template Architecture"""
        swad_file = SWAD_DIR / "SWAD-004.yaml"
        with open(swad_file) as f:
            swad = yaml.safe_load(f)
        
        assert swad['id'] == 'SWAD-004'
        assert 'Template' in swad['title'] or 'Page' in swad['title']
    
    def test_all_swad_approved(self):
        """Verify all SWAD are in approved status"""
        swad_files = list(SWAD_DIR.glob("SWAD-*.yaml"))
        
        for swad_file in swad_files:
            with open(swad_file) as f:
                swad = yaml.safe_load(f)
            
            assert swad['status'] == 'approved', \
                f"{swad['id']} should be approved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
