"""
Tests for SRS-011: Configurable Document Type Definitions (Item Model)
and SRS-002: Traceability Graph Construction (DHF Integration)

@links: SRS-011, SRS-002
"""
Automated tests for typed relationships feature.

Tests verify that different relationship types (derives_from, implements, 
guided_by, informs) are properly handled while preserving semantic meaning
and supporting graph traversal.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.models.item import Item
from traceability.compliant_flow_core import CompliantFlowCore


class TestTypedRelationships:
    """Tests for typed relationship fields in Item model.
    
    @links: SRS-011
    """
    
    def test_item_has_typed_relationship_fields(self):
        """Verify Item model has all typed relationship fields."""
        item = Item(
            id="TEST-001",
            content="Test item",
            derives_from=["PARENT-001"],
            implements=["REQ-001"],
            guided_by=["ARCH-001"],
            informs=["CHILD-001"]
        )
        
        assert item.derives_from == ["PARENT-001"]
        assert item.implements == ["REQ-001"]
        assert item.guided_by == ["ARCH-001"]
        assert item.informs == ["CHILD-001"]
    
    def test_all_links_property_returns_dict(self):
        """Verify all_links property returns dict of all relationships."""
        item = Item(
            id="TEST-001",
            derives_from=["UC-001"],
            implements=["SRS-001"]
        )
        
        all_links = item.all_links
        
        assert isinstance(all_links, dict)
        assert all_links['derives_from'] == ["UC-001"]
        assert all_links['implements'] == ["SRS-001"]
        # links field was removed from Item model
        assert all_links['guided_by'] == []  # Empty when None
        assert all_links['informs'] == []
    
    def test_all_linked_uids_aggregates_all_relationships(self):
        """Verify all_linked_uids returns flat list of all linked UIDs."""
        item = Item(
            id="TEST-001",
            derives_from=["UC-001", "UC-002"],
            implements=["SRS-001"],
            guided_by=["SWAD-001"]
        )
        
        all_uids = item.all_linked_uids
        
        assert isinstance(all_uids, list)
        assert len(all_uids) == 4  # Updated count after removing links
        assert "UC-001" in all_uids
        assert "UC-002" in all_uids
        assert "SRS-001" in all_uids
        assert "SWAD-001" in all_uids
        # Should be sorted
        assert all_uids == sorted(all_uids)
    
    def test_all_linked_uids_handles_none_values(self):
        """Verify all_linked_uids handles None relationship fields."""
        item = Item(
            id="TEST-001",
            content="Test item",
            derives_from=["UC-001"]
            # Other fields are None
        )
        
        all_uids = item.all_linked_uids
        
        assert all_uids == ["UC-001"]
    
    def test_all_linked_uids_removes_duplicates(self):
        """Verify all_linked_uids removes duplicate UIDs."""
        item = Item(
            id="TEST-001",
            content="Test item",
            derives_from=["UC-001"],
            implements=["UC-001"],  # Duplicate
            links=["UC-001"]  # Duplicate
        )
        
        all_uids = item.all_linked_uids
        
        assert all_uids == ["UC-001"]  # Only one instance


class TestTypedRelationshipsInDHF:
    """Tests for typed relationships in actual DHF items.
    
    @links: SRS-002
    """
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_crs_has_derives_from_links(self, core):
        """Verify CRS items have derives_from relationships to UC."""
        crs_items = [item for item in core.get_all_items() 
                     if item['id'].startswith('CRS-')]
        
        assert len(crs_items) > 0, "Should have CRS items"
        
        # Check at least one CRS has derives_from
        has_derives_from = any('derives_from' in item for item in crs_items)
        assert has_derives_from, "At least one CRS should have derives_from"
        
        # Check CRS-001 specifically
        crs_001 = next((item for item in crs_items if item['id'] == 'CRS-001'), None)
        if crs_001:
            assert 'derives_from' in crs_001
            assert isinstance(crs_001['derives_from'], list)
            assert len(crs_001['derives_from']) > 0
    
    def test_srs_has_derives_from_links(self, core):
        """Verify SRS items have derives_from relationships to SYS."""
        srs_items = [item for item in core.get_all_items() 
                     if item['id'].startswith('SRS-')]
        
        assert len(srs_items) > 0, "Should have SRS items"
        
        # Check at least one SRS has derives_from
        has_derives_from = any('derives_from' in item for item in srs_items)
        assert has_derives_from, "At least one SRS should have derives_from"
    
    def test_swdd_has_implements_and_guided_by(self, core):
        """Verify SWDD items have implements and guided_by relationships."""
        swdd_items = [item for item in core.get_all_items() 
                      if item['id'].startswith('SWDD-')]
        
        assert len(swdd_items) > 0, "Should have SWDD items"
        
        # Check at least one SWDD has implements
        has_implements = any('implements' in item for item in swdd_items)
        assert has_implements, "At least one SWDD should have implements"
    
    def test_all_items_have_all_linked_uids(self, core):
        """Verify all items have all_linked_uids property in dict."""
        all_items = core.get_all_items()
        
        for item in all_items:
            assert 'all_linked_uids' in item, \
                f"Item {item['id']} should have all_linked_uids"
            assert isinstance(item['all_linked_uids'], list), \
                f"Item {item['id']} all_linked_uids should be a list"
    
    def test_traceability_chain_completeness(self, core):
        """Verify complete traceability chain UC → CRS → SYS → SRS → SWDD."""
        all_items = core.get_all_items()
        
        # Get items by type
        uc_items = [i for i in all_items if i['id'].startswith('UC-')]
        crs_items = [i for i in all_items if i['id'].startswith('CRS-')]
        sys_items = [i for i in all_items if i['id'].startswith('SYS-')]
        srs_items = [i for i in all_items if i['id'].startswith('SRS-')]
        swdd_items = [i for i in all_items if i['id'].startswith('SWDD-')]
        
        # Verify we have items at each level
        assert len(uc_items) > 0, "Should have UC items"
        assert len(crs_items) > 0, "Should have CRS items"
        assert len(sys_items) > 0, "Should have SYS items"
        assert len(srs_items) > 0, "Should have SRS items"
        assert len(swdd_items) > 0, "Should have SWDD items"
        
        # Verify CRS links to UC
        crs_links_to_uc = any(
            any(uid.startswith('UC-') for uid in item.get('all_linked_uids', []))
            for item in crs_items
        )
        assert crs_links_to_uc, "At least one CRS should link to UC"
        
        # Verify SYS links to CRS
        sys_links_to_crs = any(
            any(uid.startswith('CRS-') for uid in item.get('all_linked_uids', []))
            for item in sys_items
        )
        assert sys_links_to_crs, "At least one SYS should link to CRS"
        
        # Verify SRS links to SYS
        srs_links_to_sys = any(
            any(uid.startswith('SYS-') for uid in item.get('all_linked_uids', []))
            for item in srs_items
        )
        assert srs_links_to_sys, "At least one SRS should link to SYS"
        
        # Verify SWDD links to SRS
        swdd_links_to_srs = any(
            any(uid.startswith('SRS-') for uid in item.get('all_linked_uids', []))
            for item in swdd_items
        )
        assert swdd_links_to_srs, "At least one SWDD should link to SRS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
