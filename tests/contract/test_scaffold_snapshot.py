"""Scaffold contract tests: verify init generates the expected structure.

These protect the stable scaffold output contract. Changes to the expected
structure require a MAJOR version bump.

"""

import tempfile
from pathlib import Path

import pytest

from medharness.workflows.init import _scaffold_dhf, _replace_placeholders


class TestScaffoldStructure:
    """Verify scaffolded DHF repo has the expected structure."""

    CORE_DIRS = [
        "DHF",
        "DHF/config",
        "DHF/items",
    ]

    CORE_FILES = [
        "DHF/config/global.yaml",
        "DHF/README.md",
    ]

    REQUIRED_TEMPLATES = [
        "requirements_specification.md.j2",
        "architecture_design_specification.md.j2",
        "customer_requirement_specification.md.j2",
        "change_request_specification.md.j2",
        "risk_specification.md.j2",
        "rcm_specification.md.j2",
        "test_specification.md.j2",
        "traceability_matrix.md.j2",
    ]

    REQUIRED_DOC_TYPES = [
        "uc.yaml", "crs.yaml", "sys.yaml", "srs.yaml",
        "swdd.yaml", "sysarch.yaml", "risk.yaml", "rcm.yaml",
        "cr.yaml", "rel.yaml", "def.yaml", "soup.yaml",
    ]

    @pytest.fixture
    def scaffolded(self):
        with tempfile.TemporaryDirectory() as tmp:
            dhf_dir = Path(tmp) / "test-dhf"
            _scaffold_dhf(dhf_dir)
            _replace_placeholders(dhf_dir, "Test Project")
            yield dhf_dir

    def test_core_directories_exist(self, scaffolded):
        """
        Scaffold creates all core directories.

        """
        for d in self.CORE_DIRS:
            assert (scaffolded / d).is_dir(), f"Missing directory: {d}"

    def test_core_files_exist(self, scaffolded):
        """
        Scaffold creates all core files.

        """
        for f in self.CORE_FILES:
            assert (scaffolded / f).is_file(), f"Missing file: {f}"

    def test_the_defaults_are_not_copied(self, scaffolded):
        """The project inherits doc types and templates from the package, so it
        keeps getting them as MedHarness changes them. A copy froze them."""
        assert not (scaffolded / "DHF" / "config" / "doc_types").exists()
        assert not (scaffolded / "DHF" / "documents" / "specs").exists()

    def test_the_bare_project_has_every_default_type(self, scaffolded):
        from dhfkit.models.config import ProjectConfig

        config = ProjectConfig.load(scaffolded / "DHF" / "config")
        codes = {dt.code for dt in config.doc_types}
        assert {f.split(".")[0].upper() for f in self.REQUIRED_DOC_TYPES} <= codes

    def test_every_default_template_is_found(self, scaffolded):
        from dhfkit.local_adapter import LocalDHFAdapter

        dirs = LocalDHFAdapter(scaffolded / "DHF")._template_dirs()
        for tmpl in self.REQUIRED_TEMPLATES:
            assert any((d / tmpl).is_file() for d in dirs), f"no {tmpl} anywhere"

    def test_placeholder_substitution(self, scaffolded):
        """
        Placeholders are substituted in scaffolded content.

        """
        readme = (scaffolded / "DHF" / "README.md").read_text()
        assert "Test Project" in readme
        assert "{{project_name}}" not in readme

    def test_global_yaml_project_name_set(self, scaffolded):
        """
        global.yaml has the correct project_name.

        """
        import yaml
        g = scaffolded / "DHF" / "config" / "global.yaml"
        data = yaml.safe_load(g.read_text())
        # The exact key depends on template content; check that project_name
        # is present and substituted
        content = g.read_text()
        assert "Test Project" in content
        assert "{{project_name}}" not in content

    def test_starter_items_copied(self, scaffolded):
        """
        All 12 starter sample items are copied from templates.

        """
        items_dir = scaffolded / "DHF" / "items"
        item_files = list(items_dir.rglob("*.yaml"))
        assert len(item_files) == 13, f"Expected 13 starter items, got {len(item_files)}"

    def test_no_embedded_engine_files(self, scaffolded):
        """
        Scaffold does not embed dhfkit, pyproject.toml, or medharness.

        """
        assert not (scaffolded / "dhfkit").exists(), "dhfkit/ should not be in generated repo"
        assert not (scaffolded / "pyproject.toml").exists(), "pyproject.toml should not be in generated repo"
        assert not (scaffolded / "medharness").exists(), "medharness/ should not be in generated repo"

    def test_double_scaffold_does_not_crash(self):
        """
        Running scaffold twice does not crash.

        """
        with tempfile.TemporaryDirectory() as tmp:
            dhf_dir = Path(tmp) / "test-dhf"
            _scaffold_dhf(dhf_dir)
            first = sorted(p.relative_to(dhf_dir) for p in dhf_dir.rglob("*") if p.is_file())
            _scaffold_dhf(dhf_dir)  # should not raise
            second = sorted(p.relative_to(dhf_dir) for p in dhf_dir.rglob("*") if p.is_file())

            # "does not crash" is not the property that matters: the scaffold
            # has to still be there. Without this the test passes if the second
            # call silently wipes it.
            assert second == first, "the second scaffold changed the file set"
            assert first, "the first scaffold produced nothing"
