"""WeasyPrint's install banner must not land on stdout.

With the Python package installed and cairo/pango missing — the ordinary state
after `pip install medharness[docs]` on a bare machine — WeasyPrint prints a
banner to stdout on import. `build release` imported it even for an HTML
release, so its JSON answer began with `-----` and no caller could parse it.
"""

from __future__ import annotations

import sys

import pytest

from dhfkit.document_generation import load_weasyprint


@pytest.fixture
def noisy_weasyprint(tmp_path, monkeypatch):
    """A stand-in that behaves like the real one on a machine without cairo."""
    pkg = tmp_path / "weasyprint"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "print('-----\\nWeasyPrint could not import some external libraries.')\n"
        "class HTML:\n    pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "weasyprint", raising=False)
    yield
    sys.modules.pop("weasyprint", None)


def test_the_banner_goes_to_stderr(noisy_weasyprint, capsys) -> None:
    load_weasyprint()
    out, err = capsys.readouterr()
    assert out == "", f"stdout carried {out!r}"
    assert "could not import" in err, "the banner was swallowed rather than moved"


def test_it_still_returns_the_class(noisy_weasyprint) -> None:
    assert load_weasyprint().__name__ == "HTML"
