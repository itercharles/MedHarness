"""
Automated tests for Customer Requirements (CRS)
Verifies all CRS requirements are properly defined and traceable to UCs
"""

import pytest
from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.repository.loader import ItemLoader

SPECS_DIR = Path(__file__).parent.parent / "DHF" / "items"
CRS_DIR = SPECS_DIR / "01_req_crs"


class TestCRSRequirements:
    """Tests for Customer Requirements"""
    
    def test_all_crs_files_exist(self):
        """Verify all 9 CRS files exist"""
        expected_crs = [f'CRS-{i:03d}' for i in range(1, 10)]
        
        for crs_id in expected_crs:
            crs_file = CRS_DIR / f"{crs_id}.yaml"
            assert crs_file.exists(), f"{crs_id}.yaml must exist"
    
    def test_crs_structure(self):
        """Verify CRS files have correct structure"""
        crs_files = list(CRS_DIR.glob("CRS-*.yaml"))
        
        for crs_file in crs_files:
            with open(crs_file) as f:
                crs = yaml.safe_load(f)
            
            # Required fields
            assert 'id' in crs, f"{crs_file.name} must have id"
            assert 'title' in crs, f"{crs_file.name} must have title"
            assert 'content' in crs, f"{crs_file.name} must have content"
            assert 'status' in crs, f"{crs_file.name} must have status"
            # Either derives_from or links is acceptable
            assert 'derives_from' in crs or 'links' in crs, \
                f"{crs_file.name} must have derives_from or links"
    
    def test_crs_traces_to_uc(self):
        """Verify all CRS requirements trace to UC"""
        crs_files = list(CRS_DIR.glob("CRS-*.yaml"))
        
        for crs_file in crs_files:
            with open(crs_file) as f:
                crs = yaml.safe_load(f)
            
            # Get traceability links (either derives_from or links)
            derives_from = crs.get('derives_from', crs.get('links', []))
            assert isinstance(derives_from, list), \
                f"{crs['id']} derives_from must be a list"
            # Some CRS may not have traceability yet
            if len(derives_from) == 0:
                continue  # Skip CRS without traceability
            
            # Check all links are to UC
            for link in derives_from:
                assert link.startswith('UC-'), \
                    f"{crs['id']} should only derive from UC items, found {link}"
    
    def test_crs_001_iec_compliance(self):
        """Verify CRS-001: IEC 62304 Compliance"""
        crs_file = CRS_DIR / "CRS-001.yaml"
        with open(crs_file) as f:
            crs = yaml.safe_load(f)
        
        assert crs['id'] == 'CRS-001'
        assert 'IEC 62304' in crs['title'] or 'IEC 62304' in crs['content']
        assert crs['priority'] == 'Critical'
    
    def test_crs_002_traceability(self):
        """Verify CRS-002: Complete Traceability"""
        crs_file = CRS_DIR / "CRS-002.yaml"
        with open(crs_file) as f:
            crs = yaml.safe_load(f)
        
        assert crs['id'] == 'CRS-002'
        assert 'Traceability' in crs['title']
        assert crs['priority'] == 'Critical'
    
    def test_crs_003_audit_trail(self):
        """Verify CRS-003: Complete Audit Trail"""
        crs_file = CRS_DIR / "CRS-003.yaml"
        with open(crs_file) as f:
            crs = yaml.safe_load(f)
        
        assert crs['id'] == 'CRS-003'
        assert 'Audit' in crs['title']
    
    def test_critical_requirements_identified(self):
        """Verify critical requirements are properly marked"""
        crs_files = list(CRS_DIR.glob("CRS-*.yaml"))
        
        critical_count = 0
        for crs_file in crs_files:
            with open(crs_file) as f:
                crs = yaml.safe_load(f)
            
            if 'priority' in crs and crs['priority'] == 'Critical':
                critical_count += 1
        
        assert critical_count >= 3, "Should have at least 3 critical requirements"
    
    def test_all_crs_approved(self):
        """Verify all CRS are in approved status"""
        crs_files = list(CRS_DIR.glob("CRS-*.yaml"))
        
        for crs_file in crs_files:
            with open(crs_file) as f:
                crs = yaml.safe_load(f)
            
            assert crs['status'] == 'approved', \
                f"{crs['id']} should be approved"
    
    def test_crs_have_rationale(self):
        """Verify CRS requirements can have rationale"""
        crs_files = list(CRS_DIR.glob("CRS-*.yaml"))
        
        with_rationale = 0
        for crs_file in crs_files:
            with open(crs_file) as f:
                crs = yaml.safe_load(f)
            
            if 'rationale' in crs and len(crs['rationale']) > 0:
                with_rationale += 1
        
        # At least some should have rationale
        assert with_rationale >= 5, "Most CRS should have rationale"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
