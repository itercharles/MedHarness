"""Specification templates: the project's first, the package's for the rest.

The project no longer carries copies of the templates. It overrides one by
placing a file of the same name in `documents/specs/`, which is also where the
rendered Markdown lands — so that directory holding no templates is normal, and
used to raise "No .j2 templates found".
"""

from pathlib import Path

import yaml

from dhfkit.paths import DEFAULT_SPECS_DIR


def _adapter(dhf_root: Path):
    from dhfkit.local_adapter import LocalDHFAdapter

    (dhf_root / "config").mkdir(parents=True, exist_ok=True)
    (dhf_root / "config" / "global.yaml").write_text(yaml.dump({"project_name": "T"}))
    (dhf_root / "items").mkdir(exist_ok=True)
    return LocalDHFAdapter(dhf_root)


def test_the_package_supplies_templates_the_project_does_not_have(tmp_path: Path) -> None:
    assert _adapter(tmp_path)._template_dirs() == [DEFAULT_SPECS_DIR]


def test_the_project_is_searched_first(tmp_path: Path) -> None:
    specs = tmp_path / "documents" / "specs"
    specs.mkdir(parents=True)
    assert _adapter(tmp_path)._template_dirs() == [specs, DEFAULT_SPECS_DIR]


def test_a_project_template_overrides_the_default(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    name = "requirements_specification.md.j2"
    specs = tmp_path / "documents" / "specs"
    specs.mkdir(parents=True)
    (specs / name).write_text("OVERRIDDEN {{ project_name }}")

    from dhfkit.document_generation import DocumentGenerator

    gen = DocumentGenerator(adapter._loader, adapter._config, adapter._template_dirs())
    assert gen.jinja_env.get_template(name).render(project_name="X") == "OVERRIDDEN X"


def test_a_specs_directory_of_rendered_markdown_is_fine(tmp_path: Path) -> None:
    """Where the output goes, and nothing else: it must not be an error."""
    specs = tmp_path / "documents" / "specs"
    specs.mkdir(parents=True)
    (specs / "software_requirement_specification.md").write_text("# rendered")
    assert DEFAULT_SPECS_DIR in _adapter(tmp_path)._template_dirs()
