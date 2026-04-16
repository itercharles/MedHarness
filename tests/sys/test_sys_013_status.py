"""
Tests for SYS-013: Compliance Posture Status Command

Verifies that get_status() returns a structured summary of compliance,
traceability, open defects, and release readiness.

@links: SYS-013
"""

import pytest
from compliantflow.core import CompliantFlowCore


def test_TC_SYS_013_001_status_returns_required_keys(stub_adapter, governance_dir):
    """
    TC-SYS-013-001: get_status returns a dict with compliance, traceability,
    open_defects, and release keys.

    @test_id: TC-SYS-013-001
    @links: SYS-013
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_status(governance_dir)
    assert "compliance" in result
    assert "traceability" in result
    assert "open_defects" in result
    assert "release" in result


def test_TC_SYS_013_002_status_compliance_entries_have_required_fields(stub_adapter, governance_dir):
    """
    TC-SYS-013-002: each compliance entry in status output has standard, score,
    passed_policies, total_policies, and source fields.

    @test_id: TC-SYS-013-002
    @links: SYS-013
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_status(governance_dir, live=True)
    assert len(result["compliance"]) > 0
    for entry in result["compliance"]:
        assert "standard" in entry
        assert "score" in entry
        assert "passed_policies" in entry
        assert "total_policies" in entry
        assert "source" in entry


def test_TC_SYS_013_003_status_uses_persisted_run_when_available(stub_adapter, governance_dir):
    """
    TC-SYS-013-003: get_status reads from persisted compliance run store by default
    when a run exists.

    @test_id: TC-SYS-013-003
    @links: SYS-013
    """
    stub_adapter.record_compliance_run(
        group_id="IEC_62304",
        report_dict={
            "schema_version": "1.0",
            "source_id": "IEC_62304",
            "score": 95.0,
            "passed_policies": 95,
            "total_policies": 100,
            "results": [],
            "timestamp": "2026-04-15T10:00:00+00:00",
            "commit_sha": "abc123",
        },
    )
    core = CompliantFlowCore(stub_adapter)
    result = core.get_status(governance_dir, live=False)
    iec_entry = next((e for e in result["compliance"] if e["standard"] == "IEC_62304"), None)
    assert iec_entry is not None
    assert iec_entry["score"] == 95.0
    assert iec_entry["source"] == "persisted"


def test_TC_SYS_013_004_status_open_defects_count(stub_adapter, governance_dir):
    """
    TC-SYS-013-004: open_defects count reflects DEF items with open status.

    @test_id: TC-SYS-013-004
    @links: SYS-013
    """
    stub_adapter.create_item({"id": "DEF-001", "title": "Crash on import", "status": "open"})
    core = CompliantFlowCore(stub_adapter)
    result = core.get_status(governance_dir)
    assert result["open_defects"]["count"] == 1
    assert result["open_defects"]["items"][0]["id"] == "DEF-001"


def test_TC_SYS_013_005_get_open_defects_is_shared_method(stub_adapter):
    """
    TC-SYS-013-005: get_open_defects() is a standalone method on CompliantFlowCore,
    callable independently of get_status.

    @test_id: TC-SYS-013-005
    @links: SYS-013
    """
    stub_adapter.create_item({"id": "DEF-002", "title": "Validation error", "status": "draft"})
    stub_adapter.create_item({"id": "DEF-003", "title": "Closed issue", "status": "closed"})
    core = CompliantFlowCore(stub_adapter)
    open_defs = core.get_open_defects()
    ids = [d["id"] for d in open_defs]
    assert "DEF-002" in ids
    assert "DEF-003" not in ids
