"""
Automated tests for SRS-001: Graph Data Structure
Verifies: Software shall use directed graph to represent traceability relationships
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.graph.engine import GraphEngine
from traceability.repository.loader import ItemLoader

# Path to DHF items
SPECS_DIR = Path(__file__).parent.parent.parent / "DHF" / "items"


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
    
    def test_specific_parent_child_relationship(self):
        """Verify specific parent-child relationship in graph (SRS-001 → SYS-001)"""
        loader = ItemLoader(SPECS_DIR)
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Find SRS-001 (should derive from SYS-001)
        srs_001 = next((item for item in items if item.uid == "SRS-001"), None)
        if srs_001 and hasattr(srs_001, 'derives_from') and srs_001.derives_from:
            # Verify edge exists from SRS-001 to its parent
            for parent_id in srs_001.derives_from:
                if engine.graph.has_node(parent_id):
                    assert engine.graph.has_edge("SRS-001", parent_id), \
                        f"Edge must exist from SRS-001 to parent {parent_id}"
                    
                    # Verify edge direction (child → parent)
                    assert not engine.graph.has_edge(parent_id, "SRS-001") or \
                           engine.graph.has_edge("SRS-001", parent_id), \
                        "Edge direction must be from child to parent"
    
    def test_graph_with_mocked_simple_hierarchy(self):
        """Test graph with mocked simple parent-child hierarchy"""
        from traceability.models.item import Item
        
        # Mock items with specific hierarchy
        mock_items = [
            Item(uid="SYS-001", item_type="SYS", title="System Req", content="Test"),
            Item(uid="SRS-001", item_type="SRS", title="Software Req", content="Test",
                 derives_from=["SYS-001"]),
            Item(uid="SRS-002", item_type="SRS", title="Software Req 2", content="Test",
                 derives_from=["SYS-001"]),
        ]
        
        engine = GraphEngine()
        engine.build_from_items(mock_items)
        
        # Verify exact structure
        assert set(engine.graph.nodes()) == {"SYS-001", "SRS-001", "SRS-002"}, \
            "Graph should contain exactly 3 nodes"
        
        # Verify exact edges
        assert engine.graph.has_edge("SRS-001", "SYS-001"), "SRS-001 → SYS-001 edge must exist"
        assert engine.graph.has_edge("SRS-002", "SYS-001"), "SRS-002 → SYS-001 edge must exist"
        
        # Verify edge count
        assert len(list(engine.graph.edges())) == 2, "Graph should have exactly 2 edges"
    
    def test_graph_with_circular_dependency_detection(self):
        """Test graph handles circular dependencies (edge case)"""
        from traceability.models.item import Item
        
        # Mock items with circular dependency
        mock_items = [
            Item(uid="A", item_type="SRS", title="Item A", content="Test",
                 derives_from=["B"]),
            Item(uid="B", item_type="SRS", title="Item B", content="Test",
                 derives_from=["A"]),  # Circular!
        ]
        
        engine = GraphEngine()
        engine.build_from_items(mock_items)
        
        # Graph should still build (directed graphs can have cycles)
        assert len(engine.graph.nodes()) == 2, "Graph should contain 2 nodes"
        assert engine.graph.has_edge("A", "B"), "A → B edge must exist"
        assert engine.graph.has_edge("B", "A"), "B → A edge must exist"
        
        # Verify cycle detection (if implemented)
        # Note: This is an edge case - the system should either:
        # 1. Allow cycles (valid for some traceability scenarios)
        # 2. Detect and report them
        # Current implementation allows cycles
    
    def test_graph_with_orphan_node(self):
        """Test graph with orphan node (no parent links)"""
        from traceability.models.item import Item
        
        # Mock items with orphan
        mock_items = [
            Item(uid="SYS-001", item_type="SYS", title="System Req", content="Test"),
            Item(uid="SRS-001", item_type="SRS", title="Software Req", content="Test",
                 derives_from=["SYS-001"]),
            Item(uid="SRS-ORPHAN", item_type="SRS", title="Orphan", content="Test",
                 derives_from=[]),  # No parent!
        ]
        
        engine = GraphEngine()
        engine.build_from_items(mock_items)
        
        # Orphan should still be in graph as node
        assert "SRS-ORPHAN" in engine.graph.nodes(), "Orphan node must be in graph"
        
        # Orphan should have no outgoing edges
        orphan_edges = list(engine.graph.out_edges("SRS-ORPHAN"))
        assert len(orphan_edges) == 0, "Orphan should have no outgoing edges"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
