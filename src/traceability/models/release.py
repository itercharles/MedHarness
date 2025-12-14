"""Release management models for IEC 62304 compliance."""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict


class ReleaseStatus(str, Enum):
    """Status of a release in its lifecycle."""
    PLANNING = "planning"
    DEVELOPING = "developing"
    TESTING = "testing"
    RELEASED = "released"


class Release(BaseModel):
    """
    Release model for tracking software releases.
    
    Complies with IEC 62304 §5.8 (Software Release).
    """
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )
    
    # Core identification
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    status: ReleaseStatus = Field(default=ReleaseStatus.PLANNING, description="Current status")
    
    # Dates
    release_date: Optional[date] = Field(None, description="Target or actual release date")
    created_date: datetime = Field(default_factory=datetime.now, description="When release was created")
    approved_date: Optional[datetime] = Field(None, description="When release was approved")
    released_date: Optional[datetime] = Field(None, description="When release was marked as released")
    
    # People
    created_by: str = Field(..., description="Person who created the release")
    approved_by: Optional[str] = Field(None, description="Person who approved the release")
    
    # Content - Change Requests are the primary items in a release
    included_change_requests: List[str] = Field(
        default_factory=list,
        description="List of change request IDs included in this release (e.g., CR-001, CR-002)"
    )
    
    # Optional: Additional items for traceability
    additional_items: List[str] = Field(
        default_factory=list,
        description="Optional list of other item IDs for reference (requirements, tests, etc.)"
    )
    
    # Summaries
    test_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of test results (total, passed, failed, etc.)"
    )
    defect_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of defect status (total, open, closed, critical, etc.)"
    )
    
    # Documentation
    release_notes: str = Field(
        default="",
        description="Markdown-formatted release notes"
    )
    
    # Validation
    validation_passed: bool = Field(
        default=False,
        description="Whether release passed all validation checks"
    )
    validation_report: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed validation results"
    )
    
    # Manual verifications tracking
    manual_verifications: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Track manual criteria verifications: {criterion_id: {verified_by: str, verified_date: datetime, notes: str}}"
    )
    
    # Stage approvals tracking
    stage_approvals: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Track stage transition approvals: {transition: {approved_by: str, approved_date: datetime}}"
    )
    
    # Metadata
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization (e.g., 'major', 'patch', 'hotfix')"
    )
    comments: List[str] = Field(
        default_factory=list,
        description="Additional comments or notes"
    )
