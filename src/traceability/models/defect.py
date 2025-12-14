"""Defect tracking models for IEC 62304 compliance."""

from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DefectStatus(str, Enum):
    """Status of a defect in its lifecycle."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    VERIFIED = "verified"
    CLOSED = "closed"
    DEFERRED = "deferred"
    REOPENED = "reopened"


class DefectSeverity(str, Enum):
    """Severity level of a defect."""
    CRITICAL = "critical"  # System crash, data loss, safety issue
    MAJOR = "major"        # Major functionality broken
    MINOR = "minor"        # Minor functionality issue
    COSMETIC = "cosmetic"  # UI/UX issue, no functional impact


class Defect(BaseModel):
    """
    Defect model for tracking software defects.
    
    Complies with IEC 62304 §9.7 (Problem Resolution Process).
    """
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )
    
    # Core identification
    id: str = Field(..., description="Unique defect identifier (e.g., DEF-001)")
    title: str = Field(..., description="Brief description of the defect")
    description: str = Field(..., description="Detailed description of the defect")
    
    # Classification
    severity: DefectSeverity = Field(..., description="Severity level")
    status: DefectStatus = Field(default=DefectStatus.OPEN, description="Current status")
    
    # People
    reported_by: str = Field(..., description="Person who reported the defect")
    assigned_to: Optional[str] = Field(None, description="Person assigned to investigate")
    
    # Relationships
    affected_items: List[str] = Field(
        default_factory=list,
        description="List of affected item IDs (requirements, tests, etc.)"
    )
    related_change_request: Optional[str] = Field(
        None,
        description="ID of related change request if one was created"
    )
    
    # Technical details
    steps_to_reproduce: Optional[str] = Field(
        None,
        description="Steps to reproduce the defect"
    )
    environment: Optional[str] = Field(
        None,
        description="Environment where defect was found (e.g., dev, test, production)"
    )
    
    # Analysis and resolution
    root_cause: Optional[str] = Field(
        None,
        description="Analysis of the root cause"
    )
    resolution: Optional[str] = Field(
        None,
        description="Description of how the defect was resolved"
    )
    verification: Optional[str] = Field(
        None,
        description="Description of how the resolution was verified"
    )
    
    # Timestamps
    reported_date: datetime = Field(
        default_factory=datetime.now,
        description="When the defect was reported"
    )
    assigned_date: Optional[datetime] = Field(
        None,
        description="When the defect was assigned"
    )
    investigation_started_date: Optional[datetime] = Field(
        None,
        description="When investigation started"
    )
    resolved_date: Optional[datetime] = Field(
        None,
        description="When the defect was resolved"
    )
    verified_date: Optional[datetime] = Field(
        None,
        description="When the resolution was verified"
    )
    closed_date: Optional[datetime] = Field(
        None,
        description="When the defect was closed"
    )
    
    # Additional metadata
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization (e.g., 'ui', 'performance', 'security')"
    )
    comments: List[str] = Field(
        default_factory=list,
        description="Additional comments or notes"
    )
