"""Smoke test: document generation works with template-only specs/ directory.

Verifies that generated specification Markdown is produced correctly
without pre-existing committed .md files in the specs/ directory.
"""

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
                "output": "DHF/documents/specs/Test_Specification.md",
                "doc_type_name": "Test Spec",
            }
        },
        "test_integration": {},
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


def test_doc_generation_creates_spec_md_from_templates_only(tmpdir):
    """Generate a spec from a clean template-only DHF."""
    from dhfkit.local_adapter import LocalDHFAdapter

    project_root, dhf_root, specs_dir = _make_test_dhf_with_flat_templates(tmpdir)
    output_file = dhf_root / "documents" / "specs" / "Test_Specification.md"

    assert not output_file.exists(), "Output .md must not exist before generation"

    adapter = LocalDHFAdapter(dhf_root)
    result = adapter.generate_doc("TEST")

    assert output_file.exists(), f"Expected {output_file} to be created"
    content = output_file.read_text()
    assert "Test Spec Specification" in content
    assert "TEST-001" in content
    assert "This is a smoke test" in content
    assert result is not None


def test_generation_cleans_up_after_itself(tmpdir):
    """Generated spec is placed at configured output path, not polluting template dir."""
    from dhfkit.local_adapter import LocalDHFAdapter

    project_root, dhf_root, specs_dir = _make_test_dhf_with_flat_templates(tmpdir)

    adapter = LocalDHFAdapter(dhf_root)
    adapter.generate_doc("TEST")

    # Template .j2 files are still there
    assert (specs_dir / "test_template.md.j2").exists()
    # Generated .md is at the configured output path
    assert (dhf_root / "documents" / "specs" / "Test_Specification.md").exists()
