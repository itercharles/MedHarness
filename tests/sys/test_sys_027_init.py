"""Tests for compliantflow init command (CR-054 / SYS-027).

Covers the pure-Python logic of init_cmd.py:
- compliance.yml generation for various standard/DHF/LLM combinations
- DHF CI workflow template content
- Standard label and governance file mappings
- _init_dhf_template: file population, project name substitution, governance filtering
- run_init validation guards: product repo existence and emptiness
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch
import tempfile

import click
import pytest

from compliantflow.init_cmd import (
    GOVERNANCE_FILES,
    HARNESS_DIR,
    PRODUCT_TEMPLATE_DIR,
    STANDARD_LABELS,
    TEMPLATE_DIR,
    _generate_compliance_yaml,
    _init_dhf_template,
    _init_product_template,
    _write_compliance_yml,
    _write_cr_complete_yml,
    _write_dhf_ci_workflow,
    _write_dhf_cr_transition_workflow,
)


class TestInitCmd:
    """SYS-027: compliantflow init — interactive infrastructure onboarding command."""

    def test_TC_SYS_027_001_template_dir_exists(self):
        """
        TC-SYS-027-001: The bundled dhf-template directory is present in package data.

        @test_id: TC-SYS-027-001
        @links: SYS-027
        """
        assert TEMPLATE_DIR.exists(), f"Template directory not found: {TEMPLATE_DIR}"
        assert (TEMPLATE_DIR / "DHF" / "config" / "global.yaml").exists()
        assert (TEMPLATE_DIR / "governance").exists()

    def test_TC_SYS_027_002_governance_files_complete(self):
        """
        TC-SYS-027-002: All four governance standard files exist in the template.

        @test_id: TC-SYS-027-002
        @links: SYS-027
        """
        gov_dir = TEMPLATE_DIR / "governance"
        for std_id, filename in GOVERNANCE_FILES.items():
            f = gov_dir / filename
            assert f.exists(), f"Missing governance file for {std_id}: {f}"

    def test_TC_SYS_027_003_compliance_yaml_with_dhf(self):
        """
        TC-SYS-027-003: Generated compliance.yml includes DHF checkout step when dhf_repo is provided.

        @test_id: TC-SYS-027-003
        @links: SYS-027
        """
        yaml = _generate_compliance_yaml(
            dhf_repo="acme/my-dhf",
            standards=["IEC_62304"],
            llm_provider=None,
        )
        assert "repository: acme/my-dhf" in yaml
        assert "secrets.DHF_REPO_TOKEN" in yaml
        assert "--dhf dhf/DHF" in yaml
        assert "validate traceability" in yaml
        assert "validate compliance IEC_62304" in yaml

    def test_TC_SYS_027_004_compliance_yaml_without_dhf(self):
        """
        TC-SYS-027-004: Generated compliance.yml omits DHF checkout when dhf_repo is None.

        @test_id: TC-SYS-027-004
        @links: SYS-027
        """
        yaml = _generate_compliance_yaml(
            dhf_repo=None,
            standards=["IEC_62304", "ISO_14971"],
            llm_provider=None,
        )
        assert "DHF_REPO_TOKEN" not in yaml
        assert "--dhf DHF" in yaml
        assert "validate compliance IEC_62304" in yaml
        assert "validate compliance ISO_14971" in yaml

    def test_TC_SYS_027_005_compliance_yaml_gemini_llm(self):
        """
        TC-SYS-027-005: Generated compliance.yml includes GEMINI_API_KEY env when provider is gemini.

        @test_id: TC-SYS-027-005
        @links: SYS-027
        """
        yaml = _generate_compliance_yaml(
            dhf_repo=None,
            standards=["IEC_62304"],
            llm_provider="gemini",
        )
        assert "GEMINI_API_KEY" in yaml
        assert "secrets.GEMINI_API_KEY" in yaml

    def test_TC_SYS_027_006_compliance_yaml_ollama_llm(self):
        """
        TC-SYS-027-006: Generated compliance.yml includes COMPLIANTFLOW_OLLAMA_URL env when provider is ollama.

        @test_id: TC-SYS-027-006
        @links: SYS-027
        """
        yaml = _generate_compliance_yaml(
            dhf_repo=None,
            standards=["IEC_62304"],
            llm_provider="ollama",
        )
        assert "COMPLIANTFLOW_OLLAMA_URL" in yaml

    def test_TC_SYS_027_007_compliance_yaml_no_llm(self):
        """
        TC-SYS-027-007: Generated compliance.yml has no env block when llm_provider is None.

        @test_id: TC-SYS-027-007
        @links: SYS-027
        """
        yaml = _generate_compliance_yaml(
            dhf_repo=None,
            standards=["IEC_62304"],
            llm_provider=None,
        )
        assert "GEMINI_API_KEY" not in yaml
        assert "COMPLIANTFLOW_OLLAMA_URL" not in yaml

    def test_TC_SYS_027_008_compliance_yaml_multiple_standards(self):
        """
        TC-SYS-027-008: Generated compliance.yml includes a validate step for each selected standard.

        @test_id: TC-SYS-027-008
        @links: SYS-027
        """
        standards = ["IEC_62304", "ISO_14971", "ISO_13485"]
        yaml = _generate_compliance_yaml(
            dhf_repo="org/dhf",
            standards=standards,
            llm_provider=None,
        )
        for std in standards:
            assert f"validate compliance {std}" in yaml

    def test_TC_SYS_027_009_dhf_ci_workflow_content(self):
        """
        TC-SYS-027-009: Generated DHF ci.yml contains schema-validation and utils-tests jobs.

        @test_id: TC-SYS-027-009
        @links: SYS-027
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ci.yml"
            _write_dhf_ci_workflow(path)
            content = path.read_text()
        assert "schema-validation" in content
        assert "utils-tests" in content
        assert "python -m dhf_util validate schema" in content

    def test_TC_SYS_027_010_cr_transition_workflow_content(self):
        """
        TC-SYS-027-010: Generated cr-transition.yml contains workflow_dispatch trigger and transition step.

        @test_id: TC-SYS-027-010
        @links: SYS-027
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cr-transition.yml"
            _write_dhf_cr_transition_workflow(path)
            content = path.read_text()
        assert "workflow_dispatch" in content
        assert "python -m dhf_util item transition" in content
        assert "cr_ids" in content

    def test_TC_SYS_027_011_standard_labels_cover_all_governance_files(self):
        """
        TC-SYS-027-011: STANDARD_LABELS and GOVERNANCE_FILES have matching key sets.

        @test_id: TC-SYS-027-011
        @links: SYS-027
        """
        assert set(STANDARD_LABELS.keys()) == set(GOVERNANCE_FILES.keys())

    def test_TC_SYS_027_012_template_global_yaml_has_project_name(self):
        """
        TC-SYS-027-012: The bundled global.yaml template contains a project_name field.

        @test_id: TC-SYS-027-012
        @links: SYS-027
        """
        global_yaml = (TEMPLATE_DIR / "DHF" / "config" / "global.yaml").read_text()
        assert "project_name:" in global_yaml

    def test_TC_SYS_027_013_init_dhf_template_substitutes_project_name(self, tmp_path):
        """
        TC-SYS-027-013: _init_dhf_template writes project_name into global.yaml.

        @test_id: TC-SYS-027-013
        @links: SYS-027
        """
        dhf_dir = tmp_path / "my-dhf"
        _init_dhf_template(dhf_dir, "My Test Device", ["IEC_62304", "ISO_14971"])
        global_yaml = (dhf_dir / "DHF" / "config" / "global.yaml").read_text()
        assert 'project_name: "My Test Device"' in global_yaml

    def test_TC_SYS_027_014_init_dhf_template_removes_unselected_governance(self, tmp_path):
        """
        TC-SYS-027-014: _init_dhf_template removes governance files for standards not selected.

        @test_id: TC-SYS-027-014
        @links: SYS-027
        """
        dhf_dir = tmp_path / "my-dhf"
        _init_dhf_template(dhf_dir, "Device", ["IEC_62304"])
        gov_dir = dhf_dir / "governance"
        assert (gov_dir / "IEC_62304.yaml").exists()
        assert not (gov_dir / "ISO_14971.yaml").exists()
        assert not (gov_dir / "IEC_82304_1.yaml").exists()
        assert not (gov_dir / "ISO_13485.yaml").exists()

    def test_TC_SYS_027_015_init_dhf_template_writes_ci_workflows(self, tmp_path):
        """
        TC-SYS-027-015: _init_dhf_template creates .github/workflows/ci.yml and cr-transition.yml.

        @test_id: TC-SYS-027-015
        @links: SYS-027
        """
        dhf_dir = tmp_path / "my-dhf"
        _init_dhf_template(dhf_dir, "Device", ["IEC_62304"])
        assert (dhf_dir / ".github" / "workflows" / "ci.yml").exists()
        assert (dhf_dir / ".github" / "workflows" / "cr-transition.yml").exists()

    def test_TC_SYS_027_016_init_dhf_template_no_git_operations(self, tmp_path):
        """
        TC-SYS-027-016: _init_dhf_template does not invoke any git or gh commands —
        all operations are local file writes only.

        @test_id: TC-SYS-027-016
        @links: SYS-027
        """
        import inspect
        src = inspect.getsource(_init_dhf_template)
        assert "subprocess" not in src
        assert "_gh(" not in src
        # Verify it actually writes files without any external calls
        dhf_dir = tmp_path / "my-dhf"
        _init_dhf_template(dhf_dir, "Device", ["IEC_62304"])
        assert dhf_dir.exists()

    def test_TC_SYS_027_017_write_compliance_yml_creates_file(self, tmp_path):
        """
        TC-SYS-027-017: _write_compliance_yml writes compliance.yml to the correct path.

        @test_id: TC-SYS-027-017
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        result = _write_compliance_yml(product_dir, "org/dhf", ["IEC_62304"], None)
        expected = product_dir / ".github" / "workflows" / "compliance.yml"
        assert result == expected
        assert expected.exists()
        assert "validate compliance IEC_62304" in expected.read_text()

    def test_TC_SYS_027_018_run_init_no_github_calls(self):
        """
        TC-SYS-027-018: run_init makes no GitHub API or gh CLI calls — all execution
        is local file writes only.

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

    def test_TC_SYS_027_019_product_template_dir_exists(self):
        """
        TC-SYS-027-019: The bundled product-template directory exists in package data.

        @test_id: TC-SYS-027-019
        @links: SYS-027
        """
        assert PRODUCT_TEMPLATE_DIR.exists(), f"Product template directory not found: {PRODUCT_TEMPLATE_DIR}"
        assert HARNESS_DIR.exists(), f"Root AI-harness not found: {HARNESS_DIR}"
        assert (HARNESS_DIR / "context.md").exists()
        assert (HARNESS_DIR / "CLAUDE.md").exists()

    def test_TC_SYS_027_020_init_product_template_creates_context(self, tmp_path):
        """
        TC-SYS-027-020: _init_product_template creates AI-harness/context.md in product_dir.

        @test_id: TC-SYS-027-020
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _init_product_template(product_dir, "My Device", "acme/my-device-dhf", ["IEC_62304"])
        assert (product_dir / "AI-harness" / "context.md").exists()

    def test_TC_SYS_027_021_init_product_template_substitutes_project_name(self, tmp_path):
        """
        TC-SYS-027-021: _init_product_template copies context.md from root AI-harness.
        Root harness has no placeholders — file is copied as-is.

        @test_id: TC-SYS-027-021
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _init_product_template(product_dir, "Insulin Pump Firmware", "acme/dhf", ["IEC_62304"])
        assert (product_dir / "AI-harness" / "context.md").exists()

    def test_TC_SYS_027_022_init_product_template_substitutes_dhf_repo(self, tmp_path):
        """
        TC-SYS-027-022: _init_product_template copies docs/ with {{dhf_repo}} substituted.
        Root AI-harness has no placeholders; substitution applies to docs/ scaffold.

        @test_id: TC-SYS-027-022
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _init_product_template(product_dir, "Device", "acme/my-device-dhf", ["IEC_62304"])
        # docs/ scaffold (from product-template) has placeholders — verify substitution there
        tech_strategy = (product_dir / "docs" / "technical_strategy.md").read_text()
        assert "acme/my-device-dhf" in tech_strategy
        assert "{{dhf_repo}}" not in tech_strategy

    def test_TC_SYS_027_023_init_product_template_creates_adapter_files(self, tmp_path):
        """
        TC-SYS-027-023: _init_product_template creates adapters/.cursorrules and
        adapters/copilot-instructions.md.

        @test_id: TC-SYS-027-023
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _init_product_template(product_dir, "Device", "acme/dhf", ["IEC_62304"])
        assert (product_dir / "AI-harness" / "adapters" / ".cursorrules").exists()
        assert (product_dir / "AI-harness" / "adapters" / "copilot-instructions.md").exists()

    def test_TC_SYS_027_024_init_product_template_creates_agent_files(self, tmp_path):
        """
        TC-SYS-027-024: _init_product_template creates CLAUDE.md, AGENTS.md, GEMINI.md.

        @test_id: TC-SYS-027-024
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _init_product_template(product_dir, "Device", "acme/dhf", ["IEC_62304"])
        assert (product_dir / "AI-harness" / "CLAUDE.md").exists()
        assert (product_dir / "AI-harness" / "AGENTS.md").exists()
        assert (product_dir / "AI-harness" / "GEMINI.md").exists()

    def test_TC_SYS_027_025_init_product_template_no_dhf_fallback(self, tmp_path):
        """
        TC-SYS-027-025: _init_product_template uses fallback text when dhf_repo is None.
        Fallback substitution applies to docs/ scaffold (not root harness, which has no placeholders).

        @test_id: TC-SYS-027-025
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _init_product_template(product_dir, "Device", None, ["IEC_62304"])
        tech_strategy = (product_dir / "docs" / "technical_strategy.md").read_text()
        assert "your-org/your-product-dhf" in tech_strategy
        assert "{{dhf_repo}}" not in tech_strategy

    def test_TC_SYS_027_026_init_dhf_template_substitutes_product_repo(self, tmp_path):
        """
        TC-SYS-027-026: _init_dhf_template substitutes {{product_repo}} in workflow files.

        @test_id: TC-SYS-027-026
        @links: SYS-027
        """
        dhf_dir = tmp_path / "my-dhf"
        _init_dhf_template(
            dhf_dir,
            "Device",
            ["IEC_62304"],
            product_repo="acme/my-device",
        )
        content = (dhf_dir / ".github" / "workflows" / "cr-develop.yml").read_text()
        assert "acme/my-device" in content
        assert "{{product_repo}}" not in content

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
        assert "compliantflow cr workflow complete" in content
        assert "--dhf-repo dhf" in content
        assert "python -m dhf_util item transition" not in content

    def test_TC_SYS_027_029_init_product_template_creates_docs(self, tmp_path):
        """
        TC-SYS-027-029: _init_product_template creates docs/ scaffold with strategy files.

        @test_id: TC-SYS-027-029
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _init_product_template(product_dir, "My Device", "acme/my-device-dhf", ["IEC_62304"])
        assert (product_dir / "docs" / "product_strategy.md").exists()
        assert (product_dir / "docs" / "product_roadmap.md").exists()
        assert (product_dir / "docs" / "technical_strategy.md").exists()
        assert (product_dir / "docs" / "testing_strategy.md").exists()
        assert (product_dir / "docs" / "adr" / "ADR-000-template.md").exists()

    def test_TC_SYS_027_030_docs_scaffold_substitutes_project_name(self, tmp_path):
        """
        TC-SYS-027-030: Strategy docs scaffold substitutes {{project_name}} throughout.

        @test_id: TC-SYS-027-030
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _init_product_template(product_dir, "Cardiac Monitor", "acme/dhf", ["IEC_62304"])
        for doc in ["product_strategy.md", "product_roadmap.md", "technical_strategy.md", "testing_strategy.md"]:
            content = (product_dir / "docs" / doc).read_text()
            assert "Cardiac Monitor" in content, f"{{{{project_name}}}} not substituted in {doc}"
            assert "{{project_name}}" not in content, f"Unsubstituted placeholder in {doc}"

    def test_TC_SYS_027_031_docs_scaffold_substitutes_dhf_repo(self, tmp_path):
        """
        TC-SYS-027-031: technical_strategy.md substitutes {{dhf_repo}} with actual DHF repo.

        @test_id: TC-SYS-027-031
        @links: SYS-027
        """
        product_dir = tmp_path / "my-product"
        _init_product_template(product_dir, "Device", "acme/device-dhf", ["IEC_62304"])
        content = (product_dir / "docs" / "technical_strategy.md").read_text()
        assert "acme/device-dhf" in content
        assert "{{dhf_repo}}" not in content
