"""
Automated tests for SRS-001: Graph Data Structure
Verifies: Software shall use directed graph to represent traceability relationships
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from compliantflow.traceability.graph.engine import GraphEngine
# Removed: from utils.repository.loader import ItemLoader

# Removed: Path to DHF items
# Removed: SPECS_DIR = Path(__file__).parent.parent.parent / "DHF" / "items"


class TestGraphDataStructure:
    """Tests for SRS-001: Graph Data Structure"""
    
    def test_graph_uses_directed_edges(self, test_core, loader):
        """Verify graph uses directed edges for traceability"""
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Verify graph is directed
        assert engine.graph.is_directed(), "Graph must be directed"
    
    def test_items_are_nodes(self, test_core, loader):
        """Verify DHF items are represented as nodes"""
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Verify exact node count matches item count
        expected_node_count = len(items)
        actual_node_count = len(engine.graph.nodes())
        assert actual_node_count == expected_node_count, \
            f"Graph should have exactly {expected_node_count} nodes, got {actual_node_count}"
        
        # Verify node IDs match item IDs exactly
        item_ids = {item.uid for item in items}
        graph_nodes = set(engine.graph.nodes())
        
        assert item_ids == graph_nodes, \
            f"Graph nodes must exactly match item IDs. Missing: {item_ids - graph_nodes}, Extra: {graph_nodes - item_ids}"
    
    def test_links_are_edges(self, test_core, loader):
        """Verify links between items are represented as directed edges"""
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Use test data - we know SRS-001 links to SYS-001
        assert engine.graph.has_edge('SRS-001', 'SYS-001'), \
            "Edge must exist from SRS-001 to SYS-001"
        assert engine.graph.has_edge('SRS-002', 'SYS-001'), \
            "Edge must exist from SRS-002 to SYS-001"
    
    def test_graph_performance(self, test_core, loader):
        """Verify graph builds quickly with test data"""
        import time
        
        items = loader.load_all()
        
        # Performance test with small dataset - should be instant
        start = time.time()
        engine = GraphEngine()
        engine.build_from_items(items)
        elapsed = time.time() - start
        
        assert elapsed < 0.1, f"Graph build took {elapsed:.2f}s, should be < 0.1s for small dataset"
    
    def test_specific_parent_child_relationship(self, test_core, loader):
        """Verify specific parent-child relationship in graph (SRS-001 → SYS-001)"""
        items = loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Verify edge exists from SRS-001 to SYS-001
        assert engine.graph.has_edge("SRS-001", "SYS-001"), \
            "Edge must exist from SRS-001 to parent SYS-001"
        
        # Verify edge direction (child → parent, not parent → child)
        assert not engine.graph.has_edge("SYS-001", "SRS-001"), \
            "Edge should not exist from parent to child"
    
    def test_graph_with_mocked_simple_hierarchy(self):
        """Test graph with mocked simple parent-child hierarchy"""
        from utils.models.item import Item
        
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
        expected_nodes = {"SYS-001", "SRS-001", "SRS-002"}
        actual_nodes = set(engine.graph.nodes())
        assert actual_nodes == expected_nodes, \
            f"Graph must have exactly {expected_nodes}, got {actual_nodes}"
        
        # Verify exact edges
        assert engine.graph.has_edge("SRS-001", "SYS-001"), "SRS-001 → SYS-001 edge must exist"
        assert engine.graph.has_edge("SRS-002", "SYS-001"), "SRS-002 → SYS-001 edge must exist"
        
        # Verify edge count
        assert len(list(engine.graph.edges())) == 2, "Graph should have exactly 2 edges"
    
    def test_graph_with_circular_dependency_detection(self):
        """Test graph handles circular dependencies (edge case)"""
        from utils.models.item import Item
        
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
        expected_nodes = {"A", "B"}
        actual_nodes = set(engine.graph.nodes())
        assert actual_nodes == expected_nodes, \
            f"Graph must have exactly {expected_nodes}, got {actual_nodes}"
        
        assert engine.graph.has_edge("A", "B"), "A → B edge must exist"
        assert engine.graph.has_edge("B", "A"), "B → A edge must exist"
        
        # Verify exact edge count
        assert len(list(engine.graph.edges())) == 2, \
            f"Graph must have exactly 2 edges, got {len(list(engine.graph.edges()))}"
        
        # Verify cycle detection (if implemented)
        # Note: This is an edge case - the system should either:
        # 1. Allow cycles (valid for some traceability scenarios)
        # 2. Detect and report them
        # Current implementation allows cycles
    
    def test_graph_with_orphan_node(self):
        """Test graph with orphan node (no parent links)"""
        from utils.models.item import Item
        
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
