"""Change workflow state machine."""

from typing import Dict, Tuple, Optional
from datetime import datetime
from ..models.change_request import ChangeStatus


class ChangeWorkflow:
    """
    Manages change request workflow and state transitions.
    
    Implements a state machine for change request lifecycle:
    submitted → under_review → approved/rejected → implemented
    """
    
    # Define valid state transitions
    VALID_TRANSITIONS: Dict[ChangeStatus, list[ChangeStatus]] = {
        ChangeStatus.SUBMITTED: [
            ChangeStatus.UNDER_REVIEW,
            ChangeStatus.CANCELLED
        ],
        ChangeStatus.UNDER_REVIEW: [
            ChangeStatus.APPROVED,
            ChangeStatus.REJECTED,
            ChangeStatus.CANCELLED
        ],
        ChangeStatus.APPROVED: [
            ChangeStatus.IMPLEMENTED,
            ChangeStatus.CANCELLED
        ],
        ChangeStatus.REJECTED: [
            ChangeStatus.CANCELLED
        ],
        ChangeStatus.IMPLEMENTED: [],  # Terminal state
        ChangeStatus.CANCELLED: []  # Terminal state
    }
    
    @classmethod
    def validate_transition(
        cls,
        current_status: ChangeStatus,
        new_status: ChangeStatus
    ) -> Tuple[bool, str]:
        """
        Validate if a state transition is allowed.
        
        Args:
            current_status: Current status
            new_status: Desired new status
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if new_status in cls.VALID_TRANSITIONS.get(current_status, []):
            return True, ""
        
        error_msg = (
            f"Invalid transition from {current_status.value} to {new_status.value}. "
            f"Valid transitions: {[s.value for s in cls.VALID_TRANSITIONS.get(current_status, [])]}"
        )
        return False, error_msg
    
    @classmethod
    def submit_for_review(cls, change_tracker, change_id: str) -> Tuple[bool, str]:
        """
        Move change request from SUBMITTED to UNDER_REVIEW.
        
        Args:
            change_tracker: ChangeTracker instance
            change_id: Change request ID
            
        Returns:
            Tuple of (success, message)
        """
        change_request = change_tracker.get_change_request(change_id)
        if not change_request:
            return False, f"Change request {change_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            change_request.status,
            ChangeStatus.UNDER_REVIEW
        )
        if not is_valid:
            return False, error_msg
        
        # Update status
        change_tracker.update_change_request(
            change_id,
            {'status': ChangeStatus.UNDER_REVIEW}
        )
        
        return True, f"Change request {change_id} submitted for review"
    
    @classmethod
    def approve_change(
        cls,
        change_tracker,
        change_id: str,
        reviewer: str,
        comments: str = ""
    ) -> Tuple[bool, str]:
        """
        Approve a change request.
        
        Args:
            change_tracker: ChangeTracker instance
            change_id: Change request ID
            reviewer: Name of reviewer
            comments: Review comments
            
        Returns:
            Tuple of (success, message)
        """
        change_request = change_tracker.get_change_request(change_id)
        if not change_request:
            return False, f"Change request {change_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            change_request.status,
            ChangeStatus.APPROVED
        )
        if not is_valid:
            return False, error_msg
        
        # Update status and review info
        change_tracker.update_change_request(
            change_id,
            {
                'status': ChangeStatus.APPROVED,
                'reviewed_by': reviewer,
                'review_date': datetime.now(),
                'review_comments': comments
            },
            author=reviewer
        )
        
        return True, f"Change request {change_id} approved by {reviewer}"
    
    @classmethod
    def reject_change(
        cls,
        change_tracker,
        change_id: str,
        reviewer: str,
        comments: str
    ) -> Tuple[bool, str]:
        """
        Reject a change request.
        
        Args:
            change_tracker: ChangeTracker instance
            change_id: Change request ID
            reviewer: Name of reviewer
            comments: Reason for rejection
            
        Returns:
            Tuple of (success, message)
        """
        change_request = change_tracker.get_change_request(change_id)
        if not change_request:
            return False, f"Change request {change_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            change_request.status,
            ChangeStatus.REJECTED
        )
        if not is_valid:
            return False, error_msg
        
        # Update status and review info
        change_tracker.update_change_request(
            change_id,
            {
                'status': ChangeStatus.REJECTED,
                'reviewed_by': reviewer,
                'review_date': datetime.now(),
                'review_comments': comments
            },
            author=reviewer
        )
        
        return True, f"Change request {change_id} rejected by {reviewer}"
    
    @classmethod
    def mark_implemented(
        cls,
        change_tracker,
        change_id: str,
        author: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Mark a change request as implemented.
        
        Args:
            change_tracker: ChangeTracker instance
            change_id: Change request ID
            author: Name of person marking as implemented
            
        Returns:
            Tuple of (success, message)
        """
        change_request = change_tracker.get_change_request(change_id)
        if not change_request:
            return False, f"Change request {change_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            change_request.status,
            ChangeStatus.IMPLEMENTED
        )
        if not is_valid:
            return False, error_msg
        
        # Update status
        change_tracker.update_change_request(
            change_id,
            {
                'status': ChangeStatus.IMPLEMENTED,
                'implemented_date': datetime.now()
            },
            author=author
        )
        
        return True, f"Change request {change_id} marked as implemented"
    
    @classmethod
    def cancel_change(
        cls,
        change_tracker,
        change_id: str,
        author: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Cancel a change request.
        
        Args:
            change_tracker: ChangeTracker instance
            change_id: Change request ID
            author: Name of person cancelling
            
        Returns:
            Tuple of (success, message)
        """
        change_request = change_tracker.get_change_request(change_id)
        if not change_request:
            return False, f"Change request {change_id} not found"
        
        # Validate transition
        is_valid, error_msg = cls.validate_transition(
            change_request.status,
            ChangeStatus.CANCELLED
        )
        if not is_valid:
            return False, error_msg
        
        # Update status
        change_tracker.update_change_request(
            change_id,
            {'status': ChangeStatus.CANCELLED},
            author=author
        )
        
        return True, f"Change request {change_id} cancelled"


# Add missing import
from typing import Optional
