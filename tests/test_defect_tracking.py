"""Tests for defect tracking functionality."""

import pytest
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from traceability.models.defect import Defect, DefectStatus, DefectSeverity
from traceability.defect.defect_tracker import DefectTracker
from traceability.defect.defect_workflow import DefectWorkflow


@pytest.fixture
def temp_dhf():
    """Create a temporary DHF directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def defect_tracker(temp_dhf):
    """Create a DefectTracker instance for testing."""
    return DefectTracker(temp_dhf)


class TestDefectModel:
    """Test Defect Pydantic model."""
    
    def test_create_minimal_defect(self):
        """Test creating a defect with minimal required fields."""
        defect = Defect(
            id="DEF-001",
            title="Test defect",
            description="This is a test defect",
            severity=DefectSeverity.MAJOR,
            reported_by="Test User"
        )
        
        assert defect.id == "DEF-001"
        assert defect.title == "Test defect"
        assert defect.severity == DefectSeverity.MAJOR
        assert defect.status == DefectStatus.OPEN  # Default status
    
    def test_create_full_defect(self):
        """Test creating a defect with all fields."""
        defect = Defect(
            id="DEF-002",
            title="Critical bug",
            description="System crashes on startup",
            severity=DefectSeverity.CRITICAL,
            status=DefectStatus.INVESTIGATING,
            reported_by="John Doe",
            assigned_to="Jane Smith",
            affected_items=["SYS-001", "TC-001"],
            steps_to_reproduce="1. Start app\n2. Click button\n3. Crash",
            environment="production",
            root_cause="Null pointer exception",
            resolution="Added null check",
            tags=["crash", "critical"]
        )
        
        assert defect.severity == DefectSeverity.CRITICAL
        assert defect.assigned_to == "Jane Smith"
        assert len(defect.affected_items) == 2
        assert "crash" in defect.tags


class TestDefectTracker:
    """Test DefectTracker CRUD operations."""
    
    def test_create_defect(self, defect_tracker):
        """Test creating a new defect."""
        data = {
            "title": "Test defect",
            "description": "This is a test",
            "severity": "major",
            "reported_by": "Test User"
        }
        
        defect = defect_tracker.create_defect(data)
        
        assert defect.id == "DEF-001"  # First defect
        assert defect.title == "Test defect"
        assert defect.severity == DefectSeverity.MAJOR
    
    def test_get_defect(self, defect_tracker):
        """Test retrieving a defect by ID."""
        # Create a defect first
        data = {
            "title": "Test defect",
            "description": "This is a test",
            "severity": "minor",
            "reported_by": "Test User"
        }
        created = defect_tracker.create_defect(data)
        
        # Retrieve it
        retrieved = defect_tracker.get_defect(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title
    
    def test_get_nonexistent_defect(self, defect_tracker):
        """Test retrieving a defect that doesn't exist."""
        defect = defect_tracker.get_defect("DEF-999")
        assert defect is None
    
    def test_list_defects(self, defect_tracker):
        """Test listing all defects."""
        # Create multiple defects
        for i in range(3):
            defect_tracker.create_defect({
                "title": f"Defect {i}",
                "description": f"Description {i}",
                "severity": "major",
                "reported_by": "Test User"
            })
        
        defects = defect_tracker.list_defects()
        assert len(defects) == 3
    
    def test_list_defects_with_filters(self, defect_tracker):
        """Test listing defects with filters."""
        # Create defects with different severities
        defect_tracker.create_defect({
            "title": "Critical defect",
            "description": "Critical issue",
            "severity": "critical",
            "reported_by": "User1"
        })
        defect_tracker.create_defect({
            "title": "Minor defect",
            "description": "Minor issue",
            "severity": "minor",
            "reported_by": "User2"
        })
        
        # Filter by severity
        critical_defects = defect_tracker.list_defects(severity=DefectSeverity.CRITICAL)
        assert len(critical_defects) == 1
        assert critical_defects[0].severity == DefectSeverity.CRITICAL
    
    def test_update_defect(self, defect_tracker):
        """Test updating a defect."""
        # Create a defect
        defect = defect_tracker.create_defect({
            "title": "Original title",
            "description": "Original description",
            "severity": "major",
            "reported_by": "Test User"
        })
        
        # Update it
        updated = defect_tracker.update_defect(
            defect.id,
            {"title": "Updated title", "assigned_to": "Jane Doe"}
        )
        
        assert updated is not None
        assert updated.title == "Updated title"
        assert updated.assigned_to == "Jane Doe"


class TestDefectWorkflow:
    """Test DefectWorkflow state transitions."""
    
    def test_assign_defect(self, defect_tracker):
        """Test assigning a defect."""
        # Create a defect
        defect = defect_tracker.create_defect({
            "title": "Test defect",
            "description": "Test",
            "severity": "major",
            "reported_by": "User1"
        })
        
        # Assign it
        success, message = DefectWorkflow.assign_defect(
            defect_tracker,
            defect.id,
            "Jane Doe",
            "Manager"
        )
        
        assert success is True
        assert "assigned" in message.lower()
        
        # Verify assignment
        updated = defect_tracker.get_defect(defect.id)
        assert updated.assigned_to == "Jane Doe"
    
    def test_start_investigation(self, defect_tracker):
        """Test starting investigation."""
        defect = defect_tracker.create_defect({
            "title": "Test defect",
            "description": "Test",
            "severity": "major",
            "reported_by": "User1"
        })
        
        success, message = DefectWorkflow.start_investigation(
            defect_tracker,
            defect.id,
            "Investigator"
        )
        
        assert success is True
        
        updated = defect_tracker.get_defect(defect.id)
        assert updated.status == DefectStatus.INVESTIGATING
    
    def test_resolve_defect(self, defect_tracker):
        """Test resolving a defect."""
        # Create and start investigating
        defect = defect_tracker.create_defect({
            "title": "Test defect",
            "description": "Test",
            "severity": "major",
            "reported_by": "User1"
        })
        DefectWorkflow.start_investigation(defect_tracker, defect.id, "User1")
        
        # Resolve it
        success, message = DefectWorkflow.resolve_defect(
            defect_tracker,
            defect.id,
            "Root cause: bad code",
            "Fixed the code",
            "Developer"
        )
        
        assert success is True
        
        updated = defect_tracker.get_defect(defect.id)
        assert updated.status == DefectStatus.RESOLVED
        assert updated.root_cause == "Root cause: bad code"
        assert updated.resolution == "Fixed the code"
    
    def test_verify_and_close_defect(self, defect_tracker):
        """Test verifying and closing a defect."""
        # Create, investigate, and resolve
        defect = defect_tracker.create_defect({
            "title": "Test defect",
            "description": "Test",
            "severity": "major",
            "reported_by": "User1"
        })
        DefectWorkflow.start_investigation(defect_tracker, defect.id, "User1")
        DefectWorkflow.resolve_defect(
            defect_tracker, defect.id,
            "Root cause", "Resolution", "User1"
        )
        
        # Verify
        success, _ = DefectWorkflow.verify_resolution(
            defect_tracker,
            defect.id,
            "Tested and works",
            "Tester"
        )
        assert success is True
        
        updated = defect_tracker.get_defect(defect.id)
        assert updated.status == DefectStatus.VERIFIED
        
        # Close
        success, _ = DefectWorkflow.close_defect(
            defect_tracker,
            defect.id,
            "Manager"
        )
        assert success is True
        
        final = defect_tracker.get_defect(defect.id)
        assert final.status == DefectStatus.CLOSED
    
    def test_invalid_transition(self, defect_tracker):
        """Test that invalid state transitions are rejected."""
        defect = defect_tracker.create_defect({
            "title": "Test defect",
            "description": "Test",
            "severity": "major",
            "reported_by": "User1"
        })
        
        # Try to verify without resolving first
        success, message = DefectWorkflow.verify_resolution(
            defect_tracker,
            defect.id,
            "Verification",
            "Tester"
        )
        
        assert success is False
        assert "invalid transition" in message.lower()
    
    def test_defer_defect(self, defect_tracker):
        """Test deferring a defect."""
        defect = defect_tracker.create_defect({
            "title": "Test defect",
            "description": "Test",
            "severity": "minor",
            "reported_by": "User1"
        })
        
        success, message = DefectWorkflow.defer_defect(
            defect_tracker,
            defect.id,
            "Not critical, defer to next release",
            "Manager"
        )
        
        assert success is True
        
        updated = defect_tracker.get_defect(defect.id)
        assert updated.status == DefectStatus.DEFERRED
        assert any("Deferred" in comment for comment in updated.comments)
    
    def test_reopen_defect(self, defect_tracker):
        """Test reopening a closed defect."""
        # Create, investigate, resolve, verify, and close
        defect = defect_tracker.create_defect({
            "title": "Test defect",
            "description": "Test",
            "severity": "major",
            "reported_by": "User1"
        })
        DefectWorkflow.start_investigation(defect_tracker, defect.id, "User1")
        DefectWorkflow.resolve_defect(defect_tracker, defect.id, "RC", "Res", "User1")
        DefectWorkflow.verify_resolution(defect_tracker, defect.id, "Ver", "User1")
        DefectWorkflow.close_defect(defect_tracker, defect.id, "User1")
        
        # Reopen
        success, message = DefectWorkflow.reopen_defect(
            defect_tracker,
            defect.id,
            "Issue still occurs",
            "User2"
        )
        
        assert success is True
        
        updated = defect_tracker.get_defect(defect.id)
        assert updated.status == DefectStatus.REOPENED
        assert any("Reopened" in comment for comment in updated.comments)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
