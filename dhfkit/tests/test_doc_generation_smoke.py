"""Smoke test: a project template in DHF/documents/specs renders a specification."""

import tempfile
from pathlib import Path
import yaml
import shutil


def _make_test_dhf_with_flat_templates(tmpdir: str) -> tuple[Path, Path]:
    """Create a minimal DHF with flat templates and doc_specs config.

    Mimics the standard DHF structure where the project root contains a DHF/ subdirectory.
    Returns (project_root, dhf_root, specs_dir).
    """
    project_root = Path(tmpdir) / "test_project"
    dhf_root = project_root / "DHF"
    specs_dir = dhf_root / "documents" / "specs"
    specs_dir.mkdir(parents=True)

    # Flat template layout
    (specs_dir / "test_template.md.j2").write_text(
        "# {{ doc_type_name }} Specification\n\n"
        "**Version:** {{ version }}\n\n"
        "{% for item in items %}\n"
        "## {{ item.id }}\n\n{{ item.content }}\n\n"
        "{% endfor %}"
    )
    styles_dir = specs_dir / "styles"
    styles_dir.mkdir()
    (styles_dir / "default.css").write_text("body { font-family: sans-serif; }")

    # Minimal global.yaml with document_specifications
    config_dir = dhf_root / "config"
    config_dir.mkdir(parents=True)
    config = {
        "global_lifecycle": {"states": []},
        "traceability_matrices": [],
        "document_specifications": {
            "TEST": {
                "template": "test_template.md.j2",
                "doc_type_name": "Test Spec",
            }
        },
    }
    (config_dir / "global.yaml").write_text(yaml.dump(config))

    # Doc types
    doc_types_dir = config_dir / "doc_types"
    doc_types_dir.mkdir()
    (doc_types_dir / "test.yaml").write_text(yaml.dump({
        "code": "TEST",
        "name": "Test Doc",
        "prefix": "TEST-",
        "directory": "99_test",
        "icon": "🧪",
        "page_enabled": True,
        "page_number": 99,
        "properties": ["id", {"name": "title", "format": "short_text"}, {"name": "content", "format": "long_text"}],
    }))

    # Create minimal item data
    items_dir = dhf_root / "items" / "99_test"
    items_dir.mkdir(parents=True)
    (items_dir / "TEST-001.yaml").write_text(yaml.dump({
        "id": "TEST-001",
        "title": "Smoke Test Item",
        "content": "This is a smoke test.",
    }))

    return project_root, dhf_root, specs_dir


def test_a_project_template_renders(tmpdir):
    from dhfkit.item_store import ItemStore

    project_root, dhf_root, specs_dir = _make_test_dhf_with_flat_templates(tmpdir)
    out = Path(tmpdir) / "out"

    result = ItemStore(dhf_root).render_spec("TEST", "html", out, "3.1.0")

    content = Path(result["path"]).read_text()
    assert "Test Spec Specification" in content
    assert "TEST-001" in content and "This is a smoke test" in content
    assert "3.1.0" in content
    assert (specs_dir / "test_template.md.j2").exists()
    assert not list(specs_dir.glob("*.md")), "rendering wrote into the DHF"
