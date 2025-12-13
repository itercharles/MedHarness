"""Review workflow state machine."""

from typing import Dict, Tuple, Optional
from datetime import datetime
from ..models.review import ReviewStatus


class ReviewWorkflow:
    """
    Review workflow state machine.
    
    Manages state transitions for review lifecycle:
    pending → in_review → approved/rejected/needs_revision
    """
    
    # Valid state transitions
    VALID_TRANSITIONS: Dict[ReviewStatus, list[ReviewStatus]] = {
        ReviewStatus.pending: [ReviewStatus.in_review],
        ReviewStatus.in_review: [ReviewStatus.approved, ReviewStatus.rejected, ReviewStatus.needs_revision],
        ReviewStatus.needs_revision: [ReviewStatus.in_review],
        ReviewStatus.approved: [],  # Terminal state
        ReviewStatus.rejected: [],  # Terminal state
    }
    
    @staticmethod
    def validate_transition(from_status: ReviewStatus, to_status: ReviewStatus) -> Tuple[bool, str]:
        """
        Validate if a state transition is allowed.
        
        Args:
            from_status: Current status
            to_status: Desired status
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if to_status in ReviewWorkflow.VALID_TRANSITIONS.get(from_status, []):
            return True, ""
        
        return False, f"Invalid transition from {from_status} to {to_status}"
    
    @staticmethod
    def start_review(tracker, review_id: str) -> Tuple[bool, str]:
        """
        Start a review (pending → in_review).
        
        Args:
            tracker: ReviewTracker instance
            review_id: Review ID
            
        Returns:
            Tuple of (success, message)
        """
        review = tracker.get_review(review_id)
        if not review:
            return False, f"Review {review_id} not found"
        
        valid, error = ReviewWorkflow.validate_transition(review.status, ReviewStatus.in_review)
        if not valid:
            return False, error
        
        tracker.update_review(review_id, {
            'status': ReviewStatus.in_review,
            'assigned_date': datetime.now()
        })
        
        return True, f"Review {review_id} started"
    
    @staticmethod
    def approve_review(
        tracker,
        review_id: str,
        comments: str,
        signature: Optional[str] = None,
        author: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Approve a review (in_review → approved).
        
        Args:
            tracker: ReviewTracker instance
            review_id: Review ID
            comments: Approval comments
            signature: Optional digital signature
            author: Author for git commit
            
        Returns:
            Tuple of (success, message)
        """
        review = tracker.get_review(review_id)
        if not review:
            return False, f"Review {review_id} not found"
        
        valid, error = ReviewWorkflow.validate_transition(review.status, ReviewStatus.approved)
        if not valid:
            return False, error
        
        tracker.update_review(review_id, {
            'status': ReviewStatus.approved,
            'comments': comments,
            'approval_signature': signature,
            'completed_date': datetime.now()
        }, author=author)
        
        return True, f"Review {review_id} approved by {review.reviewer}"
    
    @staticmethod
    def reject_review(
        tracker,
        review_id: str,
        comments: str,
        author: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Reject a review (in_review → rejected).
        
        Args:
            tracker: ReviewTracker instance
            review_id: Review ID
            comments: Rejection reason
            author: Author for git commit
            
        Returns:
            Tuple of (success, message)
        """
        review = tracker.get_review(review_id)
        if not review:
            return False, f"Review {review_id} not found"
        
        valid, error = ReviewWorkflow.validate_transition(review.status, ReviewStatus.rejected)
        if not valid:
            return False, error
        
        tracker.update_review(review_id, {
            'status': ReviewStatus.rejected,
            'comments': comments,
            'completed_date': datetime.now()
        }, author=author)
        
        return True, f"Review {review_id} rejected"
    
    @staticmethod
    def request_revision(
        tracker,
        review_id: str,
        comments: str,
        author: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Request revision (in_review → needs_revision).
        
        Args:
            tracker: ReviewTracker instance
            review_id: Review ID
            comments: Revision request comments
            author: Author for git commit
            
        Returns:
            Tuple of (success, message)
        """
        review = tracker.get_review(review_id)
        if not review:
            return False, f"Review {review_id} not found"
        
        valid, error = ReviewWorkflow.validate_transition(review.status, ReviewStatus.needs_revision)
        if not valid:
            return False, error
        
        tracker.update_review(review_id, {
            'status': ReviewStatus.needs_revision,
            'comments': comments
        }, author=author)
        
        return True, f"Review {review_id} needs revision"
    
    @staticmethod
    def resubmit_review(
        tracker,
        review_id: str,
        author: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Resubmit review after revision (needs_revision → in_review).
        
        Args:
            tracker: ReviewTracker instance
            review_id: Review ID
            author: Author for git commit
            
        Returns:
            Tuple of (success, message)
        """
        review = tracker.get_review(review_id)
        if not review:
            return False, f"Review {review_id} not found"
        
        valid, error = ReviewWorkflow.validate_transition(review.status, ReviewStatus.in_review)
        if not valid:
            return False, error
        
        tracker.update_review(review_id, {
            'status': ReviewStatus.in_review,
            'assigned_date': datetime.now()
        }, author=author)
        
        return True, f"Review {review_id} resubmitted for review"
