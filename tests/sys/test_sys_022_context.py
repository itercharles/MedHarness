"""
Tests for SYS-022: AI Agent Context Package

Verifies that get_context() returns a structured schema, lifecycle, and
compliance policy summary for LLM/agent consumption.

@links: SYS-022
"""

import pytest
from compliantflow.core import CompliantFlowCore
from compliantflow.domain.schema import FieldSchema, ItemTypeSchema


def test_TC_SYS_022_001_context_returns_required_keys(stub_adapter, governance_dir):
    """
    TC-SYS-022-001: get_context returns a dict with item_types, lifecycle,
    and compliance_policies keys.

    @test_id: TC-SYS-022-001
    @links: SYS-022
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_context(governance_dir)
    assert "item_types" in result
    assert "lifecycle" in result
    assert "compliance_policies" in result


def test_TC_SYS_022_002_item_types_have_required_fields(stub_adapter, governance_dir):
    """
    TC-SYS-022-002: Each item_type entry has name, id_prefix, parent_types,
    has_verification, and fields keys.

    @test_id: TC-SYS-022-002
    @links: SYS-022
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_context(governance_dir)
    assert len(result["item_types"]) > 0
    for t in result["item_types"]:
        assert "name" in t
        assert "id_prefix" in t
        assert "parent_types" in t
        assert "has_verification" in t
        assert "fields" in t


def test_TC_SYS_022_003_lifecycle_states_present(stub_adapter, governance_dir):
    """
    TC-SYS-022-003: lifecycle.states is a list with at least one entry
    containing id, label, and is_stable.

    @test_id: TC-SYS-022-003
    @links: SYS-022
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_context(governance_dir)
    states = result["lifecycle"]["states"]
    assert len(states) > 0
    for s in states:
        assert "id" in s
        assert "label" in s
        assert "is_stable" in s


def test_TC_SYS_022_004_compliance_policies_reflect_governance_dir(stub_adapter, governance_dir):
    """
    TC-SYS-022-004: compliance_policies includes one entry per governance YAML,
    each with standard, title, and policies list.

    @test_id: TC-SYS-022-004
    @links: SYS-022
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_context(governance_dir)
    assert len(result["compliance_policies"]) > 0
    for group in result["compliance_policies"]:
        assert "standard" in group
        assert "title" in group
        assert "policies" in group
        assert len(group["policies"]) > 0


def test_TC_SYS_022_005_standard_filter_limits_policies(stub_adapter, governance_dir):
    """
    TC-SYS-022-005: --standard filter returns only the matching governance group.

    @test_id: TC-SYS-022-005
    @links: SYS-022
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_context(governance_dir, standard="IEC_62304")
    standards = [g["standard"] for g in result["compliance_policies"]]
    assert standards == ["IEC_62304"]


def test_TC_SYS_022_006_standard_filter_unknown_returns_empty(stub_adapter, governance_dir):
    """
    TC-SYS-022-006: Filtering for an unknown standard returns empty
    compliance_policies list.

    @test_id: TC-SYS-022-006
    @links: SYS-022
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_context(governance_dir, standard="NONEXISTENT")
    assert result["compliance_policies"] == []


def test_TC_SYS_022_007_summary_flag_omits_check_details(stub_adapter, governance_dir):
    """
    TC-SYS-022-007: With summary=True, policy entries contain only id, section,
    and text — no check_type or automated fields.

    @test_id: TC-SYS-022-007
    @links: SYS-022
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_context(governance_dir, summary=True)
    for group in result["compliance_policies"]:
        for p in group["policies"]:
            assert "id" in p
            assert "section" in p
            assert "text" in p
            assert "check_type" not in p
            assert "automated" not in p


def test_TC_SYS_022_008_full_policies_include_check_type(stub_adapter, governance_dir):
    """
    TC-SYS-022-008: Without summary flag, policy entries include automated and
    check_type fields.

    @test_id: TC-SYS-022-008
    @links: SYS-022
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_context(governance_dir, summary=False)
    for group in result["compliance_policies"]:
        for p in group["policies"]:
            assert "automated" in p
            assert "check_type" in p


def test_TC_SYS_022_009_item_types_with_fields_populated(stub_adapter, governance_dir):
    """
    TC-SYS-022-009: item_type fields list carries FieldSchema-compatible dicts
    when the adapter provides them.

    @test_id: TC-SYS-022-009
    @links: SYS-022
    """
    from compliantflow.domain.schema import FieldSchema, ItemTypeSchema, ProjectSchema, GlobalLifecycle, LifecycleStateInfo

    class FieldedAdapter(stub_adapter.__class__):
        pass

    adapter = FieldedAdapter()
    # Inject a schema with field definitions
    from compliantflow.domain.schema import ProjectSchema, ItemTypeSchema, FieldSchema, GlobalLifecycle, LifecycleStateInfo
    adapter._schema = ProjectSchema(
        item_types=[
            ItemTypeSchema(
                name="SYS",
                id_prefix="SYS-",
                fields=[
                    FieldSchema(name="title", format="short_text", label="Title", required=False),
                    FieldSchema(name="category", format="select",
                                options=["Functional", "Security"], required=True, default="Functional"),
                ],
            )
        ],
        global_lifecycle=GlobalLifecycle(states=[
            LifecycleStateInfo(id="draft", label="Draft"),
        ]),
    )
    core = CompliantFlowCore(adapter)
    result = core.get_context(governance_dir)
    sys_type = next((t for t in result["item_types"] if t["name"] == "SYS"), None)
    assert sys_type is not None
    field_names = [f["name"] for f in sys_type["fields"]]
    assert "title" in field_names
    assert "category" in field_names
    cat_field = next(f for f in sys_type["fields"] if f["name"] == "category")
    assert "Functional" in cat_field["options"]
    assert cat_field["required"] is True
