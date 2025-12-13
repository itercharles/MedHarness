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
    level: Optional[int] = Field(None, description="Hierarchy level")
    allowed_parents: Optional[List[str]] = Field(None, description="Allowed parent document types")
    relations: Optional[List[RelationConfig]] = Field(None, description="Relationship configurations")
    type: Optional[str] = Field(None, description="Special type (e.g., 'test')")
    verifies: Optional[List[str]] = Field(None, description="Document types this verifies")
    properties: Optional[List[str]] = Field(None, description="Properties to display")


class PoliciesConfig(BaseModel):
    """Project policies configuration."""
    
    require_test_coverage: List[str] = Field(default_factory=list, description="Document types requiring test coverage")


class ProjectConfig(BaseModel):
    """Project configuration."""
    
    doc_types: List[DocTypeConfig] = Field(..., description="Document type configurations")
    policies: PoliciesConfig = Field(default_factory=PoliciesConfig, description="Project policies")
    
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
