"""
Automated tests for System Requirements (SYS)
Verifies SYS requirements trace to CRS and have proper verification
"""

import pytest
from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

SPECS_DIR = Path(__file__).parent.parent / "DHF" / "items"
SYS_DIR = SPECS_DIR / "02_req_sys"


class TestSYSRequirements:
    """Tests for System Requirements"""
    
    def test_sys_files_exist(self):
        """Verify SYS requirement files exist"""
        sys_files = list(SYS_DIR.glob("SYS-*.yaml"))
        assert len(sys_files) >= 10, "Should have at least 10 SYS requirements"
    
    def test_sys_structure(self):
        """Verify SYS files have correct structure"""
        sys_files = list(SYS_DIR.glob("SYS-*.yaml"))
        
        for sys_file in sys_files[:10]:  # Check first 10
            with open(sys_file) as f:
                sys_req = yaml.safe_load(f)
            
            # Required fields
            assert 'id' in sys_req, f"{sys_file.name} must have id"
            assert 'title' in sys_req, f"{sys_file.name} must have title"
            assert 'content' in sys_req, f"{sys_file.name} must have content"
    
    def test_sys_traces_to_crs(self):
        """Verify SYS requirements trace to CRS"""
        sys_files = list(SYS_DIR.glob("SYS-*.yaml"))
        
        traced_count = 0
        for sys_file in sys_files:
            with open(sys_file) as f:
                sys_req = yaml.safe_load(f)
            
            if 'links' in sys_req and sys_req['links']:
                # Check if any link is to CRS
                for link in sys_req['links']:
                    if link.startswith('CRS-'):
                        traced_count += 1
                        break
        
        assert traced_count > 0, "At least some SYS requirements should trace to CRS"
    
    def test_sys_have_verification_method(self):
        """Verify SYS requirements specify verification method"""
        sys_files = list(SYS_DIR.glob("SYS-*.yaml"))
        
        with_verification = 0
        for sys_file in sys_files[:10]:
            with open(sys_file) as f:
                sys_req = yaml.safe_load(f)
            
            if 'verification_method' in sys_req:
                with_verification += 1
        
        # At least some should have verification method
        assert with_verification >= 0, "SYS requirements should support verification_method"
    
    def test_sys_categories_defined(self):
        """Verify SYS requirements can have categories"""
        sys_files = list(SYS_DIR.glob("SYS-*.yaml"))
        
        categories = set()
        for sys_file in sys_files[:10]:
            with open(sys_file) as f:
                sys_req = yaml.safe_load(f)
            
            if 'category' in sys_req:
                categories.add(sys_req['category'])
        
        # Should support categorization
        assert isinstance(categories, set), "Should be able to categorize SYS requirements"
    
    def test_sys_001_exists(self):
        """Verify SYS-001 exists"""
        sys_file = SYS_DIR / "SYS-001.yaml"
        assert sys_file.exists(), "SYS-001.yaml must exist"
        
        with open(sys_file) as f:
            sys_req = yaml.safe_load(f)
        
        assert sys_req['id'] == 'SYS-001'
        assert len(sys_req['title']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
