"""Defect workflow management for state transitions."""

from typing import Tuple, Dict
from datetime import datetime

from ..models.defect import DefectStatus
from .defect_tracker import DefectTracker


class DefectWorkflow:
    """
    Manages defect workflow and state transitions.
    
    Implements a state machine for defect lifecycle:
    open → investigating → resolved → verified → closed
    
    Also supports:
    - Deferring defects to future releases
    - Reopening closed/resolved defects
    """
    
    # Define valid state transitions
    VALID_TRANSITIONS: Dict[DefectStatus, list[DefectStatus]] = {
        DefectStatus.OPEN: [
            DefectStatus.INVESTIGATING,
            DefectStatus.DEFERRED,
            DefectStatus.CLOSED  # Can close if duplicate/invalid
        ],
        DefectStatus.INVESTIGATING: [
            DefectStatus.RESOLVED,
            DefectStatus.DEFERRED,
            DefectStatus.REOPENED
        ],
        DefectStatus.RESOLVED: [
            DefectStatus.VERIFIED,
            DefectStatus.REOPENED
        ],
        DefectStatus.VERIFIED: [
            DefectStatus.CLOSED,
            DefectStatus.REOPENED
        ],
        DefectStatus.DEFERRED: [
            DefectStatus.OPEN,
            DefectStatus.INVESTIGATING,
            DefectStatus.CLOSED
        ],
        DefectStatus.CLOSED: [
            DefectStatus.REOPENED
        ],
        DefectStatus.REOPENED: [
            DefectStatus.INVESTIGATING,
            DefectStatus.RESOLVED
        ]
    }
    
    @classmethod
    def validate_transition(
        cls,
        current_status: DefectStatus,
        new_status: DefectStatus
    ) -> Tuple[bool, str]:
        """
        Validate if a status transition is allowed.
        
        Args:
            current_status: Current defect status
            new_status: Desired new status
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if new_status in cls.VALID_TRANSITIONS.get(current_status, []):
            return True, ""
        
        return False, (
            f"Invalid transition from {current_status.value} to {new_status.value}. "
            f"Valid transitions: {[s.value for s in cls.VALID_TRANSITIONS.get(current_status, [])]}"
        )
    
    @classmethod
    def assign_defect(
        cls,
        defect_tracker: DefectTracker,
        defect_id: str,
        assigned_to: str,
        author: str
    ) -> Tuple[bool, str]:
        """
        Assign defect to an investigator.
        
        Args:
            defect_tracker: DefectTracker instance
            defect_id: Defect ID
            assigned_to: Person to assign to
            author: Person making the assignment
            
        Returns:
            Tuple of (success, message)
        """
        defect = defect_tracker.get_defect(defect_id)
        if not defect:
            return False, f"Defect {defect_id} not found"
        
        updates = {
            'assigned_to': assigned_to,
            'assigned_date': datetime.now()
        }
        
        defect_tracker.update_defect(defect_id, updates, author=author)
        return True, f"Defect {defect_id} assigned to {assigned_to}"
    
    @classmethod
    def start_investigation(
        cls,
        defect_tracker: DefectTracker,
        defect_id: str,
        author: str
    ) -> Tuple[bool, str]:
        """
        Start investigating a defect.
        
        Args:
            defect_tracker: DefectTracker instance
            defect_id: Defect ID
            author: Person starting investigation
            
        Returns:
            Tuple of (success, message)
        """
        defect = defect_tracker.get_defect(defect_id)
        if not defect:
            return False, f"Defect {defect_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            defect.status,
            DefectStatus.INVESTIGATING
        )
        if not is_valid:
            return False, error_msg
        
        updates = {
            'status': DefectStatus.INVESTIGATING,
            'investigation_started_date': datetime.now()
        }
        
        defect_tracker.update_defect(defect_id, updates, author=author)
        return True, f"Investigation started for defect {defect_id}"
    
    @classmethod
    def resolve_defect(
        cls,
        defect_tracker: DefectTracker,
        defect_id: str,
        root_cause: str,
        resolution: str,
        author: str
    ) -> Tuple[bool, str]:
        """
        Mark defect as resolved.
        
        Args:
            defect_tracker: DefectTracker instance
            defect_id: Defect ID
            root_cause: Root cause analysis
            resolution: How it was resolved
            author: Person resolving the defect
            
        Returns:
            Tuple of (success, message)
        """
        defect = defect_tracker.get_defect(defect_id)
        if not defect:
            return False, f"Defect {defect_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            defect.status,
            DefectStatus.RESOLVED
        )
        if not is_valid:
            return False, error_msg
        
        updates = {
            'status': DefectStatus.RESOLVED,
            'root_cause': root_cause,
            'resolution': resolution,
            'resolved_date': datetime.now()
        }
        
        defect_tracker.update_defect(defect_id, updates, author=author)
        return True, f"Defect {defect_id} marked as resolved"
    
    @classmethod
    def verify_resolution(
        cls,
        defect_tracker: DefectTracker,
        defect_id: str,
        verification: str,
        author: str
    ) -> Tuple[bool, str]:
        """
        Verify that defect resolution works.
        
        Args:
            defect_tracker: DefectTracker instance
            defect_id: Defect ID
            verification: Verification details
            author: Person verifying the resolution
            
        Returns:
            Tuple of (success, message)
        """
        defect = defect_tracker.get_defect(defect_id)
        if not defect:
            return False, f"Defect {defect_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            defect.status,
            DefectStatus.VERIFIED
        )
        if not is_valid:
            return False, error_msg
        
        updates = {
            'status': DefectStatus.VERIFIED,
            'verification': verification,
            'verified_date': datetime.now()
        }
        
        defect_tracker.update_defect(defect_id, updates, author=author)
        return True, f"Defect {defect_id} resolution verified"
    
    @classmethod
    def close_defect(
        cls,
        defect_tracker: DefectTracker,
        defect_id: str,
        author: str
    ) -> Tuple[bool, str]:
        """
        Close a defect.
        
        Args:
            defect_tracker: DefectTracker instance
            defect_id: Defect ID
            author: Person closing the defect
            
        Returns:
            Tuple of (success, message)
        """
        defect = defect_tracker.get_defect(defect_id)
        if not defect:
            return False, f"Defect {defect_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            defect.status,
            DefectStatus.CLOSED
        )
        if not is_valid:
            return False, error_msg
        
        updates = {
            'status': DefectStatus.CLOSED,
            'closed_date': datetime.now()
        }
        
        defect_tracker.update_defect(defect_id, updates, author=author)
        return True, f"Defect {defect_id} closed"
    
    @classmethod
    def defer_defect(
        cls,
        defect_tracker: DefectTracker,
        defect_id: str,
        reason: str,
        author: str
    ) -> Tuple[bool, str]:
        """
        Defer a defect to future release.
        
        Args:
            defect_tracker: DefectTracker instance
            defect_id: Defect ID
            reason: Reason for deferring
            author: Person deferring the defect
            
        Returns:
            Tuple of (success, message)
        """
        defect = defect_tracker.get_defect(defect_id)
        if not defect:
            return False, f"Defect {defect_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            defect.status,
            DefectStatus.DEFERRED
        )
        if not is_valid:
            return False, error_msg
        
        # Add reason to comments
        comments = defect.comments.copy()
        comments.append(f"Deferred: {reason}")
        
        updates = {
            'status': DefectStatus.DEFERRED,
            'comments': comments
        }
        
        defect_tracker.update_defect(defect_id, updates, author=author)
        return True, f"Defect {defect_id} deferred"
    
    @classmethod
    def reopen_defect(
        cls,
        defect_tracker: DefectTracker,
        defect_id: str,
        reason: str,
        author: str
    ) -> Tuple[bool, str]:
        """
        Reopen a closed or resolved defect.
        
        Args:
            defect_tracker: DefectTracker instance
            defect_id: Defect ID
            reason: Reason for reopening
            author: Person reopening the defect
            
        Returns:
            Tuple of (success, message)
        """
        defect = defect_tracker.get_defect(defect_id)
        if not defect:
            return False, f"Defect {defect_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            defect.status,
            DefectStatus.REOPENED
        )
        if not is_valid:
            return False, error_msg
        
        # Add reason to comments
        comments = defect.comments.copy()
        comments.append(f"Reopened: {reason}")
        
        updates = {
            'status': DefectStatus.REOPENED,
            'comments': comments
        }
        
        defect_tracker.update_defect(defect_id, updates, author=author)
        return True, f"Defect {defect_id} reopened"
