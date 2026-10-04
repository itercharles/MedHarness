"""Tests for medharness init command.

Tests the zero-prompt init command:
- AGENTS.md and CLAUDE.md for coding agents
- DHF template placeholder substitution
- prompt scaffolding
- run_init guards and structure
"""

import inspect


from medharness.scaffold import (
    scaffold_dhf,
    replace_placeholders,
    _write_agent_files,
    _write_gitignore,
)


class TestInitCmd:
    """init command — zero-prompt infrastructure onboarding command."""

    # ── AGENTS.md and CLAUDE.md ─────────────────────────────────────────────

    def test_a_new_project_gets_agents_md_and_a_claude_md_that_imports_it(self, tmp_path):
        _write_agent_files(tmp_path, "Cardiac Monitor")
        agents = (tmp_path / "AGENTS.md").read_text()
        for section in ("## Product", "## Architecture", "## Scope", "## Design History File"):
            assert section in agents, section
        assert "Cardiac Monitor" in agents
        assert (tmp_path / "CLAUDE.md").read_text() == "@AGENTS.md\n"

    def test_the_instructions_name_the_high_level_steps(self, tmp_path):
        _write_agent_files(tmp_path, "Device")
        agents = (tmp_path / "AGENTS.md").read_text()
        for step in ("build plan --cr CR-NNN --prompt", "build code --cr CR-NNN --prompt",
                     "verify completion --cr CR-NNN", "verify changes --cr CR-NNN"):
            assert step in agents, step

    def test_the_instructions_route_every_dhf_read_and_write_through_item(self, tmp_path):
        """Without this an agent answering a question outside a CR edits the YAML."""
        _write_agent_files(tmp_path, "Device")
        agents = (tmp_path / "AGENTS.md").read_text()
        for text in ("item list --type", "item get", "item create|update|transition",
                     "never by editing the\n  files under `DHF/`"):
            assert text in agents, text

    def test_existing_files_are_added_to_not_replaced(self, tmp_path):
        """init used to overwrite a repository's own CLAUDE.md."""
        (tmp_path / "AGENTS.md").write_text("# Ours\n\nKeep this.\n")
        (tmp_path / "CLAUDE.md").write_text("# Ours too\n")
        _write_agent_files(tmp_path, "Device")
        _write_agent_files(tmp_path, "Device")
        agents = (tmp_path / "AGENTS.md").read_text()
        claude = (tmp_path / "CLAUDE.md").read_text()
        assert agents.startswith("# Ours\n\nKeep this.") and agents.count("## Design History File") == 1
        assert claude.startswith("# Ours too") and claude.count("@AGENTS.md") == 1

    # ── placeholder substitution ─────────────────────────────────────────────

    def test_replace_placeholders_substitutes_project_name(self, tmp_path):
        """replace_placeholders substitutes {{project_name}} in DHF template files."""
        (tmp_path / "DHF").mkdir(parents=True)
        readme = tmp_path / "README.md"
        readme.write_text("# {{project_name}} DHF")
        replace_placeholders(tmp_path, "Test Device")
        assert "Test Device" in readme.read_text()
        assert "{{project_name}}" not in readme.read_text()

    def test_replace_placeholders_substitutes_medharness_version(self, tmp_path):
        """replace_placeholders substitutes {{medharness_version}}."""
        (tmp_path / "DHF").mkdir(parents=True)
        wf = tmp_path / "workflow.yml"
        wf.write_text("pip install medharness=={{medharness_version}}")
        replace_placeholders(tmp_path, "Device")
        assert "{{medharness_version}}" not in wf.read_text()

    def test_replace_placeholders_handles_missing_dir(self, tmp_path):
        """replace_placeholders handles directories with no substitutable files gracefully."""
        (tmp_path / "DHF").mkdir()
        untouched = tmp_path / "DHF" / "keep.txt"
        untouched.write_text("no placeholders here")

        replace_placeholders(tmp_path, "Device")

        # A no-op would pass on "does not raise" alone; what matters is that it
        # left a file with nothing to substitute exactly as it was.
        assert untouched.read_text() == "no placeholders here"

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
        """scaffold_dhf copies from bundled templates, not remote git."""
        src = inspect.getsource(scaffold_dhf)
        assert "shutil.copytree" in src
        assert "_TEMPLATES_DIR" in src
        assert "git clone" not in src
        assert "subprocess.run" not in src

    def test_scaffold_writes_nothing_that_nothing_reads(self, tmp_path):
        """`.github/prompts/*.md` and `AI-harness/context.md` were scaffolded and
        kept current by `upgrade`, and no code or prompt read them."""
        scaffold_dhf(tmp_path)
        assert not (tmp_path / ".github").exists()
        assert not (tmp_path / "AI-harness").exists()

    def test_scaffold_omits_github_workflow(self, tmp_path):
        """CI is not in the release payload, so init must not claim to create it."""
        scaffold_dhf(tmp_path)
        assert not (tmp_path / ".github" / "workflows").exists()

    def test_scaffold_creates_dhf_readme_inside_dhf(self, tmp_path):
        """scaffold_dhf places README inside DHF/, not at repo root."""
        scaffold_dhf(tmp_path)
        assert (tmp_path / "DHF" / "README.md").exists()

    def test_scaffold_creates_items_directories(self, tmp_path):
        """scaffold_dhf creates DHF item directories for all doc types."""
        scaffold_dhf(tmp_path)
        for d in ("00_uc", "01_crs", "02_sys", "03_srs", "04_modules", "05_swdd", "07_cr"):
            assert (tmp_path / "DHF" / "items" / d).is_dir(), f"Missing items/{d}"

    # ── run_init guards ──────────────────────────────────────────────────────

    def test_run_init_no_github_calls(self):
        """run_init makes no GitHub API or gh CLI calls."""
        from medharness.scaffold import run_init
        src = inspect.getsource(run_init)
        assert "gh(" not in src
        assert "_repo_exists" not in src
        assert "_create_dhf_repo" not in src
        assert "_set_secret" not in src
        assert "llm_provider" not in src

    def test_run_init_no_prompts(self):
        """run_init contains no click.prompt calls — it is zero-prompt."""
        from medharness.scaffold import run_init
        src = inspect.getsource(run_init)
        assert "click.prompt" not in src


def test_the_ai_workflow_page_shows_the_section_init_writes():
    """A project that predates AGENTS.md copies it from there."""
    from pathlib import Path

    from medharness.scaffold import DHF_INSTRUCTIONS

    adopting = (Path(__file__).resolve().parents[2] / "docs" / "ai-workflow.md").read_text()
    assert DHF_INSTRUCTIONS in adopting
