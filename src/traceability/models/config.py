"""Configuration models."""

from pydantic import BaseModel, Field
from typing import List, Optional


class RelationConfig(BaseModel):
    """Configuration for a relationship."""
    target: str = Field(..., description="Target Document Type Code")
    label: str = Field(..., description="Label for the relationship (e.g., 'verify')")


class DocTypeConfig(BaseModel):
    """Configuration for a document type."""
    
    code: str = Field(..., description="Document type code (e.g., 'SYS')")
    name: str = Field(..., description="Human-readable name")
    prefix: str = Field(..., description="ID prefix (e.g., 'SYS-')")
    directory: Optional[str] = Field(None, description="Storage directory name (defaults to prefix without dash)")
    allowed_parents: Optional[List[str]] = Field(None, description="Allowed parent document types")
    relations: Optional[List[RelationConfig]] = Field(None, description="Relationship configurations")
    type: Optional[str] = Field(None, description="Special type (e.g., 'test')")
    verifies: Optional[List[str]] = Field(None, description="Document types this verifies")
    properties: Optional[List[str]] = Field(None, description="Properties to display")
    
    # Universal framework fields
    icon: Optional[str] = Field(None, description="Icon for UI display")
    page_enabled: Optional[bool] = Field(None, description="Whether to generate a page for this type")
    page_number: Optional[int] = Field(None, description="Page number in Streamlit sidebar")
    lifecycle: Optional[dict] = Field(None, description="Lifecycle configuration with states and transitions")
    has_verification: Optional[bool] = Field(None, description="Whether this type supports verification tracking")
    verification_states: Optional[List[str]] = Field(None, description="Verification states")



class PoliciesConfig(BaseModel):
    """Project policies configuration."""
    
    require_test_coverage: List[str] = Field(default_factory=list, description="Document types requiring test coverage")


class TraceabilityMatrix(BaseModel):
    """Configuration for a traceability matrix."""
    name: str = Field(..., description="Matrix name")
    description: str = Field(..., description="Matrix description")
    path: List[str] = Field(..., description="List of doc type codes in trace order")

class ProjectConfig(BaseModel):
    """Project configuration."""
    
    change_control: Optional[dict] = Field(default_factory=dict, description="Change control configuration")
    doc_types: List[DocTypeConfig] = Field(..., description="Document type configurations")
    policies: PoliciesConfig = Field(default_factory=PoliciesConfig, description="Project policies")
    traceability_matrices: List['TraceabilityMatrix'] = Field(default_factory=list, description="Traceability matrix configurations")
    test_integration: dict = Field(default_factory=dict, description="Test integration configuration")
    
    def get_doc_type(self, code: str) -> Optional[DocTypeConfig]:
        """Get document type configuration by code."""
        for dt in self.doc_types:
            if dt.code == code:
                return dt
        return None
    
    def get_doc_type_by_prefix(self, prefix: str) -> Optional[DocTypeConfig]:
        """Get document type configuration by prefix."""
        for dt in self.doc_types:
            if dt.prefix == prefix:
                return dt
        return None

