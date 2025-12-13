"""Compliance models."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class PolicyAutomation(BaseModel):
    """Configuration for automated checks."""
    check: str = Field(..., description="Name of the check function to run")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the check")

class Policy(BaseModel):
    """A single regulatory policy."""
    id: str = Field(..., description="Unique ID of the policy (e.g. 5.1.1.a)")
    section: str = Field(..., description="Section of the standard")
    text: str = Field(..., description="Normative text of the requirement")
    status: Literal['approved', 'draft', 'rejected'] = Field(default='draft', description="Approval status")
    automation: Optional[PolicyAutomation] = Field(None, description="Automation configuration")

class PolicyGroup(BaseModel):
    """A collection of policies defining a standard, procedure, or guideline."""
    id: str = Field(..., description="ID of the policy group (e.g. IEC_62304)")
    title: str = Field(..., description="Title of the document")
    type: Literal['regulation', 'procedure', 'standard'] = Field(default='regulation', description="Type of governance document")
    version: Optional[str] = Field(None, description="Version string")
    policies: List[Policy] = Field(..., description="List of policies")

class PolicyResult(BaseModel):
    """Result of a single policy check."""
    policy_id: str
    passed: bool
    details: str
    evidence: Optional[Dict[str, Any]] = None

class ComplianceReport(BaseModel):
    """Full compliance report for a policy group."""
    source_id: str
    total_policies: int
    passed_policies: int
    results: List[PolicyResult]
    score: float = Field(..., description="Percentage score (0-100)")
