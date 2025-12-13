"""Review workflow data models."""

from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    """Review status enumeration."""
    pending = "pending"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    needs_revision = "needs_revision"


class Review(BaseModel):
    """
    Review model for tracking item reviews.
    
    Reviews are separate from items to maintain clean separation
    between product data (items) and process data (reviews).
    """
    id: str = Field(..., description="Unique review identifier (e.g., REV-001)")
    item_id: str = Field(..., description="UID of item being reviewed")
    reviewer: str = Field(..., description="Assigned reviewer name")
    status: ReviewStatus = Field(default=ReviewStatus.pending, description="Current review status")
    checklist_id: Optional[str] = Field(None, description="Optional checklist ID for guidance")
    comments: Optional[str] = Field(None, description="Review comments")
    
    # Timestamps
    created_date: datetime = Field(default_factory=datetime.now, description="Review creation date")
    assigned_date: Optional[datetime] = Field(None, description="Date review was assigned")
    completed_date: Optional[datetime] = Field(None, description="Date review was completed")
    
    # Optional signature for approval
    approval_signature: Optional[str] = Field(None, description="Digital signature for approval")
    
    class Config:
        use_enum_values = True


class GuidancePoint(BaseModel):
    """
    Guidance point for review checklists.
    
    These are suggestions to help reviewers, not mandatory questions.
    """
    id: str = Field(..., description="Point identifier")
    text: str = Field(..., description="Guidance text")
    notes: Optional[str] = Field(None, description="Optional reviewer notes")


class ReviewChecklist(BaseModel):
    """
    Review checklist model.
    
    Checklists provide optional guidance for reviewers.
    They are not mandatory but help ensure consistent reviews.
    """
    id: str = Field(..., description="Checklist identifier")
    name: str = Field(..., description="Checklist name")
    description: Optional[str] = Field(None, description="Purpose of this checklist")
    applicable_to: List[str] = Field(default_factory=list, description="Document type codes this applies to")
    guidance_points: List[GuidancePoint] = Field(default_factory=list, description="List of guidance points")
