"""Tests for specification generation and export.

These cover four defects that shipped in generated regulatory documents:

* every ``SYSARCH-*`` item was emitted into the *system requirements*
  specification, because the item filter matched on the bare code and
  ``"SYSARCH-001".startswith("SYS")`` is true;
* the document version was bumped on every run, so a CI job that regenerated
  docs inflated the version of a controlled document with nothing changed;
* PDFs were written to a hardcoded ``/tmp`` path, so concurrent runs on one
  runner overwrote each other;
* export required WeasyPrint's native libraries, which the base install does
  not provide — the fully-built HTML was constructed and then discarded.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.cli import main
from dhfkit.local_adapter import LocalDHFAdapter


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    """Build a DHF with dhfkit alone.

    dhfkit must not import medharness (docs/architecture.md), and its suite has
    to run standalone — so this copies the bundled templates directly rather
    than calling medharness's scaffolder.
    """
    import shutil

    templates = Path(__file__).resolve().parents[1] / "templates"
    root = tmp_path / "DHF"
    for src, dst in (("config", "config"), ("specs", "documents/specs"),
                     ("plans", "documents/plans"), ("items", "items")):
        source = templates / src
        if source.is_dir():
            shutil.copytree(source, root / dst, dirs_exist_ok=True)
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".yaml", ".yml", ".j2"}:
            text = path.read_text()
            if "{{project_name}}" in text:
                path.write_text(text.replace("{{project_name}}", "Trial"))
    return root


def _generate(dhf: Path, code: str) -> str:
    r = CliRunner().invoke(main, ["--dhf", str(dhf), "doc", "generate", code])
    assert r.exit_code == 0, r.output
    return r.output


def _spec_text(dhf: Path, filename: str) -> str:
    return (dhf / "documents" / "specs" / filename).read_text()


def _version(text: str) -> str:
    return re.search(r'\|\s*\*\*Version\*\*\s*\|\s*([\d.]+)\s*\|', text).group(1)


class TestItemFilter:
    def test_sysarch_items_stay_out_of_the_sys_spec(self, dhf: Path) -> None:
        _generate(dhf, "SYS")
        text = _spec_text(dhf, "system_requirement_specification.md")
        assert "SYS-001" in text
        assert "SYSARCH-001" not in text

    def test_sysarch_spec_still_contains_its_own_items(self, dhf: Path) -> None:
        _generate(dhf, "SYSARCH")
        text = _spec_text(dhf, "architecture_design_specification.md")
        assert "SYSARCH-001" in text

    def test_filter_uses_configured_prefix(self, dhf: Path) -> None:
        """Guard the mechanism, not just the SYS/SYSARCH instance of it."""
        config = LocalDHFAdapter(dhf)._config
        assert config.get_doc_type("SYS").prefix == "SYS-"
        assert not "SYSARCH-001".startswith("SYS-")


class TestVersioning:
    def test_regeneration_without_changes_keeps_the_version(self, dhf: Path) -> None:
        _generate(dhf, "SRS")
        first = _version(_spec_text(dhf, "software_requirement_specification.md"))
        for _ in range(3):
            _generate(dhf, "SRS")
        assert _version(_spec_text(dhf, "software_requirement_specification.md")) == first

    def test_content_change_bumps_the_version(self, dhf: Path) -> None:
        _generate(dhf, "SRS")
        before = _version(_spec_text(dhf, "software_requirement_specification.md"))

        srs = next((dhf / "items" / "03_srs").glob("SRS-*.yaml"))
        srs.write_text(srs.read_text().replace("Starter Software Requirement",
                                               "Session timeout after 15 minutes"))
        _generate(dhf, "SRS")

        after = _spec_text(dhf, "software_requirement_specification.md")
        assert _version(after) != before
        assert "Session timeout" in after

    def test_unchanged_regeneration_does_not_rewrite_the_file(self, dhf: Path) -> None:
        _generate(dhf, "SRS")
        path = dhf / "documents" / "specs" / "software_requirement_specification.md"
        before = path.read_bytes()
        _generate(dhf, "SRS")
        assert path.read_bytes() == before


class TestTitles:
    def test_srs_title_is_not_doubled(self, dhf: Path) -> None:
        _generate(dhf, "SRS")
        title = _spec_text(dhf, "software_requirement_specification.md").splitlines()[0]
        assert title == "# Software Requirement Specification"

    def test_absent_status_renders_a_usable_badge(self, dhf: Path) -> None:
        _generate(dhf, "SRS")
        text = _spec_text(dhf, "software_requirement_specification.md")
        assert 'class="status-"' not in text
        assert "UNKNOWN" in text


class TestHtmlExport:
    def test_export_defaults_to_html(self, dhf: Path) -> None:
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "doc", "export", "SRS"])
        assert r.exit_code == 0, r.output
        assert "html_path" in r.output

    def test_html_is_self_contained(self, dhf: Path) -> None:
        CliRunner().invoke(main, ["--dhf", str(dhf), "doc", "export", "SRS"])
        html = next((dhf / "documents" / "exports").glob("*.html")).read_text()
        assert html.startswith("<!DOCTYPE html>")
        assert "<style>" in html          # CSS inlined, no external request
        assert "<table>" in html          # markdown tables rendered
        assert "Software Requirement Specification" in html

    def test_export_honours_out_dir(self, dhf: Path, tmp_path: Path) -> None:
        target = tmp_path / "somewhere-else"
        r = CliRunner().invoke(
            main, ["--dhf", str(dhf), "doc", "export", "SRS", "--out-dir", str(target)]
        )
        assert r.exit_code == 0, r.output
        assert list(target.glob("*.html"))

    def test_output_is_scoped_to_the_dhf(self, dhf: Path) -> None:
        """The old path was a fixed /tmp location shared by every run.

        Asserting the absence of "/tmp" would be wrong — pytest's own tmp_path
        lives under /tmp on Linux. What matters is that the destination derives
        from the DHF, so two DHFs on one runner cannot collide.
        """
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "doc", "export", "SRS"])
        assert r.exit_code == 0, r.output
        written = next((dhf / "documents" / "exports").glob("*.html"))
        assert written.is_relative_to(dhf)


class TestPdfFallback:
    def test_missing_renderer_reports_how_to_fix(self, dhf: Path, monkeypatch) -> None:
        """No native libs must yield an actionable message, not a traceback."""
        import builtins

        real_import = builtins.__import__

        def _no_weasyprint(name, *args, **kwargs):
            if name == "weasyprint":
                raise ImportError("No module named 'weasyprint'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _no_weasyprint)
        r = CliRunner().invoke(
            main, ["--dhf", str(dhf), "doc", "export", "SRS", "--format", "pdf"]
        )
        assert r.exit_code != 0
        assert "medharness[docs]" in r.output
        assert "HTML export instead" in r.output
