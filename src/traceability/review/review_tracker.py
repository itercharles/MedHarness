"""Review tracker for CRUD operations."""

from pathlib import Path
from typing import Optional, List
import yaml
from datetime import datetime
from ..models.review import Review, ReviewStatus
from ..repository.git import GitRepository


class ReviewTracker:
    """
    Manages CRUD operations for reviews.
    
    Reviews are stored as YAML files in DHF/reviews/ directory.
    """
    
    def __init__(self, dhf_root: Path, git_repo: Optional[GitRepository] = None):
        """
        Initialize review tracker.
        
        Args:
            dhf_root: Path to DHF root directory
            git_repo: Optional GitRepository for version control
        """
        self.dhf_root = Path(dhf_root)
        self.reviews_dir = self.dhf_root / "reviews"
        self.reviews_dir.mkdir(parents=True, exist_ok=True)
        self.git_repo = git_repo
    
    def _generate_next_id(self) -> str:
        """
        Generate next review ID.
        
        Returns:
            Next review ID (e.g., REV-001, REV-002)
        """
        existing_reviews = list(self.reviews_dir.glob("REV-*.yaml"))
        if not existing_reviews:
            return "REV-001"
        
        # Extract numbers from existing IDs
        numbers = []
        for review_file in existing_reviews:
            try:
                num = int(review_file.stem.split('-')[1])
                numbers.append(num)
            except (IndexError, ValueError):
                continue
        
        next_num = max(numbers) + 1 if numbers else 1
        return f"REV-{next_num:03d}"
    
    def create_review(
        self,
        item_id: str,
        reviewer: str,
        checklist_id: Optional[str] = None,
        author: Optional[str] = None
    ) -> Review:
        """
        Create a new review.
        
        Args:
            item_id: UID of item to review
            reviewer: Name of assigned reviewer
            checklist_id: Optional checklist ID
            author: Author for git commit
            
        Returns:
            Created Review object
        """
        review_id = self._generate_next_id()
        
        review = Review(
            id=review_id,
            item_id=item_id,
            reviewer=reviewer,
            status=ReviewStatus.pending,
            checklist_id=checklist_id,
            created_date=datetime.now(),
            assigned_date=datetime.now()
        )
        
        # Save to YAML
        file_path = self.reviews_dir / f"{review_id}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(review.model_dump(mode='json'), f, default_flow_style=False, sort_keys=False)
        
        # Git commit
        if self.git_repo:
            commit_msg = f"Create review {review_id} for {item_id}"
            self.git_repo.commit_file(
                file_path,
                commit_msg,
                author_name=author,
                author_email=f"{author}@compliantflow.local" if author else None
            )
        
        return review
    
    def get_review(self, review_id: str) -> Optional[Review]:
        """
        Get review by ID.
        
        Args:
            review_id: Review ID
            
        Returns:
            Review object or None
        """
        file_path = self.reviews_dir / f"{review_id}.yaml"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return Review.model_validate(data)
    
    def list_reviews(
        self,
        status: Optional[ReviewStatus] = None,
        reviewer: Optional[str] = None,
        item_id: Optional[str] = None
    ) -> List[Review]:
        """
        List reviews with optional filters.
        
        Args:
            status: Filter by status
            reviewer: Filter by reviewer
            item_id: Filter by item ID
            
        Returns:
            List of Review objects
        """
        reviews = []
        
        for review_file in self.reviews_dir.glob("REV-*.yaml"):
            with open(review_file, 'r') as f:
                data = yaml.safe_load(f)
            
            review = Review.model_validate(data)
            
            # Apply filters
            if status and review.status != status:
                continue
            if reviewer and review.reviewer != reviewer:
                continue
            if item_id and review.item_id != item_id:
                continue
            
            reviews.append(review)
        
        # Sort by created_date descending
        reviews.sort(key=lambda r: r.created_date, reverse=True)
        return reviews
    
    def update_review(
        self,
        review_id: str,
        updates: dict,
        author: Optional[str] = None
    ) -> Optional[Review]:
        """
        Update an existing review.
        
        Args:
            review_id: Review ID
            updates: Dictionary of fields to update
            author: Author for git commit
            
        Returns:
            Updated Review object or None
        """
        review = self.get_review(review_id)
        if not review:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(review, key):
                setattr(review, key, value)
        
        # Save to YAML
        file_path = self.reviews_dir / f"{review_id}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(review.model_dump(mode='json'), f, default_flow_style=False, sort_keys=False)
        
        # Git commit
        if self.git_repo:
            commit_msg = f"Update review {review_id}"
            self.git_repo.commit_file(
                file_path,
                commit_msg,
                author_name=author,
                author_email=f"{author}@compliantflow.local" if author else None
            )
        
        return review
    
    def get_reviews_for_item(self, item_id: str) -> List[Review]:
        """
        Get all reviews for a specific item.
        
        Args:
            item_id: Item UID
            
        Returns:
            List of Review objects for the item
        """
        return self.list_reviews(item_id=item_id)
    
    def get_latest_review_for_item(self, item_id: str) -> Optional[Review]:
        """
        Get the most recent review for an item.
        
        Args:
            item_id: Item UID
            
        Returns:
            Most recent Review object or None
        """
        reviews = self.get_reviews_for_item(item_id)
        return reviews[0] if reviews else None
