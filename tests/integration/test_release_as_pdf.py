"""`build release --doc-format pdf` writes real PDFs, and CI proves it.

The PDF path ran only on machines that happened to have WeasyPrint's native libraries, and
every other machine skipped its tests, so nothing guarded it. This test runs the command and
reads what it wrote; where the libraries are required (`MEDHARNESS_REQUIRE_PDF=1`, set in CI)
a machine without them fails instead of skipping.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from fixtures.starter import keep_the_starter_text
from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


def _pdf_libraries_load() -> bool:
    try:
        from dhfkit.document_generation import load_weasyprint

        load_weasyprint()
    except (ImportError, OSError):
        return False
    return True


REQUIRED = os.environ.get("MEDHARNESS_REQUIRE_PDF") == "1"


def test_the_libraries_are_present_where_they_are_required() -> None:
    if not REQUIRED:
        pytest.skip("MEDHARNESS_REQUIRE_PDF is not set")
    assert _pdf_libraries_load(), "WeasyPrint's native libraries did not load; CI installs them"


@pytest.mark.skipif(not REQUIRED and not _pdf_libraries_load(), reason="WeasyPrint's native libraries are not available")
def test_a_release_writes_its_documents_as_pdf(tmp_path: Path) -> None:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Pdf")
    dhf = tmp_path / "DHF"
    keep_the_starter_text(dhf)
    cr = next((dhf / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(cr.read_text())
    data.update(status="completed", implementation_notes="n", affected_risk_items=[],
                triage_result={"verdict": "approved"}, affected_items=[])
    cr.write_text(yaml.safe_dump(data))
    out = tmp_path / "rel"

    result = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "release", "--version", "1.0.0",
                                       "--out-dir", str(out), "--doc-format", "pdf"])

    assert result.exit_code == 0, result.stderr
    pdfs = sorted(out.rglob("*.pdf"))
    assert {p.parent.name for p in pdfs} >= {"specifications", "traceability"}
    assert all(p.read_bytes()[:5] == b"%PDF-" for p in pdfs), [p.name for p in pdfs]
    assert not list(out.rglob("*.html")), "a PDF release also wrote HTML"
