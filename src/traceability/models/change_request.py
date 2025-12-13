"""Change Request models for change management."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ChangeType(str, Enum):
    """Type of change being requested."""
    BUG_FIX = "bug_fix"
    ENHANCEMENT = "enhancement"
    NEW_FEATURE = "new_feature"
    DOCUMENTATION = "documentation"


class ChangePriority(str, Enum):
    """Priority level of the change."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeStatus(str, Enum):
    """Current status of the change request."""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    CANCELLED = "cancelled"


class ChangeRequest(BaseModel):
    """
    Change request for tracking modifications to the medical device software.
    
    Follows IEC 62304 change management requirements and MDCG 2020-3 guidance.
    """
    id: str = Field(..., description="Unique identifier (e.g., CR-001)")
    title: str = Field(..., description="Brief title of the change")
    description: str = Field(..., description="Detailed description of the change")
    type: ChangeType = Field(..., description="Type of change")
    priority: ChangePriority = Field(default=ChangePriority.MEDIUM, description="Priority level")
    status: ChangeStatus = Field(default=ChangeStatus.SUBMITTED, description="Current status")
    
    # Affected items
    affected_items: List[str] = Field(
        default_factory=list,
        description="List of item UIDs affected by this change"
    )
    
    # Risk assessment
    risk_assessment: Optional[str] = Field(
        None,
        description="Assessment of risks introduced by this change"
    )
    
    # Creation tracking
    created_by: str = Field(..., description="Person who created the change request")
    created_date: datetime = Field(
        default_factory=datetime.now,
        description="Date/time when change request was created"
    )
    
    # Review tracking
    reviewed_by: Optional[str] = Field(None, description="Person who reviewed the change")
    review_date: Optional[datetime] = Field(None, description="Date/time of review")
    review_comments: Optional[str] = Field(None, description="Comments from reviewer")
    
    # Implementation tracking
    implemented_date: Optional[datetime] = Field(
        None,
        description="Date/time when change was implemented"
    )
    
    # Additional metadata
    related_changes: List[str] = Field(
        default_factory=list,
        description="IDs of related change requests"
    )
    
    class Config:
        use_enum_values = True


class ChangeImpact(BaseModel):
    """
    Impact analysis results for a change request.
    
    Identifies all items affected by the change and assesses significance.
    """
    change_id: str = Field(..., description="ID of the change request")
    
    # Categorized affected items
    affected_requirements: List[str] = Field(
        default_factory=list,
        description="UIDs of affected requirements (CRS, SYS, SDS)"
    )
    affected_tests: List[str] = Field(
        default_factory=list,
        description="UIDs of affected test cases"
    )
    affected_risks: List[str] = Field(
        default_factory=list,
        description="UIDs of affected risk items"
    )
    affected_other: List[str] = Field(
        default_factory=list,
        description="UIDs of other affected items"
    )
    
    # Impact metrics
    downstream_count: int = Field(
        default=0,
        description="Total number of downstream items affected"
    )
    
    # Significance assessment (per MDCG 2020-3)
    is_significant: bool = Field(
        default=False,
        description="Whether this is a significant change per MDCG 2020-3"
    )
    significance_rationale: Optional[str] = Field(
        None,
        description="Explanation of significance determination"
    )
    
    # Impact summary
    impact_summary: Optional[str] = Field(
        None,
        description="Human-readable summary of the impact"
    )
    
    class Config:
        use_enum_values = True
