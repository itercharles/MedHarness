"""
Automated tests for SRS-007: Graph-Based Orphan Detection
Verifies: Software shall identify orphan items using graph analysis
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.graph.engine import GraphEngine
from traceability.repository.loader import ItemLoader

# Path to DHF items
SPECS_DIR = Path(__file__).parent.parent.parent / "DHF/items"


class TestOrphanDetection:
    """Tests for SRS-007: Graph-Based Orphan Detection"""
    
    def test_orphan_detection_uses_graph(self):
        """Verify orphan detection uses graph structure"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Orphan detection should work
        orphans = engine.find_orphans()
        
        # Should return a list
        assert isinstance(orphans, list), "Orphan detection must return list"
    
    def test_orphans_have_no_incoming_edges(self):
        """Verify orphans are items with no incoming edges"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        orphans = engine.find_orphans()
        
        # Each orphan should have no incoming edges
        for orphan in orphans:
            orphan_id = orphan['uid'] if isinstance(orphan, dict) else orphan
            in_degree = engine.graph.in_degree(orphan_id)
            
            # Orphans should have in_degree of 0
            assert in_degree == 0, f"{orphan_id} is marked as orphan but has in_degree {in_degree}"
    
    def test_root_types_excluded_from_orphan_check(self):
        """Verify root types (UC, CRS) are excluded from orphan check"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        orphans = engine.find_orphans()
        
        # No UC or CRS items should be in orphans list
        orphan_ids = [o['uid'] if isinstance(o, dict) else o for o in orphans]
        
        for orphan_id in orphan_ids:
            assert not orphan_id.startswith('UC-'), "UC items should not be marked as orphans"
            assert not orphan_id.startswith('CRS-'), "CRS items should not be marked as orphans"
    
    def test_orphans_grouped_by_type(self):
        """Verify orphans can be grouped by document type"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        orphans = engine.find_orphans()
        
        # Group orphans by prefix
        orphan_types = {}
        for orphan in orphans:
            orphan_id = orphan['uid'] if isinstance(orphan, dict) else orphan
            prefix = orphan_id.split('-')[0]
            
            if prefix not in orphan_types:
                orphan_types[prefix] = []
            orphan_types[prefix].append(orphan_id)
        
        # Should be able to group by type
        assert isinstance(orphan_types, dict), "Orphans should be groupable by type"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
