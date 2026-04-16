"""
Tests for SYS-023: Draft Item Pre-Validation

Verifies that validate_draft() checks required fields and allowed values
against the doc-type FieldSchema without requiring a full CI run.

@links: SYS-023
"""

import pytest
from compliantflow.core import CompliantFlowCore
from compliantflow.domain.schema import (
    FieldSchema, GlobalLifecycle, ItemTypeSchema, LifecycleStateInfo, ProjectSchema,
)
from tests.stub_adapter import StubDHFAdapter


def _adapter_with_sys_schema() -> StubDHFAdapter:
    """StubDHFAdapter with a SYS type that has required and constrained fields."""
    adapter = StubDHFAdapter()
    adapter._schema = ProjectSchema(
        item_types=[
            ItemTypeSchema(
                name="SYS",
                id_prefix="SYS-",
                fields=[
                    FieldSchema(name="title", format="short_text", label="Title", required=True),
                    FieldSchema(name="content", format="long_text", label="Content", required=True),
                    FieldSchema(
                        name="category", format="select", required=True,
                        options=["Functional", "Performance", "Security"],
                        default="Functional",
                    ),
                    FieldSchema(
                        name="verification_method", format="multiselect",
                        options=["Test", "Inspection", "Analysis"],
                    ),
                ],
            ),
        ],
        global_lifecycle=GlobalLifecycle(states=[
            LifecycleStateInfo(id="draft", label="Draft"),
        ]),
    )
    return adapter


def test_TC_SYS_023_001_valid_item_passes(stub_adapter):
    """
    TC-SYS-023-001: A well-formed item with all required fields and valid values passes.

    @test_id: TC-SYS-023-001
    @links: SYS-023
    """
    adapter = _adapter_with_sys_schema()
    core = CompliantFlowCore(adapter)
    result = core.validate_draft({
        "id": "SYS-001",
        "title": "System shall do X",
        "content": "The system shall provide...",
        "category": "Functional",
    })
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["type"] == "SYS"


def test_TC_SYS_023_002_missing_required_field_fails(stub_adapter):
    """
    TC-SYS-023-002: Missing a required field produces an error and valid=False.

    @test_id: TC-SYS-023-002
    @links: SYS-023
    """
    adapter = _adapter_with_sys_schema()
    core = CompliantFlowCore(adapter)
    result = core.validate_draft({
        "id": "SYS-001",
        "title": "System shall do X",
        # content and category missing
    })
    assert result["valid"] is False
    field_names = [e["field"] for e in result["errors"]]
    assert "content" in field_names
    assert "category" in field_names


def test_TC_SYS_023_003_invalid_select_value_fails(stub_adapter):
    """
    TC-SYS-023-003: A select field with a value not in options fails.

    @test_id: TC-SYS-023-003
    @links: SYS-023
    """
    adapter = _adapter_with_sys_schema()
    core = CompliantFlowCore(adapter)
    result = core.validate_draft({
        "id": "SYS-001",
        "title": "System shall do X",
        "content": "The system shall...",
        "category": "InvalidCategory",
    })
    assert result["valid"] is False
    assert any(e["field"] == "category" for e in result["errors"])


def test_TC_SYS_023_004_invalid_multiselect_value_fails(stub_adapter):
    """
    TC-SYS-023-004: A multiselect field with an invalid value fails.

    @test_id: TC-SYS-023-004
    @links: SYS-023
    """
    adapter = _adapter_with_sys_schema()
    core = CompliantFlowCore(adapter)
    result = core.validate_draft({
        "id": "SYS-001",
        "title": "System shall do X",
        "content": "The system shall...",
        "category": "Functional",
        "verification_method": ["Test", "InvalidMethod"],
    })
    assert result["valid"] is False
    assert any(e["field"] == "verification_method" for e in result["errors"])


def test_TC_SYS_023_005_valid_multiselect_values_pass(stub_adapter):
    """
    TC-SYS-023-005: All valid multiselect values pass.

    @test_id: TC-SYS-023-005
    @links: SYS-023
    """
    adapter = _adapter_with_sys_schema()
    core = CompliantFlowCore(adapter)
    result = core.validate_draft({
        "id": "SYS-001",
        "title": "System shall do X",
        "content": "The system shall...",
        "category": "Functional",
        "verification_method": ["Test", "Inspection"],
    })
    assert result["valid"] is True


def test_TC_SYS_023_006_type_inferred_from_id_prefix(stub_adapter):
    """
    TC-SYS-023-006: Type is inferred from the id prefix when --type is not given.

    @test_id: TC-SYS-023-006
    @links: SYS-023
    """
    adapter = _adapter_with_sys_schema()
    core = CompliantFlowCore(adapter)
    result = core.validate_draft({"id": "SYS-042", "title": "T", "content": "C", "category": "Functional"})
    assert result["type"] == "SYS"


def test_TC_SYS_023_007_explicit_type_overrides_prefix(stub_adapter):
    """
    TC-SYS-023-007: Explicit type_name overrides id prefix inference.

    @test_id: TC-SYS-023-007
    @links: SYS-023
    """
    adapter = _adapter_with_sys_schema()
    core = CompliantFlowCore(adapter)
    result = core.validate_draft(
        {"title": "Draft item", "content": "C", "category": "Functional"},
        type_name="SYS",
    )
    assert result["type"] == "SYS"
    assert result["valid"] is True


def test_TC_SYS_023_008_unknown_type_warns_not_errors(stub_adapter):
    """
    TC-SYS-023-008: Items with an unrecognised type emit a warning but not an error.

    @test_id: TC-SYS-023-008
    @links: SYS-023
    """
    adapter = _adapter_with_sys_schema()
    core = CompliantFlowCore(adapter)
    result = core.validate_draft({"id": "UNKNOWN-001", "title": "T"})
    assert result["valid"] is True
    assert len(result["warnings"]) > 0


def test_TC_SYS_023_009_stub_adapter_no_fields_always_passes(stub_adapter):
    """
    TC-SYS-023-009: StubDHFAdapter has no field constraints so any item passes.

    @test_id: TC-SYS-023-009
    @links: SYS-023
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.validate_draft({"id": "SYS-001"})
    assert result["valid"] is True
    assert result["errors"] == []
