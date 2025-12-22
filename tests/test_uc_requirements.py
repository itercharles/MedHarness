"""
Automated tests for Use Case (UC) requirements
Verifies all UC requirements are properly defined and traceable
"""

import pytest
from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.repository.loader import ItemLoader

SPECS_DIR = Path("/Users/chenwenliang/code/CompliantFlow/DHF/items")
UC_DIR = SPECS_DIR / "00_uc"


class TestUCRequirements:
    """Tests for Use Case requirements"""
    
    def test_all_uc_files_exist(self):
        """Verify all 5 UC files exist"""
        expected_ucs = ['UC-001', 'UC-002', 'UC-003', 'UC-004', 'UC-005']
        
        for uc_id in expected_ucs:
            uc_file = UC_DIR / f"{uc_id}.yaml"
            assert uc_file.exists(), f"{uc_id}.yaml must exist"
    
    def test_uc_structure(self):
        """Verify UC files have correct structure"""
        uc_files = list(UC_DIR.glob("UC-*.yaml"))
        
        for uc_file in uc_files:
            with open(uc_file) as f:
                uc = yaml.safe_load(f)
            
            # Required fields
            assert 'id' in uc, f"{uc_file.name} must have id"
            assert 'title' in uc, f"{uc_file.name} must have title"
            assert 'content' in uc, f"{uc_file.name} must have content"
            assert 'status' in uc, f"{uc_file.name} must have status"
    
    def test_uc_content_format(self):
        """Verify UC content includes Actor and Goal"""
        uc_files = list(UC_DIR.glob("UC-*.yaml"))
        
        for uc_file in uc_files:
            with open(uc_file) as f:
                uc = yaml.safe_load(f)
            
            content = uc['content']
            assert 'Actor:' in content or '**Actor:**' in content, \
                f"{uc['id']} must specify Actor"
            assert 'Goal:' in content or '**Goal:**' in content, \
                f"{uc['id']} must specify Goal"
    
    def test_uc_001_manage_requirements(self):
        """Verify UC-001: Manage Requirements"""
        uc_file = UC_DIR / "UC-001.yaml"
        with open(uc_file) as f:
            uc = yaml.safe_load(f)
        
        assert uc['id'] == 'UC-001'
        assert 'Manage Requirements' in uc['title']
        assert 'Requirements Engineer' in uc['content']
    
    def test_uc_002_verify_traceability(self):
        """Verify UC-002: Verify Traceability"""
        uc_file = UC_DIR / "UC-002.yaml"
        with open(uc_file) as f:
            uc = yaml.safe_load(f)
        
        assert uc['id'] == 'UC-002'
        assert 'Traceability' in uc['title']
        assert 'Quality Engineer' in uc['content']
    
    def test_uc_003_generate_documents(self):
        """Verify UC-003: Generate Specification Documents"""
        uc_file = UC_DIR / "UC-003.yaml"
        with open(uc_file) as f:
            uc = yaml.safe_load(f)
        
        assert uc['id'] == 'UC-003'
        assert 'Documentation Specialist' in uc['content']
    
    def test_uc_004_manage_changes(self):
        """Verify UC-004: Manage Change Requests"""
        uc_file = UC_DIR / "UC-004.yaml"
        with open(uc_file) as f:
            uc = yaml.safe_load(f)
        
        assert uc['id'] == 'UC-004'
        assert 'Change' in uc['title']
    
    def test_uc_005_check_compliance(self):
        """Verify UC-005: Check Compliance Policies"""
        uc_file = UC_DIR / "UC-005.yaml"
        with open(uc_file) as f:
            uc = yaml.safe_load(f)
        
        assert uc['id'] == 'UC-005'
        assert 'Compliance' in uc['title'] or 'Regulatory' in uc['content']
    
    def test_all_ucs_approved(self):
        """Verify all UCs are in approved status"""
        uc_files = list(UC_DIR.glob("UC-*.yaml"))
        
        for uc_file in uc_files:
            with open(uc_file) as f:
                uc = yaml.safe_load(f)
            
            assert uc['status'] == 'approved', \
                f"{uc['id']} should be approved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
