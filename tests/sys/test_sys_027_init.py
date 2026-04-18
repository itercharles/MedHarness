"""Tests for compliantflow init command (CR-054 / SYS-027).

Covers the pure-Python logic of init_cmd.py:
- compliance.yml generation for various standard/DHF/LLM combinations
- DHF CI workflow template content
- Standard label and governance file mappings
"""

import pytest
from compliantflow.init_cmd import (
    GOVERNANCE_FILES,
    STANDARD_LABELS,
    TEMPLATE_DIR,
    _generate_compliance_yaml,
    _write_dhf_ci_workflow,
    _write_dhf_cr_transition_workflow,
)
import tempfile
from pathlib import Path


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
        assert "python -m utils validate schema" in content

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
        assert "python -m utils item transition" in content
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
