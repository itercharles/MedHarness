"""Tests for compliantflow init command (CR-054 / SYS-027).

Covers the pure-Python logic of init_cmd.py:
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

from compliantflow.init_cmd import (
    DHF_TEMPLATE_REPO,
    _fetch_dhf_template,
    _generate_engineering_control_yaml,
    _replace_placeholders,
    _write_claude_md,
    _write_engineering_control_yml,
    _write_cr_complete_yml,
)


class TestInitCmd:
    """SYS-027: compliantflow init — interactive infrastructure onboarding command."""

    def test_TC_SYS_027_003_engineering_control_yaml_with_dhf(self):
        """
        TC-SYS-027-003: Generated engineering-control.yml includes DHF checkout step when dhf_repo is provided.

        @test_id: TC-SYS-027-003
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo="acme/my-dhf")
        assert "repository: acme/my-dhf" in yaml
        assert "secrets.DHF_REPO_TOKEN" in yaml
        assert "--dhf dhf/DHF" in yaml
        assert "ci test-coverage" in yaml

    def test_TC_SYS_027_004_engineering_control_yaml_without_dhf(self):
        """
        TC-SYS-027-004: Generated engineering-control.yml omits DHF checkout when dhf_repo is None.

        @test_id: TC-SYS-027-004
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo=None)
        assert "DHF_REPO_TOKEN" not in yaml
        assert "--dhf DHF" in yaml
        assert "ci test-coverage" in yaml

    def test_TC_SYS_027_005_engineering_control_yaml_no_compliance_check(self):
        """
        TC-SYS-027-005: Generated engineering-control.yml does not include a compliance-check job.

        @test_id: TC-SYS-027-005
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "compliance-check" not in yaml
        assert "ci compliance-check" not in yaml
        assert "--standard" not in yaml
        assert "--governance-dir" not in yaml

    def test_TC_SYS_027_006_engineering_control_yaml_has_test_coverage_gate(self):
        """
        TC-SYS-027-006: Generated engineering-control.yml has a test-coverage gate job.

        @test_id: TC-SYS-027-006
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "test-coverage" in yaml
        assert "name: Test Coverage Gate" in yaml
        assert "ci test-coverage" in yaml

    def test_TC_SYS_027_007_engineering_control_yaml_no_llm(self):
        """
        TC-SYS-027-007: Generated engineering-control.yml has no LLM API key references.

        @test_id: TC-SYS-027-007
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo=None)
        assert "GEMINI_API_KEY" not in yaml
        assert "COMPLIANTFLOW_OLLAMA_URL" not in yaml

    def test_TC_SYS_027_008_engineering_control_yaml_no_standards(self):
        """
        TC-SYS-027-008: Generated engineering-control.yml has no standards flags or governance config.

        @test_id: TC-SYS-027-008
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "--standard" not in yaml
        assert "--governance-dir" not in yaml
        assert "GEMINI_API_KEY" not in yaml

    def test_TC_SYS_027_017_write_engineering_control_yml_creates_file(self, tmp_path):
        """
        TC-SYS-027-017: _write_engineering_control_yml writes engineering-control.yml to the correct path.

        @test_id: TC-SYS-027-017
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        result = _write_engineering_control_yml(product_dir, "org/dhf")
        expected = product_dir / ".github" / "workflows" / "engineering-control.yml"
        assert result == expected
        assert expected.exists()
        assert "ci test-coverage" in expected.read_text()

    def test_TC_SYS_027_018_run_init_no_github_calls(self):
        """
        TC-SYS-027-018: run_init makes no GitHub API or gh CLI calls — all execution
        is local file writes only. Also verifies no LLM provider prompting remains.

        @test_id: TC-SYS-027-018
        @links: SYS-027
        """
        import inspect
        from compliantflow.init_cmd import run_init
        src = inspect.getsource(run_init)
        assert "_gh(" not in src
        assert "_repo_exists" not in src
        assert "_create_dhf_repo" not in src
        assert "_set_secret" not in src
        assert "llm_provider" not in src
        assert 'click.Choice(["gemini"' not in src

    def test_TC_SYS_027_019_write_claude_md_creates_file(self, tmp_path):
        """
        TC-SYS-027-019: _write_claude_md creates CLAUDE.md in product_dir.

        @test_id: TC-SYS-027-019
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "My Device", "acme/my-device-dhf")
        assert (product_dir / "CLAUDE.md").exists()

    def test_TC_SYS_027_020_write_claude_md_contains_project_name(self, tmp_path):
        """
        TC-SYS-027-020: CLAUDE.md includes the project name.

        @test_id: TC-SYS-027-020
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "Cardiac Monitor", "acme/dhf")
        content = (product_dir / "CLAUDE.md").read_text()
        assert "Cardiac Monitor" in content

    def test_TC_SYS_027_021_write_claude_md_contains_dhf_repo(self, tmp_path):
        """
        TC-SYS-027-021: CLAUDE.md includes the DHF repo reference.

        @test_id: TC-SYS-027-021
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "Device", "acme/my-device-dhf")
        content = (product_dir / "CLAUDE.md").read_text()
        assert "acme/my-device-dhf" in content

    def test_TC_SYS_027_022_write_claude_md_fallback_when_no_dhf(self, tmp_path):
        """
        TC-SYS-027-022: CLAUDE.md uses fallback DHF repo when dhf_repo is None.

        @test_id: TC-SYS-027-022
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "Device", None)
        content = (product_dir / "CLAUDE.md").read_text()
        assert "your-org/your-product-dhf" in content

    def test_TC_SYS_027_023_write_claude_md_mentions_cr_workflow(self, tmp_path):
        """
        TC-SYS-027-023: CLAUDE.md references CR ID in PR title and testing conventions.

        @test_id: TC-SYS-027-023
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _write_claude_md(product_dir, "Device", "acme/dhf")
        content = (product_dir / "CLAUDE.md").read_text()
        assert "CR ID" in content
        assert "ci test-coverage" in content

    def test_TC_SYS_027_026_replace_placeholders_substitutes_project_name(self, tmp_path):
        """
        TC-SYS-027-026: _replace_placeholders substitutes {{project_name}} in DHF template files.

        @test_id: TC-SYS-027-026
        @links: SYS-027
        """
        dhf_dir = tmp_path / "my-dhf"
        (dhf_dir / "DHF").mkdir(parents=True)
        readme = dhf_dir / "README.md"
        readme.write_text("# {{project_name}} DHF")
        _replace_placeholders(dhf_dir, "Test Device", "acme/test-device")
        assert "Test Device" in readme.read_text()
        assert "{{project_name}}" not in readme.read_text()

    def test_TC_SYS_027_027_write_cr_complete_yml_creates_file(self, tmp_path):
        """
        TC-SYS-027-027: _write_cr_complete_yml creates .github/workflows/cr-complete.yml.

        @test_id: TC-SYS-027-027
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        result = _write_cr_complete_yml(product_dir, "acme/my-device-dhf")
        expected = product_dir / ".github" / "workflows" / "cr-complete.yml"
        assert result == expected
        assert expected.exists()

    def test_TC_SYS_027_028_cr_complete_yml_contains_dhf_repo_reference(self, tmp_path):
        """
        TC-SYS-027-028: cr-complete.yml contains the DHF repo reference.

        @test_id: TC-SYS-027-028
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _write_cr_complete_yml(product_dir, "acme/my-device-dhf")
        content = (product_dir / ".github" / "workflows" / "cr-complete.yml").read_text()
        assert "repository: acme/my-device-dhf" in content
        assert "compliantflow cr workflow complete-from-github-pr" in content
        assert "--dhf-repo dhf" in content

    def test_TC_SYS_027_032_engineering_control_yaml_has_required_phases(self):
        """
        TC-SYS-027-032: Generated engineering-control.yml contains the test-coverage job
        with JUnit artifact contract.

        @test_id: TC-SYS-027-032
        @links: SYS-027
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

    def test_TC_SYS_027_033_engineering_control_yaml_no_legacy_gate_commands(self):
        """
        TC-SYS-027-033: Generated engineering-control.yml does not contain
        compliance-check or deprecated gate commands.

        @test_id: TC-SYS-027-033
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "ci compliance-check" not in yaml
        assert "compliance-check" not in yaml
        assert "validate coverage" not in yaml
        assert "validate traceability" not in yaml
        assert "--standard" not in yaml

    def test_TC_SYS_027_034_engineering_control_yaml_no_hardcoded_private_refs(self):
        """
        TC-SYS-027-034: Generated engineering-control.yml does not contain hardcoded
        private repo references (itercharles, etc.).

        @test_id: TC-SYS-027-034
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "itercharles" not in yaml

    def test_TC_SYS_027_035_engineering_control_yaml_has_python_setup(self):
        """
        TC-SYS-027-035: Generated engineering-control.yml includes Python setup and pip
        install steps for CompliantFlow.

        @test_id: TC-SYS-027-035
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo="org/dhf")
        assert "setup-python@v5" in yaml
        assert "python-version: '3.11'" in yaml
        assert "pip install" in yaml

    def test_TC_SYS_027_036_engineering_control_yaml_no_standards_or_llm(self):
        """
        TC-SYS-027-036: Generated engineering-control.yml has no standards flags
        and no LLM API key references.

        @test_id: TC-SYS-027-036
        @links: SYS-027
        """
        yaml = _generate_engineering_control_yaml(dhf_repo=None)
        assert "--standard" not in yaml
        assert "GEMINI_API_KEY" not in yaml
        assert "COMPLIANTFLOW_OLLAMA_URL" not in yaml

    def test_TC_SYS_027_037_cr_complete_yml_no_legacy_commands(self, tmp_path):
        """
        TC-SYS-027-037: Generated cr-complete.yml uses only CompliantFlow facade
        commands, not direct dhf_util item transition calls.

        @test_id: TC-SYS-027-037
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _write_cr_complete_yml(product_dir, "acme/my-device-dhf")
        content = (product_dir / ".github" / "workflows" / "cr-complete.yml").read_text()
        assert "compliantflow cr workflow complete-from-github-pr" in content

    def test_TC_SYS_027_038_replace_placeholders_product_repo(self, tmp_path):
        """
        TC-SYS-027-038: _replace_placeholders substitutes {{product_repo}} in DHF template.

        @test_id: TC-SYS-027-038
        @links: SYS-027
        """
        dhf_dir = tmp_path / "my-dhf"
        (dhf_dir / ".github" / "workflows").mkdir(parents=True)
        wf = dhf_dir / ".github" / "workflows" / "cr-develop.yml"
        wf.write_text("gh repo clone {{product_repo}}")
        _replace_placeholders(dhf_dir, "Device", "acme/my-device")
        assert "acme/my-device" in wf.read_text()
        assert "{{product_repo}}" not in wf.read_text()

    def test_TC_SYS_027_039_init_no_hardcoded_template_refs(self):
        """
        TC-SYS-027-039: init_cmd.py does not reference a local data/ template directory.

        @test_id: TC-SYS-027-039
        @links: SYS-027
        """
        import inspect
        from compliantflow.init_cmd import _fetch_dhf_template
        src = inspect.getsource(_fetch_dhf_template)
        assert "TEMPLATE_DIR" not in src
        assert "shutil.copytree" in src  # copies from fetched clone
        assert "DHF_TEMPLATE_REPO" in src  # uses the URL constant
        assert "data/" not in src  # no local embedded data dir
        assert "subprocess.run" in src  # uses git clone, not local copy

    def test_TC_SYS_027_040_replace_placeholders_handles_missing_dir(self, tmp_path):
        """
        TC-SYS-027-040: _replace_placeholders handles empty directories gracefully.

        @test_id: TC-SYS-027-040
        @links: SYS-027
        """
        dhf_dir = tmp_path / "my-dhf"
        dhf_dir.mkdir()
        # Should not raise
        _replace_placeholders(dhf_dir, "Device", "acme/test-device")
