"""Configuration models."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Any

import yaml


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
    RELATIONSHIP = "relationship"


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

    # New relationship format fields
    relationship_type: Optional[str] = Field(None, description="Reference to relationship type in global registry")

    @property
    def display_label(self) -> str:
        """Get display label (use custom or generate from name)."""
        if self.label:
            return self.label
        return self.name.replace('_', ' ').title()


class LifecycleState(BaseModel):
    """Global lifecycle state definition with action information."""
    id: str = Field(..., description="Unique state identifier (e.g., 'draft', 'approved')")
    label: str = Field(..., description="Human-readable label")
    action_label: Optional[str] = Field(None, description="Label for action to reach this state")
    icon: Optional[str] = Field(None, description="Emoji icon for the state")
    color: Optional[str] = Field(None, description="Color for UI display")
    is_initial: bool = Field(False, description="Whether this is an initial state for new items")
    is_stable: bool = Field(False, description="Whether items in this state are stable/locked")


class GlobalLifecycle(BaseModel):
    """Global lifecycle configuration with all states."""
    states: List[LifecycleState] = Field(default_factory=list, description="All available lifecycle states")


class RelationConfig(BaseModel):
    """Configuration for a relationship."""
    target: str = Field(..., description="Target Document Type Code")
    label: str = Field(..., description="Label for the relationship")


class DocTypeConfig(BaseModel):
    """Configuration for a document type."""

    code: str = Field(..., description="Document type code (e.g., 'SYS')")
    type_name: Optional[str] = Field(None, description="medharness domain name (e.g., 'system_requirement'); falls back to code if absent")
    parent_types: Optional[List[str]] = Field(None, description="medharness domain parent type names for traceability hierarchy")
    name: str = Field(..., description="Human-readable name")
    prefix: str = Field(..., description="ID prefix (e.g., 'SYS-')")
    directory: Optional[str] = Field(None, description="Storage directory name")
    allowed_parents: Optional[List[str]] = Field(None, description="Allowed parent document types")
    relations: Optional[List[RelationConfig]] = Field(None, description="Relationship configurations")
    type: Optional[str] = Field(None, description="Special type (e.g., 'test')")
    verifies: Optional[List[str]] = Field(None, description="Document types this verifies")
    properties: Optional[List[Any]] = Field(None, description="Properties to display")

    # Universal framework fields
    icon: Optional[str] = Field(None, description="Icon for UI display")
    page_enabled: Optional[bool] = Field(None, description="Whether to generate a page for this type")
    page_number: Optional[int] = Field(None, description="Page number in Streamlit sidebar")
    lifecycle: Optional[dict] = Field(None, description="Lifecycle configuration with states and transitions")
    has_verification: Optional[bool] = Field(None, description="Whether this type supports verification tracking")
    verification_states: Optional[List[str]] = Field(None, description="Verification states")


class TraceabilityMatrix(BaseModel):
    """Configuration for a traceability matrix."""
    name: str = Field(..., description="Matrix name")
    description: str = Field(..., description="Matrix description")
    path: List[str] = Field(..., description="List of doc type codes in trace order")


class RequiredTraceabilityRule(BaseModel):
    """Explicit required traceability rule — replaces deprecated allowed_parents.

    Each rule defines a mandatory link that must exist between items of two types.
    """
    source_type: str = Field(..., description="Source document type code (e.g., 'SRS')")
    direction: str = Field(..., description="'upstream' (source links to target) or 'downstream' (target links to source)")
    field: Optional[str] = Field(None, description="Field name on source item (required for upstream)")
    target_type: str = Field(..., description="Target document type code (e.g., 'SYS')")
    min_count: int = Field(1, description="Minimum required links")


class ProjectConfig(BaseModel):
    """Project configuration."""

    global_lifecycle: Optional[GlobalLifecycle] = Field(None, description="Global lifecycle configuration")
    doc_types: List[DocTypeConfig] = Field(..., description="Document type configurations")
    traceability_matrices: List[TraceabilityMatrix] = Field(default_factory=list, description="Traceability matrix configurations")
    required_traceability: Optional[List[RequiredTraceabilityRule]] = Field(None, description="Required traceability rules")
    test_integration: dict = Field(default_factory=dict, description="Test integration configuration")
    document_specifications: dict = Field(default_factory=dict, description="Document specification configurations")

    @classmethod
    def load(cls, config_dir: Path) -> "ProjectConfig":
        """Load from split config directory (global.yaml + doc_types/*.yaml)."""
        global_path = config_dir / "global.yaml"
        if not global_path.exists():
            raise FileNotFoundError(f"global.yaml not found at {global_path}")
        global_data = yaml.safe_load(global_path.read_text(encoding="utf-8")) or {}

        doc_types = []
        doc_types_dir = config_dir / "doc_types"
        if doc_types_dir.exists():
            for f in sorted(doc_types_dir.glob("*.yaml")):
                doc_types.append(yaml.safe_load(f.read_text(encoding="utf-8")))

        return cls(**global_data, doc_types=doc_types)

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
