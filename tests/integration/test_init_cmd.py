"""Tests for medharness init command.

Tests the zero-prompt init command:
- engineering-control.yml generation (4 phases: cr-validation, dhf-validation,
  test-coverage, evidence-bundle)
- CLAUDE.md generation for single-repo layout
- cr-complete.yml single-repo generation
- DHF template placeholder substitution
- run_init guards and structure
"""

import inspect
from pathlib import Path

import pytest

from medharness.workflows.init import (
    _scaffold_dhf,
    _generate_engineering_control_yaml,
    _replace_placeholders,
    _write_claude_md,
    _write_engineering_control_yml,
    _write_cr_complete_yml,
    _write_gitignore,
)


class TestInitCmd:
    """init command — zero-prompt infrastructure onboarding command."""

    # ── engineering-control.yml ──────────────────────────────────────────────

    def test_engineering_control_yaml_has_cr_validation_phase(self):
        """Generated engineering-control.yml has a CR validation phase."""
        yaml = _generate_engineering_control_yaml()
        assert "cr-validation:" in yaml
        assert "name: CR Validation" in yaml
        assert "CR-[0-9]+" in yaml

    def test_engineering_control_yaml_has_dhf_validation_phase(self):
        """Generated engineering-control.yml has a DHF validation phase."""
        yaml = _generate_engineering_control_yaml()
        assert "dhf-validation:" in yaml
        assert "name: DHF Validation" in yaml
        assert "ci dhf-validate" in yaml
        assert "--dhf DHF" in yaml

    def test_engineering_control_yaml_has_test_coverage_gate(self):
        """Generated engineering-control.yml has a test-coverage gate job."""
        yaml = _generate_engineering_control_yaml()
        assert "test-coverage:" in yaml
        assert "name: Test Coverage Gate" in yaml
        assert "ci test-coverage" in yaml
        assert "--dhf DHF" in yaml
        assert "junitxml=test-results/" in yaml
        assert "upload-artifact@v4" in yaml
        assert "download-artifact@v4" in yaml

    def test_engineering_control_yaml_has_evidence_bundle(self):
        """Generated engineering-control.yml has an evidence-bundle post-merge job."""
        yaml = _generate_engineering_control_yaml()
        assert "evidence-bundle:" in yaml
        assert "name: Evidence Bundle" in yaml
        assert "ci evidence bundle" in yaml
        assert "refs/heads/main" in yaml

    def test_engineering_control_yaml_uses_pip_install(self):
        """Generated engineering-control.yml uses pip install medharness, not gh release download."""
        yaml = _generate_engineering_control_yaml()
        assert "pip install medharness" in yaml
        assert "gh release download" not in yaml
        assert "{github_org}" not in yaml
        assert "{dhf_repo_name}" not in yaml

    def test_engineering_control_yaml_no_cross_repo_checkout(self):
        """Generated engineering-control.yml has no DHF_REPO_TOKEN or cross-repo checkout."""
        yaml = _generate_engineering_control_yaml()
        assert "DHF_REPO_TOKEN" not in yaml
        assert "repository: " not in yaml

    def test_engineering_control_yaml_no_compliance_check(self):
        """Generated engineering-control.yml does not include a compliance-check job."""
        yaml = _generate_engineering_control_yaml()
        assert "compliance-check" not in yaml
        assert "ci compliance-check" not in yaml

    def test_engineering_control_yaml_no_llm(self):
        """Generated engineering-control.yml has no LLM API key references."""
        yaml = _generate_engineering_control_yaml()
        assert "GEMINI_API_KEY" not in yaml
        assert "COMPLIANTFLOW_OLLAMA_URL" not in yaml

    def test_engineering_control_yaml_no_standards(self):
        """Generated engineering-control.yml has no standards flags."""
        yaml = _generate_engineering_control_yaml()
        assert "--standard" not in yaml
        assert "--governance-dir" not in yaml

    def test_engineering_control_yaml_no_hardcoded_private_refs(self):
        """Generated engineering-control.yml has no hardcoded private repo references."""
        yaml = _generate_engineering_control_yaml()
        assert "itercharles" not in yaml

    def test_engineering_control_yaml_has_python_setup(self):
        """Generated engineering-control.yml has Python setup for MedHarness (not product code)."""
        yaml = _generate_engineering_control_yaml()
        assert "setup-python@v5" in yaml
        assert "python-version: '3.11'" in yaml
        assert "pip install medharness" in yaml

    def test_engineering_control_yaml_test_step_is_language_agnostic(self):
        """Generated engineering-control.yml test step has examples for multiple languages."""
        yaml = _generate_engineering_control_yaml()
        assert "pytest" in yaml
        assert "Jest" in yaml or "jest" in yaml
        assert "Maven" in yaml or "mvn" in yaml

    def test_engineering_control_yaml_no_legacy_gate_commands(self):
        """Generated engineering-control.yml does not contain deprecated gate commands."""
        yaml = _generate_engineering_control_yaml()
        assert "ci compliance-check" not in yaml
        assert "validate coverage" not in yaml
        assert "validate traceability" not in yaml

    def test_write_engineering_control_yml_creates_file(self, tmp_path):
        """_write_engineering_control_yml writes to the correct path."""
        result = _write_engineering_control_yml(tmp_path / "my-product")
        expected = tmp_path / "my-product" / ".github" / "workflows" / "engineering-control.yml"
        assert result == expected
        assert expected.exists()
        assert "ci test-coverage" in expected.read_text()

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

    # ── cr-complete.yml ──────────────────────────────────────────────────────

    def test_write_cr_complete_yml_creates_file(self, tmp_path):
        """_write_cr_complete_yml creates .github/workflows/cr-complete.yml."""
        result = _write_cr_complete_yml(tmp_path)
        expected = tmp_path / ".github" / "workflows" / "cr-complete.yml"
        assert result == expected
        assert expected.exists()

    def test_cr_complete_yml_single_repo(self, tmp_path):
        """cr-complete.yml uses single-repo pattern: no DHF_REPO_TOKEN, dhf-repo is dot."""
        _write_cr_complete_yml(tmp_path)
        content = (tmp_path / ".github" / "workflows" / "cr-complete.yml").read_text()
        assert "medharness cr workflow complete-from-github-pr" in content
        assert "--dhf-repo ." in content
        assert "GITHUB_TOKEN" in content
        assert "DHF_REPO_TOKEN" not in content
        assert "contents: write" in content

    def test_cr_complete_yml_no_legacy_commands(self, tmp_path):
        """cr-complete.yml uses only MedHarness facade commands."""
        _write_cr_complete_yml(tmp_path)
        content = (tmp_path / ".github" / "workflows" / "cr-complete.yml").read_text()
        assert "medharness cr workflow complete-from-github-pr" in content

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

    def test_scaffold_omits_dhf_ci_yml(self, tmp_path):
        """_scaffold_dhf does not emit ci.yml (merged into engineering-control.yml)."""
        _scaffold_dhf(tmp_path)
        assert not (tmp_path / ".github" / "workflows" / "ci.yml").exists()

    def test_scaffold_creates_dhf_readme_inside_dhf(self, tmp_path):
        """_scaffold_dhf places README inside DHF/, not at repo root."""
        _scaffold_dhf(tmp_path)
        assert (tmp_path / "DHF" / "README.md").exists()

    def test_scaffold_creates_items_directories(self, tmp_path):
        """_scaffold_dhf creates DHF item directories for all doc types."""
        _scaffold_dhf(tmp_path)
        for d in ("00_uc", "01_crs", "02_sys", "03_srs", "04_swdd", "06_cr"):
            assert (tmp_path / "DHF" / "items" / d).is_dir(), f"Missing items/{d}"

    def test_scaffold_creates_ai_workflows(self, tmp_path):
        """_scaffold_dhf creates the CR AI workflow files."""
        _scaffold_dhf(tmp_path)
        for wf in ("cr-analyze.yml", "cr-approve.yml", "cr-develop.yml", "cr-transition.yml"):
            assert (tmp_path / ".github" / "workflows" / wf).exists(), f"Missing {wf}"

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
