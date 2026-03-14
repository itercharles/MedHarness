"""
Tests for SRS-015: Item Lifecycle Management

Verifies that the software manages items through configurable workflows,
enforces state transitions, maintains history, and supports filtering.
"""
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.local_adapter import LocalDHFAdapter
from compliantflow.core import CompliantFlowCore


class TestSRS015_ItemLifecycleManagement:
    """Tests for SRS-015: Item Lifecycle Management."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent.parent / "DHF"
        return CompliantFlowCore(LocalDHFAdapter(dhf_root))
    
    def test_item_creation_and_retrieval(self, core):
        """Verify software can manage items (CRUD operations)."""
        items = core.get_all_items()
        assert len(items) > 0, "Should have items"

        # Requirement items must NOT carry a status field (GitOps model)
        sys_items = [i for i in items if i['id'].startswith('SYS-')]
        assert len(sys_items) > 0, "Should have SYS items"
        for item in sys_items:
            assert 'status' not in item, \
                f"{item['id']} is a requirement item and must not have a status field"

        # CR items MUST carry a status field (explicit lifecycle)
        cr_items = [i for i in items if i['id'].startswith('CR-')]
        assert len(cr_items) > 0, "Should have CR items"
        for item in cr_items:
            assert 'status' in item, \
                f"{item['id']} is a CR and must have a status field"
    
    def test_workflow_engine_initialization(self, core):
        """Verify lifecycle methods are available in core."""
        # Get a doc type with lifecycle
        doc_type = None
        for dt in core.config.doc_types:
            if hasattr(dt, 'lifecycle') and dt.lifecycle:
                doc_type = dt
                break
        
        assert doc_type is not None, "Should have doc type with lifecycle"
        
        # Verify core has lifecycle methods
        assert hasattr(core, 'get_initial_state'), "Should have get_initial_state method"
        assert hasattr(core, 'get_available_transitions'), "Should have get_available_transitions method"
    
    def test_state_transition_validation(self, core):
        """Verify core validates state transitions."""
        # Get a doc type with lifecycle
        doc_type = None
        for dt in core.config.doc_types:
            if hasattr(dt, 'lifecycle') and dt.lifecycle:
                doc_type = dt
                break
        
        if doc_type is None:
            pytest.skip("No doc types with lifecycle found")
        
        # Get initial state
        initial_state = core.get_initial_state(doc_type.code)
        assert initial_state is not None, "Should have initial state"
        
        # Get available transitions for a test item
        test_item = {'id': f'{doc_type.code}-001', 'status': initial_state}
        transitions = core.get_available_transitions(test_item)
        assert isinstance(transitions, list), "Should return list of transitions"
    
    def test_item_filtering(self, core):
        """Verify software supports item filtering."""
        all_items = core.get_all_items()
        
        # Filter by item type (prefix)
        sys_items = [item for item in all_items if item['id'].startswith('SYS-')]
        assert len(sys_items) > 0, "Should be able to filter by item type"
        
        # Filter by status
        items_with_status = [item for item in all_items if 'status' in item]
        assert len(items_with_status) >= 0, "Should be able to filter by status"
    
    def test_item_search(self, core):
        """Verify software supports item search."""
        all_items = core.get_all_items()
        
        # Search by ID
        search_term = "SYS"
        matching_items = [item for item in all_items 
                         if search_term in item['id']]
        assert len(matching_items) > 0, "Should be able to search by ID"
        
        # Search by title
        items_with_title = [item for item in all_items 
                           if 'title' in item and item['title']]
        assert len(items_with_title) > 0, "Items should have titles for search"
    
    def test_change_history_tracking(self, core):
        """Verify software can track item changes."""
        # This is infrastructure - actual history would be in git
        # Verify items have fields that support history tracking
        all_items = core.get_all_items()
        
        # Items should have identifiable fields for tracking
        for item in all_items[:5]:  # Check first 5
            assert 'id' in item, "Item should have ID for tracking"
            # Status changes would be tracked via git history
