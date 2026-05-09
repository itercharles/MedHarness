"""Tests for the PDF traceability matrix output produced by _write_traceability_report."""

import json
import sys
from pathlib import Path

import pytest

from medharness import _helpers
from medharness.core import MedHarnessCore


def _weasyprint_runtime_ok() -> bool:
    """WeasyPrint imports its native libs eagerly — verify they actually loaded."""
    try:
        from weasyprint import HTML  # noqa: F401
        import markdown  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


def test_write_report_with_pdf_path_writes_both(stub_adapter, tmp_path):
    """A .pdf output path produces both a PDF and a sibling .json file."""
    if not _weasyprint_runtime_ok():
        pytest.skip("WeasyPrint runtime libraries not available")

    core = MedHarnessCore(stub_adapter)
    output = tmp_path / "traceability" / "Requirements_Traceability_Report.pdf"

    result = _helpers._write_traceability_report(
        core, ("UC", "CRS", "SYS", "SRS"), output
    )

    assert output.exists(), "PDF output should be written at the requested path"
    assert output.stat().st_size > 0, "PDF should be non-empty"
    assert output.read_bytes()[:5] == b"%PDF-", "File should be a real PDF"

    json_path = output.with_suffix(".json")
    assert json_path.exists(), "JSON sidecar should still be written"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "rows" in payload and "columns" in payload

    assert result["path"] == str(output)
    assert result["pdf_path"] == str(output)
    assert result["json_path"] == str(json_path)


def test_write_report_with_json_path_only_writes_json(stub_adapter, tmp_path):
    """A non-PDF output path keeps the legacy JSON-only behavior."""
    core = MedHarnessCore(stub_adapter)
    output = tmp_path / "trace" / "report.json"

    result = _helpers._write_traceability_report(
        core, ("UC", "CRS", "SYS", "SRS"), output
    )

    assert output.exists()
    assert "pdf_path" not in result
    assert result["path"] == str(output)
    assert result["json_path"] == str(output)


def test_write_report_skips_pdf_when_weasyprint_missing(
    stub_adapter, tmp_path, monkeypatch
):
    """If WeasyPrint is unavailable, JSON is written and pdf_skipped is reported."""
    core = MedHarnessCore(stub_adapter)
    output = tmp_path / "traceability" / "report.pdf"

    monkeypatch.setitem(sys.modules, "weasyprint", None)

    result = _helpers._write_traceability_report(
        core, ("UC", "CRS", "SYS", "SRS"), output
    )

    assert not output.exists(), "PDF should not be written when WeasyPrint missing"
    json_path = output.with_suffix(".json")
    assert json_path.exists()
    assert result["path"] == str(json_path)
    assert "pdf_skipped" in result


def test_format_matrix_markdown_renders_summary_and_matrix():
    """The Markdown formatter produces the expected sections from a matrix payload."""
    matrix = {
        "columns": ["UC", "CRS", "SYS"],
        "rows": [
            {"UC": "UC-001", "CRS": "CRS-001", "SYS": "SYS-001",
             "verification_status": "verified"},
            {"UC": "UC-002", "CRS": "CRS-002", "SYS": None,
             "verification_status": "not_verified"},
        ],
        "coverage": {
            "SYS": [
                {"id": "SYS-001", "title": "Boot", "status": "verified",
                 "tests": ["TC-001"]},
            ],
        },
        "test_results": {
            "TC-001": {"id": "TC-001", "testing_status": "PASS"},
        },
    }
    md = _helpers._format_traceability_matrix_markdown(matrix)

    assert "# Requirements Traceability Matrix" in md
    assert "UC → CRS → SYS" in md
    assert "**Total chains:** 2" in md
    assert "**Complete chains:** 1" in md
    assert "| UC-001 | CRS-001 | SYS-001 | verified |" in md
    assert "## Coverage by Level" in md
    assert "TC-001" in md
    assert "**Passed:** 1" in md


def test_format_matrix_markdown_handles_dict_tests():
    """Coverage `tests` may be dicts (from inject_junit_results), not strings.

    Regression: 0.3.3 raised TypeError: sequence item 0: expected str instance,
    dict found when joining the test list, because MedHarnessCore stores each
    test as {"name", "status"}.
    """
    matrix = {
        "columns": ["SRS"],
        "rows": [{"SRS": "SRS-010", "verification_status": "verified"}],
        "coverage": {
            "SRS": [
                {
                    "id": "SRS-010",
                    "title": "Boot path",
                    "status": "verified",
                    "tests": [
                        {"name": "Boot › cold start", "status": "PASS"},
                        {"name": "Boot › warm start", "status": "FAIL"},
                    ],
                },
            ],
        },
        "test_results": {},
    }
    md = _helpers._format_traceability_matrix_markdown(matrix)
    assert "Boot › cold start [PASS]" in md
    assert "Boot › warm start [FAIL]" in md
