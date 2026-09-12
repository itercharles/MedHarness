"""A cycle must fail loudly, in both the verdict and the text.

Cycle detection shipped in 0.20.0 with two holes. `check_traceability` computed
`passed` without consulting cycles and its summary said "All checks passed",
so every caller but the gate saw a clean DHF. And no stderr line existed for a
cycle, so the build failed with nothing printed to say why.
"""

from __future__ import annotations

from dhfkit.models.config import DocTypeConfig, ProjectConfig
from medharness.services.traceability import check_traceability

CONFIG = ProjectConfig(
    doc_types=[
        DocTypeConfig(code="SYS", name="System Requirement", prefix="SYS-"),
        DocTypeConfig(code="SRS", name="Software Requirement", prefix="SRS-"),
    ],
    required_traceability=[],
)
CYCLE = [
    {"id": "SYS-001", "derives_from": ["SRS-001"], "all_linked_uids": ["SRS-001"]},
    {"id": "SRS-001", "derives_from": ["SYS-001"], "all_linked_uids": ["SYS-001"]},
]


def test_a_cycle_is_found() -> None:
    assert check_traceability(CYCLE, CONFIG)["cycles"] == [["SRS-001", "SYS-001"]]


def test_a_cycle_makes_the_analysis_fail() -> None:
    result = check_traceability(CYCLE, CONFIG)
    assert result["passed"] is False, (
        "the gate compensated for this downstream; every other caller of "
        "check_traceability saw a DHF with a cycle reported as passing"
    )


def test_the_summary_names_the_cycle() -> None:
    summary = check_traceability(CYCLE, CONFIG)["summary"]
    assert "cycle" in summary.lower(), summary
    assert "All checks passed" not in summary
