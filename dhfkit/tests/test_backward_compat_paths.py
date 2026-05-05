"""Tests for flat documents/specs/ template layout.

The flat layout is the only supported layout. Legacy nested/old
layouts have been removed.
"""

from pathlib import Path
import yaml
import pytest


def _make_minimal_config(config_dir: Path):
    """Create a minimal global.yaml + doc_types so the adapter can load."""
    global_yaml = {
        "global_lifecycle": {"states": []},
        "traceability_matrices": [],
        "document_specifications": {},
        "test_integration": {},
    }
    (config_dir / "global.yaml").write_text(yaml.dump(global_yaml))
    doc_types_dir = config_dir / "doc_types"
    doc_types_dir.mkdir(parents=True, exist_ok=True)


def _make_adapter(dhf_root: Path):
    from dhfkit.local_adapter import LocalDHFAdapter
    (dhf_root / "config").mkdir(exist_ok=True)
    _make_minimal_config(dhf_root / "config")
    (dhf_root / "items").mkdir(exist_ok=True)
    return LocalDHFAdapter(dhf_root)


# ── Flat layout: documents/specs/*.j2 ───────────────────────────────────────

def test_flat_specs_with_j2_is_preferred(tmpdir):
    """Flat specs/ with .j2 files is the canonical layout."""
    dhf_root = Path(tmpdir)
    specs_dir = dhf_root / "documents" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "test.j2").write_text("")

    adapter = _make_adapter(dhf_root)
    assert adapter._resolve_template_dir() == specs_dir


def test_defaults_to_specs_when_none_exist(tmpdir):
    """Returns documents/specs/ when the directory doesn't exist yet."""
    dhf_root = Path(tmpdir)

    adapter = _make_adapter(dhf_root)
    assert adapter._resolve_template_dir() == dhf_root / "documents" / "specs"


# ── Fail-fast: missing .j2 templates ────────────────────────────────────────

def test_fails_when_specs_exists_but_no_j2(tmpdir):
    """Raises FileNotFoundError when specs/ dir exists but has no .j2 files."""
    dhf_root = Path(tmpdir)
    specs_dir = dhf_root / "documents" / "specs"
    specs_dir.mkdir(parents=True)
    # Empty dir — no .j2 templates

    adapter = _make_adapter(dhf_root)
    with pytest.raises(FileNotFoundError, match="No .j2 templates found"):
        adapter._resolve_template_dir()
