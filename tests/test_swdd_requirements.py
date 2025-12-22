"""
Automated tests for Software Detailed Design (SWDD) requirements
Verifies SWDD items implement SRS and are guided by SWAD
"""

import pytest
from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

SPECS_DIR = Path("/Users/chenwenliang/code/CompliantFlow/DHF/items")
SWDD_DIR = SPECS_DIR / "05_swdd"


class TestSWDDRequirements:
    """Tests for Software Detailed Design requirements"""
    
    def test_all_swdd_files_exist(self):
        """Verify all 5 SWDD files exist"""
        expected_swdd = ['SWDD-001', 'SWDD-002', 'SWDD-003', 'SWDD-004', 'SWDD-005']
        
        for swdd_id in expected_swdd:
            swdd_file = SWDD_DIR / f"{swdd_id}.yaml"
            assert swdd_file.exists(), f"{swdd_id}.yaml must exist"
    
    def test_swdd_structure(self):
        """Verify SWDD files have correct structure"""
        swdd_files = list(SWDD_DIR.glob("SWDD-*.yaml"))
        
        for swdd_file in swdd_files:
            with open(swdd_file) as f:
                swdd = yaml.safe_load(f)
            
            # Required fields
            assert 'id' in swdd, f"{swdd_file.name} must have id"
            assert 'title' in swdd, f"{swdd_file.name} must have title"
            assert 'content' in swdd, f"{swdd_file.name} must have content"
            assert 'implements' in swdd, f"{swdd_file.name} must have implements"
            assert 'guided_by' in swdd, f"{swdd_file.name} must have guided_by"
    
    def test_swdd_implements_srs(self):
        """Verify SWDD items implement SRS requirements"""
        swdd_files = list(SWDD_DIR.glob("SWDD-*.yaml"))
        
        for swdd_file in swdd_files:
            with open(swdd_file) as f:
                swdd = yaml.safe_load(f)
            
            implements = swdd['implements']
            assert isinstance(implements, list), \
                f"{swdd['id']} implements must be a list"
            assert len(implements) > 0, \
                f"{swdd['id']} must implement at least one SRS"
            
            # Check all links are to SRS
            for link in implements:
                assert link.startswith('SRS-'), \
                    f"{swdd['id']} should only implement SRS items, found {link}"
    
    def test_swdd_guided_by_swad(self):
        """Verify SWDD items are guided by SWAD"""
        swdd_files = list(SWDD_DIR.glob("SWDD-*.yaml"))
        
        for swdd_file in swdd_files:
            with open(swdd_file) as f:
                swdd = yaml.safe_load(f)
            
            guided_by = swdd['guided_by']
            assert isinstance(guided_by, list), \
                f"{swdd['id']} guided_by must be a list"
            assert len(guided_by) > 0, \
                f"{swdd['id']} must be guided by at least one SWAD"
            
            # Check all links are to SWAD
            for link in guided_by:
                assert link.startswith('SWAD-'), \
                    f"{swdd['id']} should only be guided by SWAD items, found {link}"
    
    def test_swdd_001_orphan_detection(self):
        """Verify SWDD-001: Orphan Detection Algorithm"""
        swdd_file = SWDD_DIR / "SWDD-001.yaml"
        with open(swdd_file) as f:
            swdd = yaml.safe_load(f)
        
        assert swdd['id'] == 'SWDD-001'
        assert 'Orphan' in swdd['title']
        
        # Should describe algorithm
        content = swdd['content']
        assert 'Algorithm' in content or 'algorithm' in content
    
    def test_swdd_002_coverage_calculation(self):
        """Verify SWDD-002: Coverage Calculation Algorithm"""
        swdd_file = SWDD_DIR / "SWDD-002.yaml"
        with open(swdd_file) as f:
            swdd = yaml.safe_load(f)
        
        assert swdd['id'] == 'SWDD-002'
        assert 'Coverage' in swdd['title']
    
    def test_swdd_003_serialization(self):
        """Verify SWDD-003: Item Serialization Process"""
        swdd_file = SWDD_DIR / "SWDD-003.yaml"
        with open(swdd_file) as f:
            swdd = yaml.safe_load(f)
        
        assert swdd['id'] == 'SWDD-003'
        assert 'Serialization' in swdd['title'] or 'Item' in swdd['title']
    
    def test_swdd_004_validation_criteria(self):
        """Verify SWDD-004: Validation Criteria Framework"""
        swdd_file = SWDD_DIR / "SWDD-004.yaml"
        with open(swdd_file) as f:
            swdd = yaml.safe_load(f)
        
        assert swdd['id'] == 'SWDD-004'
        assert 'Validation' in swdd['title']
    
    def test_swdd_005_document_generation(self):
        """Verify SWDD-005: Document Generation Process"""
        swdd_file = SWDD_DIR / "SWDD-005.yaml"
        with open(swdd_file) as f:
            swdd = yaml.safe_load(f)
        
        assert swdd['id'] == 'SWDD-005'
        assert 'Document' in swdd['title'] or 'Generation' in swdd['title']
    
    def test_swdd_describe_algorithms(self):
        """Verify SWDD items describe algorithms"""
        swdd_files = list(SWDD_DIR.glob("SWDD-*.yaml"))
        
        algorithm_count = 0
        for swdd_file in swdd_files:
            with open(swdd_file) as f:
                swdd = yaml.safe_load(f)
            
            content = swdd['content'].lower()
            if 'algorithm' in content or 'process' in content or 'step' in content:
                algorithm_count += 1
        
        assert algorithm_count >= 3, "Most SWDD should describe algorithms or processes"
    
    def test_all_swdd_approved(self):
        """Verify all SWDD are in approved status"""
        swdd_files = list(SWDD_DIR.glob("SWDD-*.yaml"))
        
        for swdd_file in swdd_files:
            with open(swdd_file) as f:
                swdd = yaml.safe_load(f)
            
            assert swdd['status'] == 'approved', \
                f"{swdd['id']} should be approved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
