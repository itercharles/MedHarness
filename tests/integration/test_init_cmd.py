"""Tests for medharness init command.

Tests the zero-prompt init command:
- CLAUDE.md generation for single-repo layout
- DHF template placeholder substitution
- prompt scaffolding
- run_init guards and structure
"""

import inspect
from pathlib import Path

import pytest

from medharness.workflows.init import (
    _scaffold_dhf,
    _replace_placeholders,
    _write_claude_md,
    _write_gitignore,
)


class TestInitCmd:
    """init command — zero-prompt infrastructure onboarding command."""

    # ── CLAUDE.md ────────────────────────────────────────────────────────────

    def test_write_claude_md_creates_file(self, tmp_path):
        """_write_claude_md creates CLAUDE.md in project_dir."""
        _write_claude_md(tmp_path, "My Device")
        assert (tmp_path / "CLAUDE.md").exists()

    def test_write_claude_md_contains_project_name(self, tmp_path):
        """CLAUDE.md includes the project name."""
        _write_claude_md(tmp_path, "Cardiac Monitor")
        assert "Cardiac Monitor" in (tmp_path / "CLAUDE.md").read_text()

    def test_write_claude_md_mentions_cr_workflow(self, tmp_path):
        """CLAUDE.md references CR ID in PR title and testing conventions."""
        _write_claude_md(tmp_path, "Device")
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "CR ID" in content
        assert "ci test-coverage" in content

    def test_write_claude_md_single_repo_layout(self, tmp_path):
        """CLAUDE.md describes single-repo structure with DHF/ directory."""
        _write_claude_md(tmp_path, "Device")
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "DHF/" in content
        assert "DHF_REPO_TOKEN" not in content

    # ── placeholder substitution ─────────────────────────────────────────────

    def test_replace_placeholders_substitutes_project_name(self, tmp_path):
        """_replace_placeholders substitutes {{project_name}} in DHF template files."""
        (tmp_path / "DHF").mkdir(parents=True)
        readme = tmp_path / "README.md"
        readme.write_text("# {{project_name}} DHF")
        _replace_placeholders(tmp_path, "Test Device")
        assert "Test Device" in readme.read_text()
        assert "{{project_name}}" not in readme.read_text()

    def test_replace_placeholders_substitutes_medharness_version(self, tmp_path):
        """_replace_placeholders substitutes {{medharness_version}}."""
        (tmp_path / "DHF").mkdir(parents=True)
        wf = tmp_path / "workflow.yml"
        wf.write_text("pip install medharness=={{medharness_version}}")
        _replace_placeholders(tmp_path, "Device")
        assert "{{medharness_version}}" not in wf.read_text()

    def test_replace_placeholders_handles_missing_dir(self, tmp_path):
        """_replace_placeholders handles directories with no substitutable files gracefully."""
        (tmp_path / "DHF").mkdir()
        _replace_placeholders(tmp_path, "Device")

    # ── .gitignore ───────────────────────────────────────────────────────────

    def test_write_gitignore_creates_file(self, tmp_path):
        """_write_gitignore creates .gitignore with standard Python ignores."""
        result = _write_gitignore(tmp_path)
        assert result == tmp_path / ".gitignore"
        content = (tmp_path / ".gitignore").read_text()
        assert ".venv/" in content
        assert "__pycache__/" in content
        assert "test-results/" in content

    def test_write_gitignore_skips_existing(self, tmp_path):
        """_write_gitignore does not overwrite an existing .gitignore."""
        existing = tmp_path / ".gitignore"
        existing.write_text("custom content")
        _write_gitignore(tmp_path)
        assert existing.read_text() == "custom content"

    # ── DHF scaffold ─────────────────────────────────────────────────────────

    def test_scaffold_uses_local_templates(self):
        """_scaffold_dhf copies from bundled templates, not remote git."""
        src = inspect.getsource(_scaffold_dhf)
        assert "shutil.copytree" in src
        assert "_TEMPLATES_DIR" in src
        assert "git clone" not in src
        assert "subprocess.run" not in src

    def test_scaffold_does_not_emit_workflows(self, tmp_path):
        """_scaffold_dhf does not emit GitHub workflow files."""
        _scaffold_dhf(tmp_path)
        assert not (tmp_path / ".github" / "workflows").exists()

    def test_scaffold_creates_dhf_readme_inside_dhf(self, tmp_path):
        """_scaffold_dhf places README inside DHF/, not at repo root."""
        _scaffold_dhf(tmp_path)
        assert (tmp_path / "DHF" / "README.md").exists()

    def test_scaffold_creates_items_directories(self, tmp_path):
        """_scaffold_dhf creates DHF item directories for all doc types."""
        _scaffold_dhf(tmp_path)
        for d in ("00_uc", "01_crs", "02_sys", "03_srs", "04_swdd", "06_cr"):
            assert (tmp_path / "DHF" / "items" / d).is_dir(), f"Missing items/{d}"

    def test_scaffold_creates_prompt_files(self, tmp_path):
        """_scaffold_dhf copies prompt files for repo-local automation."""
        _scaffold_dhf(tmp_path)
        for prompt in ("cr-analyze.md", "cr-develop.md"):
            assert (tmp_path / ".github" / "prompts" / prompt).exists(), f"Missing {prompt}"

    # ── run_init guards ──────────────────────────────────────────────────────

    def test_run_init_no_github_calls(self):
        """run_init makes no GitHub API or gh CLI calls."""
        from medharness.workflows.init import run_init
        src = inspect.getsource(run_init)
        assert "_gh(" not in src
        assert "_repo_exists" not in src
        assert "_create_dhf_repo" not in src
        assert "_set_secret" not in src
        assert "llm_provider" not in src

    def test_run_init_no_prompts(self):
        """run_init contains no click.prompt calls — it is zero-prompt."""
        from medharness.workflows.init import run_init
        src = inspect.getsource(run_init)
        assert "click.prompt" not in src
