"""
Tests for SYS-024: RDM Migration Completeness Validation

Verifies that validate_migration_report() categorises migrated items
into clean / gaps / skipped and that generate_migration_markdown() produces
a well-formed Markdown report.

@links: SYS-024
"""

import pytest
from compliantflow.core import CompliantFlowCore
from compliantflow.migrate.rdm import generate_migration_markdown
from compliantflow.domain.schema import (
    FieldSchema, GlobalLifecycle, ItemTypeSchema, LifecycleStateInfo, ProjectSchema,
)
from tests.stub_adapter import StubDHFAdapter


def _adapter_with_sys_schema() -> StubDHFAdapter:
    """StubDHFAdapter with a SYS type that has required fields."""
    adapter = StubDHFAdapter()
    adapter._schema = ProjectSchema(
        item_types=[
            ItemTypeSchema(
                name="SYS",
                id_prefix="SYS-",
                fields=[
                    FieldSchema(name="title", format="short_text", required=True),
                    FieldSchema(name="content", format="long_text", required=True),
                    FieldSchema(
                        name="category", format="select", required=True,
                        options=["Functional", "Performance"],
                    ),
                ],
            ),
        ],
        global_lifecycle=GlobalLifecycle(states=[
            LifecycleStateInfo(id="draft", label="Draft"),
        ]),
    )
    return adapter


def _make_migration_report(created=None, skipped=None, needs_review=None):
    return {
        "created": created or [],
        "skipped": skipped or [],
        "needs_review": needs_review or [],
        "mapping": {},
        "dry_run": False,
    }


def test_TC_SYS_024_001_clean_item_passes_validation(stub_adapter):
    """
    TC-SYS-024-001: A migrated item with all required fields and valid values
    is classified as clean.

    @test_id: TC-SYS-024-001
    @links: SYS-024
    """
    adapter = _adapter_with_sys_schema()
    adapter.create_item({
        "id": "SYS-001",
        "title": "System shall do X",
        "content": "The system shall provide...",
        "category": "Functional",
    })
    core = CompliantFlowCore(adapter)
    report = _make_migration_report(
        created=[{"cf_id": "SYS-001", "rdm_id": "rdm-req-001", "type": "SYS"}],
    )
    result = core.validate_migration_report(report)
    assert result["summary"]["clean"] == 1
    assert result["summary"]["gaps"] == 0
    assert len(result["clean"]) == 1
    assert result["clean"][0]["cf_id"] == "SYS-001"


def test_TC_SYS_024_002_item_missing_required_field_is_gap(stub_adapter):
    """
    TC-SYS-024-002: A migrated item missing required fields is classified as a gap.

    @test_id: TC-SYS-024-002
    @links: SYS-024
    """
    adapter = _adapter_with_sys_schema()
    adapter.create_item({
        "id": "SYS-001",
        "title": "System shall do X",
        # missing content and category
    })
    core = CompliantFlowCore(adapter)
    report = _make_migration_report(
        created=[{"cf_id": "SYS-001", "rdm_id": "rdm-req-001", "type": "SYS"}],
    )
    result = core.validate_migration_report(report)
    assert result["summary"]["gaps"] == 1
    assert result["summary"]["clean"] == 0
    gap = result["gaps"][0]
    assert gap["cf_id"] == "SYS-001"
    assert len(gap["validation_errors"]) > 0
    assert len(gap["remediation"]) > 0


def test_TC_SYS_024_003_migration_warning_makes_item_a_gap(stub_adapter):
    """
    TC-SYS-024-003: A migrated item with a migration warning (needs_review) is
    classified as a gap even if field validation passes.

    @test_id: TC-SYS-024-003
    @links: SYS-024
    """
    adapter = _adapter_with_sys_schema()
    adapter.create_item({
        "id": "SYS-001",
        "title": "System shall do X",
        "content": "The system shall...",
        "category": "Functional",
    })
    core = CompliantFlowCore(adapter)
    report = _make_migration_report(
        created=[{"cf_id": "SYS-001", "rdm_id": "rdm-req-001", "type": "SYS"}],
        needs_review=[{"cf_id": "SYS-001", "warning": "Parent 'rdm-old-001' not found in migration set; link dropped"}],
    )
    result = core.validate_migration_report(report)
    assert result["summary"]["gaps"] == 1
    gap = result["gaps"][0]
    assert len(gap["migration_warnings"]) == 1
    assert "Parent" in gap["migration_warnings"][0]


def test_TC_SYS_024_004_skipped_items_in_report(stub_adapter):
    """
    TC-SYS-024-004: Items from migration skipped list appear in the completeness report.

    @test_id: TC-SYS-024-004
    @links: SYS-024
    """
    core = CompliantFlowCore(stub_adapter)
    report = _make_migration_report(
        skipped=[{"rdm_id": "rdm-unknown-001", "reason": "Cannot determine CompliantFlow doc type"}],
    )
    result = core.validate_migration_report(report)
    assert result["summary"]["skipped"] == 1
    assert result["skipped"][0]["rdm_id"] == "rdm-unknown-001"


def test_TC_SYS_024_005_summary_counts_are_correct(stub_adapter):
    """
    TC-SYS-024-005: summary.total_created, clean, gaps, skipped counts match actual lists.

    @test_id: TC-SYS-024-005
    @links: SYS-024
    """
    adapter = _adapter_with_sys_schema()
    adapter.create_item({"id": "SYS-001", "title": "T", "content": "C", "category": "Functional"})
    adapter.create_item({"id": "SYS-002", "title": "T2"})  # missing required fields
    core = CompliantFlowCore(adapter)
    report = _make_migration_report(
        created=[
            {"cf_id": "SYS-001", "rdm_id": "r1", "type": "SYS"},
            {"cf_id": "SYS-002", "rdm_id": "r2", "type": "SYS"},
        ],
        skipped=[{"rdm_id": "r3", "reason": "unknown type"}],
    )
    result = core.validate_migration_report(report)
    s = result["summary"]
    assert s["total_created"] == 2
    assert s["clean"] == 1
    assert s["gaps"] == 1
    assert s["skipped"] == 1
    assert s["clean"] + s["gaps"] == s["total_created"]


def test_TC_SYS_024_006_markdown_report_contains_required_sections(stub_adapter):
    """
    TC-SYS-024-006: generate_migration_markdown produces Markdown with Clean,
    Gaps, and Skipped sections.

    @test_id: TC-SYS-024-006
    @links: SYS-024
    """
    completeness = {
        "summary": {"total_created": 2, "clean": 1, "gaps": 1, "skipped": 1},
        "clean": [{"cf_id": "SYS-001", "rdm_id": "r1", "type": "SYS", "title": "Do X"}],
        "gaps": [{
            "cf_id": "SYS-002", "rdm_id": "r2", "type": "SYS",
            "migration_warnings": ["Parent not found"],
            "validation_errors": [{"field": "content", "message": "Required field missing"}],
            "remediation": ["Set field 'content'"],
        }],
        "skipped": [{"rdm_id": "r3", "reason": "unknown type"}],
        "mapping": {},
    }
    md = generate_migration_markdown(completeness)
    assert "# RDM Migration Completeness Report" in md
    assert "✓ Clean Items" in md
    assert "⚠ Items Requiring Review" in md
    assert "✗ Skipped Items" in md
    assert "SYS-001" in md
    assert "SYS-002" in md
    assert "r3" in md


def test_TC_SYS_024_007_markdown_all_clean_shows_complete_status(stub_adapter):
    """
    TC-SYS-024-007: Markdown report indicates complete status when all items are clean.

    @test_id: TC-SYS-024-007
    @links: SYS-024
    """
    completeness = {
        "summary": {"total_created": 1, "clean": 1, "gaps": 0, "skipped": 0},
        "clean": [{"cf_id": "SYS-001", "rdm_id": "r1", "type": "SYS", "title": "T"}],
        "gaps": [],
        "skipped": [],
        "mapping": {},
    }
    md = generate_migration_markdown(completeness)
    assert "Migration complete" in md
    assert "Review required" not in md


def test_TC_SYS_024_008_item_not_found_after_migration_is_gap():
    """
    TC-SYS-024-008: If a created item is not found in the DHF after migration,
    it is classified as a gap with an explanatory error.

    @test_id: TC-SYS-024-008
    @links: SYS-024
    """
    empty_adapter = StubDHFAdapter()  # no items — SYS-MISSING won't be found
    core = CompliantFlowCore(empty_adapter)
    report = _make_migration_report(
        created=[{"cf_id": "SYS-MISSING", "rdm_id": "r1", "type": "SYS"}],
    )
    result = core.validate_migration_report(report)
    assert result["summary"]["gaps"] == 1
    assert any("not found" in e["message"] for e in result["gaps"][0]["validation_errors"])
