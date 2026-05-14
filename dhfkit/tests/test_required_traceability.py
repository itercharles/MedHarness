"""Unit tests for check_required_traceability."""

import pytest
from dhfkit.models.config import ProjectConfig, DocTypeConfig, RequiredTraceabilityRule
from dhfkit.traceability import check_required_traceability


def _make_config(rules: list) -> ProjectConfig:
    """Build a minimal ProjectConfig with required_traceability rules."""
    return ProjectConfig(
        doc_types=[
            DocTypeConfig(code="SRS", name="Software Requirement", prefix="SRS-"),
            DocTypeConfig(code="SYS", name="System Requirement", prefix="SYS-"),
            DocTypeConfig(code="SWDD", name="Software Detailed Design", prefix="SWDD-"),
            DocTypeConfig(code="RCM", name="Risk Control Measure", prefix="RCM-"),
            DocTypeConfig(code="RISK", name="Risk", prefix="RISK-"),
            DocTypeConfig(code="CRS", name="Customer Requirement", prefix="CRS-"),
            DocTypeConfig(code="UC", name="Use Case", prefix="UC-"),
        ],
        required_traceability=[
            RequiredTraceabilityRule(**r) for r in rules
        ],
    )


# ── Upstream: SRS derives_from SYS ──────────────────────────────────────────

def test_srs_has_sys_parent_pass():
    config = _make_config([
        {"source_type": "SRS", "direction": "upstream", "field": "derives_from", "target_type": "SYS", "min_count": 1},
    ])
    items = [
        {"id": "SRS-001", "derives_from": ["SYS-001"], "all_linked_uids": ["SYS-001"]},
        {"id": "SYS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is True
    assert len(result["failures"]) == 0


def test_srs_missing_sys_parent_fail():
    config = _make_config([
        {"source_type": "SRS", "direction": "upstream", "field": "derives_from", "target_type": "SYS", "min_count": 1},
    ])
    items = [
        {"id": "SRS-001", "derives_from": [], "all_linked_uids": []},
        {"id": "SYS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is False
    assert len(result["failures"]) == 1
    assert result["failures"][0]["id"] == "SRS-001"
    assert result["failures"][0]["rule"] == "SRS derives_from → SYS"


def test_srs_wrong_target_type_fail():
    config = _make_config([
        {"source_type": "SRS", "direction": "upstream", "field": "derives_from", "target_type": "SYS", "min_count": 1},
    ])
    items = [
        {"id": "SRS-001", "derives_from": ["CRS-001"], "all_linked_uids": ["CRS-001"]},
        {"id": "CRS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is False
    assert result["failures"][0]["current_count"] == 0


def test_srs_min_count_2_with_one_link_fail():
    config = _make_config([
        {"source_type": "SRS", "direction": "upstream", "field": "derives_from", "target_type": "SYS", "min_count": 2},
    ])
    items = [
        {"id": "SRS-001", "derives_from": ["SYS-001"], "all_linked_uids": ["SYS-001"]},
        {"id": "SYS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is False
    assert result["failures"][0]["current_count"] == 1
    assert result["failures"][0]["min_count"] == 2


# ── Upstream: RCM mitigates RISK ────────────────────────────────────────────

def test_rcm_missing_risk_fail():
    config = _make_config([
        {"source_type": "RCM", "direction": "upstream", "field": "mitigates", "target_type": "RISK", "min_count": 1},
    ])
    items = [
        {"id": "RCM-001", "mitigates": [], "all_linked_uids": []},
        {"id": "RISK-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is False
    assert result["failures"][0]["id"] == "RCM-001"


def test_rcm_has_risk_pass():
    config = _make_config([
        {"source_type": "RCM", "direction": "upstream", "field": "mitigates", "target_type": "RISK", "min_count": 1},
    ])
    items = [
        {"id": "RCM-001", "mitigates": ["RISK-001"], "all_linked_uids": ["RISK-001"]},
        {"id": "RISK-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is True


# ── Upstream: RCM implements SYS ───────────────────────────────────────────

def test_rcm_missing_sys_implements_fail():
    config = _make_config([
        {"source_type": "RCM", "direction": "upstream", "field": "implements", "target_type": "SYS", "min_count": 1},
    ])
    items = [
        {"id": "RCM-001", "implements": [], "all_linked_uids": []},
        {"id": "SYS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is False
    assert result["failures"][0]["id"] == "RCM-001"


def test_rcm_has_sys_implements_pass():
    config = _make_config([
        {"source_type": "RCM", "direction": "upstream", "field": "implements", "target_type": "SYS", "min_count": 1},
    ])
    items = [
        {"id": "RCM-001", "implements": ["SYS-001"], "all_linked_uids": ["SYS-001"]},
        {"id": "SYS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is True


# ── Downstream: CRS covered by SYS ─────────────────────────────────────────

def test_crs_covered_by_sys_pass():
    config = _make_config([
        {"source_type": "CRS", "direction": "downstream", "target_type": "SYS", "min_count": 1},
    ])
    items = [
        {"id": "CRS-001", "all_linked_uids": ["UC-001"]},
        {"id": "SYS-001", "satisfies": ["CRS-001"], "all_linked_uids": ["CRS-001"]},
        {"id": "UC-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is True


def test_crs_not_covered_by_sys_fail():
    config = _make_config([
        {"source_type": "CRS", "direction": "downstream", "target_type": "SYS", "min_count": 1},
    ])
    items = [
        {"id": "CRS-001", "all_linked_uids": ["UC-001"]},
        {"id": "SYS-001", "satisfies": ["CRS-002"], "all_linked_uids": ["CRS-002"]},
        {"id": "UC-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is False
    assert result["failures"][0]["id"] == "CRS-001"
    assert result["failures"][0]["rule"] == "CRS covered by SYS"


# ── Upstream: SWDD implements SRS ──────────────────────────────────────────

def test_swdd_missing_srs_fail():
    config = _make_config([
        {"source_type": "SWDD", "direction": "upstream", "field": "implements", "target_type": "SRS", "min_count": 1},
    ])
    items = [
        {"id": "SWDD-001", "implements": [], "all_linked_uids": []},
        {"id": "SRS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is False
    assert result["failures"][0]["id"] == "SWDD-001"


def test_swdd_has_srs_pass():
    config = _make_config([
        {"source_type": "SWDD", "direction": "upstream", "field": "implements", "target_type": "SRS", "min_count": 1},
    ])
    items = [
        {"id": "SWDD-001", "implements": ["SRS-001"], "all_linked_uids": ["SRS-001"]},
        {"id": "SRS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is True


# ── No rules / opt-out ──────────────────────────────────────────────────────

def test_explicit_empty_rules_skips_vmodel_defaults():
    """required_traceability=[] (explicit empty) opts out of V-model defaults."""
    config = _make_config([])
    items = [
        {"id": "SRS-001", "derives_from": [], "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is True
    assert "No required_traceability rules" in result["summary"]


def test_none_rules_applies_vmodel_defaults():
    """required_traceability=None (not configured) falls back to V-model defaults."""
    config = ProjectConfig(
        doc_types=[
            DocTypeConfig(code="SRS", name="Software Requirement", prefix="SRS-"),
            DocTypeConfig(code="SYS", name="System Requirement", prefix="SYS-"),
        ],
    )
    # SRS-001 has no derives_from SYS → should fail under V-model defaults
    items = [
        {"id": "SRS-001", "derives_from": [], "all_linked_uids": []},
        {"id": "SYS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is False
    assert any(f["id"] == "SRS-001" for f in result["failures"])


def test_vmodel_defaults_pass_when_links_correct():
    """V-model default rules pass when items have proper upstream links."""
    config = ProjectConfig(
        doc_types=[
            DocTypeConfig(code="SRS", name="Software Requirement", prefix="SRS-"),
            DocTypeConfig(code="SYS", name="System Requirement", prefix="SYS-"),
        ],
    )
    items = [
        {"id": "SRS-001", "derives_from": ["SYS-001"], "all_linked_uids": ["SYS-001"]},
        {"id": "SYS-001", "all_linked_uids": []},
    ]
    result = check_required_traceability(items, config)
    assert result["passed"] is True


# ── orphans key preserved for API compat ─────────────────────────────────────

def test_orphans_key_always_empty_list():
    """check_traceability always returns orphans=[] (deprecated field preserved for compat)."""
    from dhfkit.traceability import check_traceability

    config = ProjectConfig(
        doc_types=[
            DocTypeConfig(code="SRS", name="Software Requirement", prefix="SRS-"),
            DocTypeConfig(code="SYS", name="System Requirement", prefix="SYS-"),
        ],
        required_traceability=[],
    )
    items = [
        {"id": "SRS-001", "derives_from": [], "all_linked_uids": []},
    ]
    result = check_traceability(items, config)
    assert result["orphans"] == []
    assert result["deprecation_warnings"] == []
