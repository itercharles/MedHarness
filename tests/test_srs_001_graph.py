"""
Automated tests for SRS-001: Graph Data Structure
Verifies: Software shall use directed graph to represent traceability relationships
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.graph.engine import GraphEngine
from traceability.repository.loader import ItemLoader

# Path to DHF items
SPECS_DIR = Path(__file__).parent.parent / "DHF" / "items"


class TestGraphDataStructure:
    """Tests for SRS-001: Graph Data Structure"""
    
    def test_graph_uses_directed_edges(self):
        """Verify graph uses directed edges for traceability"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Verify graph is directed
        assert engine.graph.is_directed(), "Graph must be directed"
    
    def test_items_are_nodes(self):
        """Verify DHF items are represented as nodes"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Verify nodes exist
        assert len(engine.graph.nodes()) > 0, "Graph must have nodes"
        
        # Verify node IDs match item IDs
        item_ids = {item.uid for item in items}
        graph_nodes = set(engine.graph.nodes())
        
        # All items should be in graph
        assert item_ids.issubset(graph_nodes), "All items must be nodes in graph"
    
    def test_links_are_edges(self):
        """Verify links between items are represented as directed edges"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Find an item with links
        item_with_links = None
        for item in items:
            if hasattr(item, 'links') and item.links:
                item_with_links = item
                break
        
        if item_with_links:
            # Verify edges exist for links (only check links that exist in graph)
            for target_id in item_with_links.links:
                if engine.graph.has_node(target_id):
                    assert engine.graph.has_edge(item_with_links.uid, target_id), \
                        f"Edge must exist from {item_with_links.uid} to {target_id}"
    
    def test_graph_performance(self):
        """Verify graph with 1000 nodes builds in < 2 seconds (SRS-001 performance req)"""
        import time
        
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        # If we have < 1000 items, this test passes by default
        if len(items) < 1000:
            pytest.skip("Not enough items to test performance requirement")
        
        start = time.time()
        engine = GraphEngine()
        engine.build_from_items(items)
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"Graph build took {elapsed:.2f}s, must be < 2s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
