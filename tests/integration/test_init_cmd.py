"""Tests for medharness init command ().

Tests the init command:
- engineering-control.yml generation for various DHF configurations
- CLAUDE.md generation
- cr-complete.yml generation
- DHF template placeholder substitution
- run_init validation guards
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch
import tempfile

import click
import pytest

from medharness.workflows.init import (
    _scaffold_dhf,
    _generate_engineering_control_yaml,
    _replace_placeholders,
    _write_claude_md,
    _write_engineering_control_yml,
    _write_cr_complete_yml,
)


class TestInitCmd:
    """init command — interactive infrastructure onboarding command."""

    def test_engineering_control_yaml_with_dhf(self):
        """
        Generated engineering-control.yml includes DHF checkout step when dhf_repo is provided.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo="acme/my-dhf")
        assert "repository: acme/my-dhf" in yaml
        assert "secrets.DHF_REPO_TOKEN" in yaml
        assert "--dhf dhf/DHF" in yaml
        assert "ci test-coverage" in yaml

    def test_engineering_control_yaml_without_dhf(self):
        """
        Generated engineering-control.yml omits DHF checkout when dhf_repo is None.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo=None)
        assert "DHF_REPO_TOKEN" not in yaml
        assert "--dhf DHF" in yaml
        assert "ci test-coverage" in yaml

    def test_engineering_control_yaml_no_compliance_check(self):
        """
        Generated engineering-control.yml does not include a compliance-check job.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "compliance-check" not in yaml
        assert "ci compliance-check" not in yaml
        assert "--standard" not in yaml
        assert "--governance-dir" not in yaml

    def test_engineering_control_yaml_has_test_coverage_gate(self):
        """
        Generated engineering-control.yml has a test-coverage gate job.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "test-coverage" in yaml
        assert "name: Test Coverage Gate" in yaml
        assert "ci test-coverage" in yaml

    def test_engineering_control_yaml_no_llm(self):
        """
        Generated engineering-control.yml has no LLM API key references.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo=None)
        assert "GEMINI_API_KEY" not in yaml
        assert "COMPLIANTFLOW_OLLAMA_URL" not in yaml

    def test_engineering_control_yaml_no_standards(self):
        """
        Generated engineering-control.yml has no standards flags or governance config.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "--standard" not in yaml
        assert "--governance-dir" not in yaml
        assert "GEMINI_API_KEY" not in yaml

    def test_write_engineering_control_yml_creates_file(self, tmp_path):
        """
        _write_engineering_control_yml writes engineering-control.yml to the correct path.

        """
        product_dir = tmp_path / "my-product"
        result = _write_engineering_control_yml(product_dir, "org/dhf")
        expected = product_dir / ".github" / "workflows" / "engineering-control.yml"
        assert result == expected
        assert expected.exists()
        assert "ci test-coverage" in expected.read_text()

    def test_run_init_no_github_calls(self):
        """
        run_init makes no GitHub API or gh CLI calls — all execution
        is local file writes only. Also verifies no LLM provider prompting remains.

        """
        import inspect
        from medharness.workflows.init import run_init
        src = inspect.getsource(run_init)
        assert "_gh(" not in src
        assert "_repo_exists" not in src
        assert "_create_dhf_repo" not in src
        assert "_set_secret" not in src
        assert "llm_provider" not in src
        assert 'click.Choice(["gemini"' not in src

    def test_write_claude_md_creates_file(self, tmp_path):
        """
        _write_claude_md creates CLAUDE.md in product_dir.

        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "My Device", "acme/my-device-dhf")
        assert (product_dir / "CLAUDE.md").exists()

    def test_write_claude_md_contains_project_name(self, tmp_path):
        """
        CLAUDE.md includes the project name.

        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "Cardiac Monitor", "acme/dhf")
        content = (product_dir / "CLAUDE.md").read_text()
        assert "Cardiac Monitor" in content

    def test_write_claude_md_contains_dhf_repo(self, tmp_path):
        """
        CLAUDE.md includes the DHF repo reference.

        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "Device", "acme/my-device-dhf")
        content = (product_dir / "CLAUDE.md").read_text()
        assert "acme/my-device-dhf" in content

    def test_write_claude_md_fallback_when_no_dhf(self, tmp_path):
        """
        CLAUDE.md uses fallback DHF repo when dhf_repo is None.

        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "Device", None)
        content = (product_dir / "CLAUDE.md").read_text()
        assert "your-org/your-product-dhf" in content

    def test_write_claude_md_mentions_cr_workflow(self, tmp_path):
        """
        CLAUDE.md references CR ID in PR title and testing conventions.

        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "Device", "acme/dhf")
        content = (product_dir / "CLAUDE.md").read_text()
        assert "CR ID" in content
        assert "ci test-coverage" in content

    def test_replace_placeholders_substitutes_project_name(self, tmp_path):
        """
        _replace_placeholders substitutes {{project_name}} in DHF template files.

        """
        dhf_dir = tmp_path / "my-dhf"
        (dhf_dir / "DHF").mkdir(parents=True)
        readme = dhf_dir / "README.md"
        readme.write_text("# {{project_name}} DHF")
        _replace_placeholders(dhf_dir, "Test Device", "acme/test-device")
        assert "Test Device" in readme.read_text()
        assert "{{project_name}}" not in readme.read_text()

    def test_write_cr_complete_yml_creates_file(self, tmp_path):
        """
        _write_cr_complete_yml creates .github/workflows/cr-complete.yml.

        """
        product_dir = tmp_path / "my-product"
        result = _write_cr_complete_yml(product_dir, "acme/my-device-dhf")
        expected = product_dir / ".github" / "workflows" / "cr-complete.yml"
        assert result == expected
        assert expected.exists()

    def test_cr_complete_yml_contains_dhf_repo_reference(self, tmp_path):
        """
        cr-complete.yml contains the DHF repo reference.

        """
        product_dir = tmp_path / "my-product"
        _write_cr_complete_yml(product_dir, "acme/my-device-dhf")
        content = (product_dir / ".github" / "workflows" / "cr-complete.yml").read_text()
        assert "repository: acme/my-device-dhf" in content
        assert "medharness cr workflow complete-from-github-pr" in content
        assert "--dhf-repo dhf" in content

    def test_engineering_control_yaml_has_required_phases(self):
        """
        Generated engineering-control.yml contains the test-coverage job
        with JUnit artifact contract.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "test-coverage" in yaml
        assert "name: Test Coverage Gate" in yaml
        # JUnit artifact production
        assert "junitxml=test-results/" in yaml
        assert "mkdir -p test-results/" in yaml
        assert "upload-artifact@v4" in yaml
        # JUnit artifact consumption
        assert "download-artifact@v4" in yaml
        # Correct CLI commands
        assert "ci test-coverage" in yaml
        assert "--junit-dir test-results" in yaml
        # Evidence bundle on main
        assert "ci evidence bundle" in yaml
        assert "evidence-bundle" in yaml

    def test_engineering_control_yaml_no_legacy_gate_commands(self):
        """
        Generated engineering-control.yml does not contain
        compliance-check or deprecated gate commands.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "ci compliance-check" not in yaml
        assert "compliance-check" not in yaml
        assert "validate coverage" not in yaml
        assert "validate traceability" not in yaml
        assert "--standard" not in yaml

    def test_engineering_control_yaml_no_hardcoded_private_refs(self):
        """
        Generated engineering-control.yml does not contain hardcoded
        private repo references (itercharles, etc.).

        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "itercharles" not in yaml

    def test_engineering_control_yaml_has_python_setup(self):
        """
        Generated engineering-control.yml includes Python setup and pip
        install steps for MedHarness.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "setup-python@v5" in yaml
        assert "python-version: '3.11'" in yaml
        assert "pip install" in yaml

    def test_engineering_control_yaml_no_standards_or_llm(self):
        """
        Generated engineering-control.yml has no standards flags
        and no LLM API key references.

        """
        yaml = _generate_engineering_control_yaml(dhf_repo=None)
        assert "--standard" not in yaml
        assert "GEMINI_API_KEY" not in yaml
        assert "COMPLIANTFLOW_OLLAMA_URL" not in yaml

    def test_cr_complete_yml_no_legacy_commands(self, tmp_path):
        """
        Generated cr-complete.yml uses only MedHarness facade
        commands, not direct dhfkit item transition calls.

        """
        product_dir = tmp_path / "my-product"
        _write_cr_complete_yml(product_dir, "acme/my-device-dhf")
        content = (product_dir / ".github" / "workflows" / "cr-complete.yml").read_text()
        assert "medharness cr workflow complete-from-github-pr" in content

    def test_replace_placeholders_product_repo(self, tmp_path):
        """
        _replace_placeholders substitutes {{product_repo}} in DHF template.

        """
        dhf_dir = tmp_path / "my-dhf"
        (dhf_dir / ".github" / "workflows").mkdir(parents=True)
        wf = dhf_dir / ".github" / "workflows" / "cr-develop.yml"
        wf.write_text("gh repo clone {{product_repo}}")
        _replace_placeholders(dhf_dir, "Device", "acme/my-device")
        assert "acme/my-device" in wf.read_text()
        assert "{{product_repo}}" not in wf.read_text()

    def test_scaffold_uses_local_templates(self):
        """
        init_cmd.py does not reference a local data/ template directory.

        """
        import inspect
        from medharness.workflows.init import _scaffold_dhf
        src = inspect.getsource(_scaffold_dhf)
        assert "TEMPLATE_DIR" not in src
        assert "shutil.copytree" in src  # copies from bundled templates
        assert "_TEMPLATES_DIR" in src   # uses local templates, not remote fetch
        assert "git clone" not in src    # no remote git clone
        assert "subprocess.run" not in src  # no subprocess for clone

    def test_replace_placeholders_handles_missing_dir(self, tmp_path):
        """
        _replace_placeholders handles empty directories gracefully.

        """
        dhf_dir = tmp_path / "my-dhf"
        dhf_dir.mkdir()
        # Should not raise
        _replace_placeholders(dhf_dir, "Device", "acme/test-device")

    def test_write_skills_creates_files(self, tmp_path):
        """
        _write_skills creates .claude/skills/ with substituted placeholders.

        """
        from medharness.workflows.init import _write_skills
        product_dir = tmp_path / "product"
        written = _write_skills(product_dir, "Test Device", "acme/test-device-dhf")
        assert len(written) >= 3
        for skill in ["pre-analyze", "cr-implement", "traceability-check"]:
            skill_md = product_dir / ".claude" / "skills" / skill / "SKILL.md"
            assert skill_md.exists(), f"Missing {skill}"
            content = skill_md.read_text()
            assert "Test Device" in content, f"{{project_name}} not substituted in {skill}"
            assert "{{project_name}}" not in content, f"{{project_name}} left in {skill}"
            assert "{{product_repo}}" not in content, f"{{product_repo}} left in {skill}"
