"""Unit tests for build_risk_chain, find_affected_risks, and format_traceability_report."""

from dhfkit.models.config import ProjectConfig, DocTypeConfig
from dhfkit.traceability import build_risk_chain, find_affected_risks, format_traceability_report


def _config() -> ProjectConfig:
    return ProjectConfig(
        doc_types=[
            DocTypeConfig(code="RISK", name="Risk", prefix="RISK-"),
            DocTypeConfig(code="RCM", name="Risk Control Measure", prefix="RCM-"),
            DocTypeConfig(code="SYS", name="System Requirement", prefix="SYS-"),
        ],
    )


def _items():
    return [
        {"id": "RISK-001", "title": "Incorrect dose calculation", "all_linked_uids": []},
        {"id": "RISK-002", "title": "Data loss on power failure", "all_linked_uids": []},
        {
            "id": "RCM-001",
            "title": "Range check on dose input",
            "mitigates": ["RISK-001"],
            "implements": ["SYS-004", "SYS-007"],
            "all_linked_uids": ["RISK-001", "SYS-004", "SYS-007"],
        },
        {
            "id": "RCM-002",
            "title": "Persistent write with checksum",
            "mitigates": ["RISK-002"],
            "implements": ["SYS-010"],
            "all_linked_uids": ["RISK-002", "SYS-010"],
        },
        {"id": "SYS-004", "title": "...", "all_linked_uids": []},
        {"id": "SYS-007", "title": "...", "all_linked_uids": []},
        {"id": "SYS-010", "title": "...", "all_linked_uids": []},
    ]


def test_build_risk_chain_structure():
    chain = build_risk_chain(_items(), _config())
    assert len(chain) == 2
    assert chain[0]["risk_id"] == "RISK-001"
    assert chain[0]["title"] == "Incorrect dose calculation"
    assert len(chain[0]["rcms"]) == 1
    rcm = chain[0]["rcms"][0]
    assert rcm["rcm_id"] == "RCM-001"
    assert rcm["implements"] == ["SYS-004", "SYS-007"]


def test_build_risk_chain_no_rcm():
    items = [
        {"id": "RISK-001", "title": "Unmitigated risk", "all_linked_uids": []},
    ]
    chain = build_risk_chain(items, _config())
    assert chain[0]["rcms"] == []


def test_build_risk_chain_string_mitigates():
    items = [
        {"id": "RISK-001", "title": "Risk", "all_linked_uids": []},
        {
            "id": "RCM-001",
            "title": "Control",
            "mitigates": "RISK-001",
            "implements": "SYS-001",
            "all_linked_uids": ["RISK-001", "SYS-001"],
        },
    ]
    chain = build_risk_chain(items, _config())
    assert chain[0]["rcms"][0]["implements"] == ["SYS-001"]


def test_build_risk_chain_missing_doc_types():
    config = ProjectConfig(doc_types=[
        DocTypeConfig(code="SYS", name="System Requirement", prefix="SYS-"),
    ])
    chain = build_risk_chain(_items(), config)
    assert chain == []


def test_risk_chain_in_report():
    result = {
        "passed": True,
        "summary": "All checks passed.",
        "required": {"passed": True, "failures": []},
        "coverage": [],
        "orphans": [],
        "risk_chain": [
            {
                "risk_id": "RISK-001",
                "title": "Incorrect dose calculation",
                "rcms": [
                    {"rcm_id": "RCM-001", "title": "Range check", "implements": ["SYS-004"]},
                ],
            }
        ],
    }
    report = format_traceability_report(result)
    assert "Risk Chain" in report
    assert "RISK-001" in report
    assert "Incorrect dose calculation" in report
    assert "RCM-001" in report
    assert "Range check" in report
    assert "SYS-004" in report


def test_risk_chain_no_rcms_label():
    result = {
        "passed": True,
        "summary": "All checks passed.",
        "required": {"passed": True, "failures": []},
        "coverage": [],
        "orphans": [],
        "risk_chain": [
            {"risk_id": "RISK-001", "title": "Unmitigated", "rcms": []},
        ],
    }
    report = format_traceability_report(result)
    assert "no RCMs linked" in report


def test_report_omits_risk_chain_section_when_empty():
    result = {
        "passed": True,
        "summary": "All checks passed.",
        "required": {"passed": True, "failures": []},
        "coverage": [],
        "orphans": [],
        "risk_chain": [],
    }
    report = format_traceability_report(result)
    assert "Risk Chain" not in report


# ── find_affected_risks ──────────────────────────────────────────────────────

def test_find_affected_risks_basic():
    items = [
        {"id": "RISK-001", "title": "Incorrect dose", "all_linked_uids": []},
        {
            "id": "RCM-001",
            "title": "Range check",
            "mitigates": ["RISK-001"],
            "implements": ["SYS-004"],
            "all_linked_uids": ["RISK-001", "SYS-004"],
        },
        {"id": "SYS-004", "title": "Dose input validation", "all_linked_uids": []},
    ]
    result = find_affected_risks({"SYS-004"}, items, _config())
    assert len(result) == 1
    assert result[0]["risk_id"] == "RISK-001"
    assert result[0]["via_rcms"] == ["RCM-001"]


def test_find_affected_risks_no_overlap():
    items = _items()
    result = find_affected_risks({"SYS-999"}, items, _config())
    assert result == []


def test_find_affected_risks_multiple_risks():
    items = [
        {"id": "RISK-001", "title": "Risk A", "all_linked_uids": []},
        {"id": "RISK-002", "title": "Risk B", "all_linked_uids": []},
        {
            "id": "RCM-001",
            "title": "Control 1",
            "mitigates": ["RISK-001"],
            "implements": ["SYS-001"],
            "all_linked_uids": [],
        },
        {
            "id": "RCM-002",
            "title": "Control 2",
            "mitigates": ["RISK-002"],
            "implements": ["SYS-001"],
            "all_linked_uids": [],
        },
    ]
    result = find_affected_risks({"SYS-001"}, items, _config())
    assert {r["risk_id"] for r in result} == {"RISK-001", "RISK-002"}


def test_find_affected_risks_rcm_mitigates_multiple_risks():
    items = [
        {"id": "RISK-001", "title": "Risk A", "all_linked_uids": []},
        {"id": "RISK-002", "title": "Risk B", "all_linked_uids": []},
        {
            "id": "RCM-001",
            "title": "Combined control",
            "mitigates": ["RISK-001", "RISK-002"],
            "implements": ["SYS-001"],
            "all_linked_uids": [],
        },
    ]
    result = find_affected_risks({"SYS-001"}, items, _config())
    assert len(result) == 2
    assert result[0]["via_rcms"] == ["RCM-001"]


def test_find_affected_risks_string_fields():
    items = [
        {"id": "RISK-001", "title": "Risk", "all_linked_uids": []},
        {
            "id": "RCM-001",
            "title": "Control",
            "mitigates": "RISK-001",
            "implements": "SYS-001",
            "all_linked_uids": [],
        },
    ]
    result = find_affected_risks({"SYS-001"}, items, _config())
    assert result[0]["risk_id"] == "RISK-001"


def test_find_affected_risks_missing_doc_types():
    config = ProjectConfig(doc_types=[
        DocTypeConfig(code="SYS", name="System Requirement", prefix="SYS-"),
    ])
    result = find_affected_risks({"SYS-001"}, _items(), config)
    assert result == []


def test_find_affected_risks_empty_changed_ids():
    result = find_affected_risks(set(), _items(), _config())
    assert result == []
