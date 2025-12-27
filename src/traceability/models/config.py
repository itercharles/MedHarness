"""Configuration models."""

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Any


class PropertyFormat(str, Enum):
    """Built-in property formats for UI rendering."""
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    MARKDOWN = "markdown"
    URL = "url"
    SELECT = "select"
    MULTISELECT = "multiselect"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    TOGGLE = "toggle"
    NUMBER = "number"
    SLIDER = "slider"
    DATE = "date"
    DATETIME = "datetime"
    ITEM_REFERENCE = "item_reference"
    ITEM_MULTISELECT = "item_multiselect"
    FILE_UPLOAD = "file_upload"


class PropertyConfig(BaseModel):
    """Configuration for a single property with explicit format."""
    name: str = Field(..., description="Property name (field name in data)")
    format: PropertyFormat = Field(PropertyFormat.SHORT_TEXT, description="Display format")
    label: Optional[str] = Field(None, description="Display label (auto-generated from name if not provided)")
    required: bool = Field(False, description="Whether this field is required")
    default: Optional[Any] = Field(None, description="Default value")
    placeholder: Optional[str] = Field(None, description="Placeholder text for input fields")
    help: Optional[str] = Field(None, description="Help text displayed below the field")
    
    # Format-specific options
    options: Optional[List[str]] = Field(None, description="Options for select/multiselect/radio")
    height: Optional[int] = Field(None, description="Height in pixels for text areas")
    min_value: Optional[float] = Field(None, description="Minimum value for number/slider")
    max_value: Optional[float] = Field(None, description="Maximum value for number/slider")
    step: Optional[float] = Field(None, description="Step size for slider")
    target_types: Optional[List[str]] = Field(None, description="Target document types for item references")
    allowed_extensions: Optional[List[str]] = Field(None, description="Allowed file extensions for file upload")
    
    @property
    def display_label(self) -> str:
        """Get display label (use custom or generate from name)."""
        if self.label:
            return self.label
        return self.name.replace('_', ' ').title()



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
    properties: Optional[List[Any]] = Field(None, description="Properties to display (string, dict, or PropertyConfig)")
    
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

