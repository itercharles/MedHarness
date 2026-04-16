"""
Tests for SYS-021: Field Schema Protocol Extension

Verifies that ItemTypeSchema carries FieldSchema entries and that
ProjectSchema.get_fields() provides access to field-level constraints
without reaching into the utils layer.

@links: SYS-021
"""

import pytest
from compliantflow.domain.schema import (
    FieldSchema,
    GlobalLifecycle,
    ItemTypeSchema,
    LifecycleStateInfo,
    ProjectSchema,
)
from tests.stub_adapter import StubDHFAdapter


def _make_type_with_fields(*fields: FieldSchema) -> ItemTypeSchema:
    return ItemTypeSchema(
        name="SYS",
        id_prefix="SYS-",
        fields=list(fields),
    )


def test_TC_SYS_021_001_field_schema_model_has_required_attributes():
    """
    TC-SYS-021-001: FieldSchema has name, format, label, required, options,
    default, and target_types fields.

    @test_id: TC-SYS-021-001
    @links: SYS-021
    """
    f = FieldSchema(
        name="category",
        format="select",
        label="Category",
        required=True,
        options=["Functional", "Performance"],
        default="Functional",
    )
    assert f.name == "category"
    assert f.format == "select"
    assert f.label == "Category"
    assert f.required is True
    assert "Functional" in f.options
    assert f.default == "Functional"
    assert f.target_types == []


def test_TC_SYS_021_002_item_type_schema_carries_fields():
    """
    TC-SYS-021-002: ItemTypeSchema.fields holds the list of FieldSchema entries.

    @test_id: TC-SYS-021-002
    @links: SYS-021
    """
    field = FieldSchema(name="title", format="short_text", label="Title")
    it = _make_type_with_fields(field)
    assert len(it.fields) == 1
    assert it.fields[0].name == "title"


def test_TC_SYS_021_003_item_type_schema_fields_defaults_to_empty():
    """
    TC-SYS-021-003: ItemTypeSchema.fields defaults to an empty list when
    not provided, preserving backwards compatibility.

    @test_id: TC-SYS-021-003
    @links: SYS-021
    """
    it = ItemTypeSchema(name="UC", id_prefix="UC-")
    assert it.fields == []


def test_TC_SYS_021_004_project_schema_get_fields_returns_fields():
    """
    TC-SYS-021-004: ProjectSchema.get_fields(type_name) returns the FieldSchema
    list for the given type.

    @test_id: TC-SYS-021-004
    @links: SYS-021
    """
    content_field = FieldSchema(name="content", format="long_text", required=True)
    cat_field = FieldSchema(
        name="category",
        format="select",
        options=["Functional", "Security"],
        default="Functional",
    )
    schema = ProjectSchema(item_types=[_make_type_with_fields(content_field, cat_field)])
    fields = schema.get_fields("SYS")
    assert len(fields) == 2
    names = [f.name for f in fields]
    assert "content" in names
    assert "category" in names


def test_TC_SYS_021_005_project_schema_get_fields_unknown_type_returns_empty():
    """
    TC-SYS-021-005: ProjectSchema.get_fields returns [] for an unknown type name.

    @test_id: TC-SYS-021-005
    @links: SYS-021
    """
    schema = ProjectSchema(item_types=[])
    assert schema.get_fields("UNKNOWN") == []


def test_TC_SYS_021_006_field_schema_relationship_carries_target_types():
    """
    TC-SYS-021-006: FieldSchema for relationship fields carries target_types.

    @test_id: TC-SYS-021-006
    @links: SYS-021
    """
    f = FieldSchema(
        name="satisfies",
        format="item_multiselect",
        label="Satisfies",
        target_types=["CRS"],
    )
    assert f.target_types == ["CRS"]


def test_TC_SYS_021_007_stub_adapter_project_config_compatible():
    """
    TC-SYS-021-007: StubDHFAdapter.get_project_config() returns types with
    fields defaulting to [], preserving backwards compatibility.

    @test_id: TC-SYS-021-007
    @links: SYS-021
    """
    adapter = StubDHFAdapter()
    config = adapter.get_project_config()
    sys_type = config.get_type("SYS")
    assert sys_type is not None
    assert sys_type.fields == []  # StubDHFAdapter does not populate fields
