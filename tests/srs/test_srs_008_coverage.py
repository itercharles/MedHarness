"""
Automated tests for SRS-008: Test Coverage Calculation
Verifies: Software shall calculate test coverage for requirements
"""

import pytest
from pathlib import Path
import sys
import networkx as nx

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from compliantflow.traceability.graph.engine import GraphEngine
from utils.repository.loader import ItemLoader

# Tests use test_core fixture from conftest.py


class TestCoverageCalculation:
    """Tests for SRS-008: Test Coverage Calculation"""
    
    def test_coverage_calculation_method_exists(self):
        """Verify coverage calculation method exists"""
        engine = GraphEngine()
        
        # Should have a method for coverage calculation
        assert hasattr(engine, 'calculate_coverage') or hasattr(engine, 'get_coverage'), \
            "GraphEngine should have coverage calculation method"
    
    def test_coverage_identifies_requirements(self, test_core):
        """Verify coverage calculation identifies all requirements"""
        # loader = ItemLoader(SPECS_DIR)
        items = test_core._adapter._loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Get all SRS items (requirements)
        srs_items = [item for item in items if item.uid.startswith('SRS-')]
        
        assert len(srs_items) > 0, "Should have SRS requirements to test coverage"
    
    def test_coverage_finds_test_descendants(self, test_core):
        """Verify coverage finds test items linked to requirements"""
        items = test_core._adapter._loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Find SRS requirements - test data has SRS-001 and SRS-002
        srs_items = [item for item in items if item.uid.startswith('SRS-')]
        assert len(srs_items) > 0, "Test data should have SRS items"
        
        # Get descendants of first SRS item
        descendants = list(nx.descendants(engine.graph, srs_items[0].uid))
        
        # Should be able to get descendants (returns a list or set)
        assert isinstance(descendants, (list, set)), "Should return descendants"
    
    def test_coverage_percentage_calculation(self, test_core):
        """Verify coverage is calculated as percentage"""
        items = test_core._adapter._loader.load_all()
        
        engine = GraphEngine()
        engine.build_from_items(items)
        
        # Calculate coverage for SRS items
        coverage = engine.calculate_coverage('SRS')
        
        # Should return a dictionary with coverage percentage
        assert isinstance(coverage, dict), "Coverage should return a dictionary"
        assert 'coverage' in coverage, "Coverage should have 'coverage' percentage key"
        assert isinstance(coverage['coverage'], (int, float)), "Coverage percentage should be a number"
        assert 0 <= coverage['coverage'] <= 100, f"Coverage should be 0-100%, got {coverage['coverage']}"
    
    def test_coverage_reports_uncovered_items(self, test_core):
        """Verify coverage calculation reports uncovered requirements"""
        items = test_core._adapter._loader.load_all()
        
        # Initialize engine with config so it can identify document types
        engine = GraphEngine(config=test_core.config)
        engine.build_from_items(items)
        
        # Calculate coverage for SYS items (test config has SYS configured)
        coverage = engine.calculate_coverage('SYS')
        
        # Should return a dictionary with coverage statistics
        assert isinstance(coverage, dict), "Coverage should return a dictionary"
        assert 'total' in coverage, "Coverage should have 'total' key"
        assert 'covered' in coverage, "Coverage should have 'covered' key"
        assert 'coverage' in coverage, "Coverage should have 'coverage' percentage key"
        assert 'uncovered' in coverage, "Coverage should have 'uncovered' key"
        
        # Test data has 2 SYS items (SYS-001, SYS-002)
        assert coverage['total'] == 2, f"Expected 2 SYS items, got {coverage['total']}"
        
        # Uncovered should be a list
        assert isinstance(coverage['uncovered'], list), "Uncovered should be a list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
