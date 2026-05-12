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
        "DHF/config/doc_types",
        "DHF/documents",
        "DHF/documents/specs",
        "DHF/documents/plans",
        "DHF/items",
        "DHF/test-results",
        ".github",
        ".github/prompts",
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

    def test_all_templates_copied(self, scaffolded):
        """
        All spec templates are copied to DHF/documents/specs/.

        """
        specs_dir = scaffolded / "DHF" / "documents" / "specs"
        for tmpl in self.REQUIRED_TEMPLATES:
            assert (specs_dir / tmpl).is_file(), f"Missing template: {tmpl}"

    def test_css_stylesheet_copied(self, scaffolded):
        """
        PDF stylesheet is copied to specs/styles/.

        """
        assert (scaffolded / "DHF" / "documents" / "specs" / "styles" / "default.css").is_file()

    def test_all_doc_types_copied(self, scaffolded):
        """
        All doc type configs are copied to config/doc_types/.

        """
        dt_dir = scaffolded / "DHF" / "config" / "doc_types"
        for dt in self.REQUIRED_DOC_TYPES:
            assert (dt_dir / dt).is_file(), f"Missing doc type config: {dt}"

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
        assert len(item_files) == 12, f"Expected 12 starter items, got {len(item_files)}"

    def test_no_embedded_engine_files(self, scaffolded):
        """
        Scaffold does not embed dhfkit, pyproject.toml, or medharness.

        """
        assert not (scaffolded / "dhfkit").exists(), "dhfkit/ should not be in generated repo"
        assert not (scaffolded / "pyproject.toml").exists(), "pyproject.toml should not be in generated repo"
        assert not (scaffolded / "medharness").exists(), "medharness/ should not be in generated repo"

    def test_github_prompts_copied(self, scaffolded):
        """
        Prompt files are copied to .github/prompts/.

        """
        prompt_dir = scaffolded / ".github" / "prompts"
        prompts = list(prompt_dir.glob("*.md"))
        assert len(prompts) > 0, f"No prompt files found in {prompt_dir}"

    def test_test_results_dir_has_gitkeep(self, scaffolded):
        """
        test-results/ has a .gitkeep file.

        """
        assert (scaffolded / "DHF" / "test-results" / ".gitkeep").exists()


class TestScaffoldIdempotency:
    """Scaffolding should be idempotent — re-running should not fail."""

    def test_double_scaffold_does_not_crash(self):
        """
        Running scaffold twice does not crash.

        """
        with tempfile.TemporaryDirectory() as tmp:
            dhf_dir = Path(tmp) / "test-dhf"
            _scaffold_dhf(dhf_dir)
            _scaffold_dhf(dhf_dir)  # should not raise
