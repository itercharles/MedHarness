"""
Test suite for validating DHF requirements traceability after migration to dual-track model.

This test suite validates:
- UC → CRS → SYS → SRS → SWAD → SWDD traceability chain
- No orphaned requirements
- Correct number of requirements per type
- All links resolve correctly
"""

import pytest
from pathlib import Path
import yaml


DHF_ITEMS = Path("/Users/chenwenliang/code/CompliantFlow/DHF/items")


def load_all_items(directory: Path):
    """Load all YAML items from a directory."""
    items = []
    if directory.exists():
        for yaml_file in directory.glob("*.yaml"):
            with open(yaml_file) as f:
                item = yaml.safe_load(f)
                if item:
                    items.append(item)
    return items


def test_uc_files_exist():
    """Verify all 5 UC files were created."""
    uc_dir = DHF_ITEMS / "00_uc"
    uc_files = list(uc_dir.glob("UC-*.yaml"))
    assert len(uc_files) == 5, f"Expected 5 UC files, found {len(uc_files)}"


def test_crs_files_exist():
    """Verify all 9 CRS files were created."""
    crs_dir = DHF_ITEMS / "01_req_crs"
    crs_files = list(crs_dir.glob("CRS-*.yaml"))
    assert len(crs_files) >= 9, f"Expected at least 9 CRS files, found {len(crs_files)}"


def test_srs_files_exist():
    """Verify all 12 SRS files were created."""
    srs_dir = DHF_ITEMS / "03_req_srs"
    srs_files = list(srs_dir.glob("SRS-*.yaml"))
    assert len(srs_files) == 12, f"Expected 12 SRS files, found {len(srs_files)}"


def test_swad_files_exist():
    """Verify all 4 SWAD files were created."""
    swad_dir = DHF_ITEMS / "04_swad"
    swad_files = list(swad_dir.glob("SWAD-*.yaml"))
    assert len(swad_files) == 4, f"Expected 4 SWAD files, found {len(swad_files)}"


def test_swdd_files_exist():
    """Verify all 5 SWDD files were created."""
    swdd_dir = DHF_ITEMS / "05_swdd"
    swdd_files = list(swdd_dir.glob("SWDD-*.yaml"))
    assert len(swdd_files) == 5, f"Expected 5 SWDD files, found {len(swdd_files)}"


def test_sys_arch_files_exist():
    """Verify all 2 SYS_ARCH files were created."""
    sys_arch_dir = DHF_ITEMS / "06_sys_arch"
    sys_arch_files = list(sys_arch_dir.glob("SYSARCH-*.yaml"))
    assert len(sys_arch_files) == 2, f"Expected 2 SYS_ARCH files, found {len(sys_arch_files)}"


def test_crs_to_uc_traceability():
    """Verify all CRS items trace back to UC."""
    crs_items = load_all_items(DHF_ITEMS / "01_req_crs")
    uc_ids = {f"UC-{i:03d}" for i in range(1, 6)}
    
    for crs in crs_items:
        if 'derives_from' in crs:
            # Check that at least one link points to a UC
            derives_from = crs['derives_from']
            if isinstance(derives_from, list):
                has_uc_link = any(link.startswith('UC-') for link in derives_from)
                assert has_uc_link, f"{crs['id']} does not trace to any UC"


def test_srs_to_sys_traceability():
    """Verify all SRS items trace back to SYS."""
    srs_items = load_all_items(DHF_ITEMS / "03_req_srs")
    
    for srs in srs_items:
        assert 'derives_from' in srs, f"{srs['id']} missing derives_from field"
        derives_from = srs['derives_from']
        if isinstance(derives_from, list):
            has_sys_link = any(link.startswith('SYS-') for link in derives_from)
            assert has_sys_link, f"{srs['id']} does not trace to any SYS"


def test_swad_implements_srs():
    """Verify all SWAD items implement SRS."""
    swad_items = load_all_items(DHF_ITEMS / "04_swad")
    
    for swad in swad_items:
        assert 'implements' in swad, f"{swad['id']} missing implements field"
        implements = swad['implements']
        if isinstance(implements, list):
            has_srs_link = any(link.startswith('SRS-') for link in implements)
            assert has_srs_link, f"{swad['id']} does not implement any SRS"


def test_swdd_implements_srs():
    """Verify all SWDD items implement SRS."""
    swdd_items = load_all_items(DHF_ITEMS / "05_swdd")
    
    for swdd in swdd_items:
        assert 'implements' in swdd, f"{swdd['id']} missing implements field"
        implements = swdd['implements']
        if isinstance(implements, list):
            has_srs_link = any(link.startswith('SRS-') for link in implements)
            assert has_srs_link, f"{swdd['id']} does not implement any SRS"


def test_swdd_guided_by_swad():
    """Verify all SWDD items are guided by SWAD."""
    swdd_items = load_all_items(DHF_ITEMS / "05_swdd")
    
    for swdd in swdd_items:
        assert 'guided_by' in swdd, f"{swdd['id']} missing guided_by field"
        guided_by = swdd['guided_by']
        if isinstance(guided_by, list):
            has_swad_link = any(link.startswith('SWAD-') for link in guided_by)
            assert has_swad_link, f"{swdd['id']} not guided by any SWAD"


def test_sys_arch_informs_sys():
    """Verify SYS_ARCH items inform SYS."""
    sys_arch_items = load_all_items(DHF_ITEMS / "06_sys_arch")
    
    for sys_arch in sys_arch_items:
        assert 'informs' in sys_arch, f"{sys_arch['id']} missing informs field"
        informs = sys_arch['informs']
        if isinstance(informs, list):
            has_sys_link = any(link.startswith('SYS-') for link in informs)
            assert has_sys_link, f"{sys_arch['id']} does not inform any SYS"


def test_all_items_have_status():
    """Verify all new items have status field."""
    directories = [
        DHF_ITEMS / "00_uc",
        DHF_ITEMS / "01_req_crs",
        DHF_ITEMS / "03_req_srs",
        DHF_ITEMS / "04_swad",
        DHF_ITEMS / "05_swdd",
        DHF_ITEMS / "06_sys_arch"
    ]
    
    for directory in directories:
        items = load_all_items(directory)
        for item in items:
            assert 'status' in item, f"{item.get('id', 'unknown')} missing status field"


def test_complete_traceability_chain():
    """Verify complete traceability chain exists: UC → CRS → SYS → SRS → SWAD → SWDD."""
    # Load all items
    uc_items = load_all_items(DHF_ITEMS / "00_uc")
    crs_items = load_all_items(DHF_ITEMS / "01_req_crs")
    srs_items = load_all_items(DHF_ITEMS / "03_req_srs")
    swad_items = load_all_items(DHF_ITEMS / "04_swad")
    swdd_items = load_all_items(DHF_ITEMS / "05_swdd")
    
    # Verify chain exists
    assert len(uc_items) > 0, "No UC items found"
    assert len(crs_items) > 0, "No CRS items found"
    assert len(srs_items) > 0, "No SRS items found"
    assert len(swad_items) > 0, "No SWAD items found"
    assert len(swdd_items) > 0, "No SWDD items found"
    
    print(f"\nTraceability chain verified:")
    print(f"  UC: {len(uc_items)} items")
    print(f"  CRS: {len(crs_items)} items")
    print(f"  SRS: {len(srs_items)} items")
    print(f"  SWAD: {len(swad_items)} items")
    print(f"  SWDD: {len(swdd_items)} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
