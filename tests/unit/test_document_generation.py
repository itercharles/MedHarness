"""Specification rendering, as `build release` does it.

These cover defects that shipped in generated regulatory documents:

* every ``SYSARCH-*`` item was emitted into the *system requirements*
  specification, because the item filter matched on the bare code and
  ``"SYSARCH-001".startswith("SYS")`` is true;
* the document version drifted from the release it shipped in;
* export required WeasyPrint's native libraries, which the base install does
  not provide.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dhfkit.item_store import ItemStore


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    """A DHF from the bundled templates."""
    import shutil

    from dhfkit.paths import DEFAULTS_DIR as templates
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


def _render(dhf: Path, code: str, out: Path, version: str = "1.2.0") -> str:
    result = ItemStore(dhf).render_spec(code, "html", out, version)
    return Path(result["path"]).read_text(encoding="utf-8")


class TestItemFilter:
    def test_sysarch_items_stay_out_of_the_sys_spec(self, dhf: Path, tmp_path: Path) -> None:
        text = _render(dhf, "SYS", tmp_path)
        assert "SYS-001" in text
        assert "SYSARCH-001" not in text

    def test_sysarch_spec_still_contains_its_own_items(self, dhf: Path, tmp_path: Path) -> None:
        assert "SYSARCH-001" in _render(dhf, "SYSARCH", tmp_path)


class TestVersion:
    def test_the_document_carries_the_release_version(self, dhf: Path, tmp_path: Path) -> None:
        result = ItemStore(dhf).render_spec("SRS", "html", tmp_path, "2.4.1")
        assert result["version"] == "2.4.1"
        assert Path(result["path"]).name == "SRS_Specification_2.4.1.html"
        assert "2.4.1" in Path(result["path"]).read_text(encoding="utf-8")

    def test_rendering_writes_nothing_into_the_dhf(self, dhf: Path, tmp_path: Path) -> None:
        before = sorted(p for p in dhf.rglob("*") if p.is_file())
        _render(dhf, "SRS", tmp_path)
        assert sorted(p for p in dhf.rglob("*") if p.is_file()) == before


class TestContent:
    def test_srs_title_is_not_doubled(self, dhf: Path, tmp_path: Path) -> None:
        html = _render(dhf, "SRS", tmp_path)
        assert html.count("Software Requirement Specification</h1>") == 1

    def test_an_item_without_a_status_gets_no_status_line(self, dhf: Path, tmp_path: Path) -> None:
        html = _render(dhf, "SRS", tmp_path)
        assert 'class="status-' not in html
        assert "UNKNOWN" not in html

    def test_html_is_self_contained(self, dhf: Path, tmp_path: Path) -> None:
        html = _render(dhf, "SRS", tmp_path)
        assert html.startswith("<!DOCTYPE html>")
        assert "<style>" in html          # CSS inlined, no external request
        assert "<table>" in html          # markdown tables rendered


class TestPdfFallback:
    def test_missing_renderer_reports_how_to_fix(self, dhf: Path, tmp_path: Path, monkeypatch) -> None:
        """No native libs must yield an actionable message, not a traceback."""
        import builtins

        real_import = builtins.__import__

        def _no_weasyprint(name, *args, **kwargs):
            if name == "weasyprint":
                raise ImportError("No module named 'weasyprint'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _no_weasyprint)
        with pytest.raises(RuntimeError, match=r"medharness\[docs\]"):
            ItemStore(dhf).render_spec("SRS", "pdf", tmp_path, "1.0.0")
