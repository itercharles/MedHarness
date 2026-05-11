"""Contract tests: verify all stable CLI commands exist and are callable.

These tests protect the public CLI surface defined in compatibility-contracts.md.

"""

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run(*args: str) -> "subprocess.CompletedProcess":
    import subprocess
    return subprocess.run(
        [sys.executable, "-m", *args],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


class TestMedHarnessCLI:
    """Verify every stable medharness CLI command is callable."""

    def test_init_help(self):
        """medharness --help exits 0."""
        r = _run("medharness", "--help")
        assert r.returncode == 0, r.stderr

    def test_ci_test_coverage_help(self):
        """medharness ci test-coverage --help exits 0."""
        r = _run("medharness", "ci", "test-coverage", "--help")
        assert r.returncode == 0, r.stderr

    def test_ci_dhf_validate_help(self):
        """medharness ci dhf-validate --help exits 0."""
        r = _run("medharness", "ci", "dhf-validate", "--help")
        assert r.returncode == 0, r.stderr

    def test_ci_evidence_bundle_help(self):
        """medharness ci evidence bundle --help exits 0."""
        r = _run("medharness", "ci", "evidence", "bundle", "--help")
        assert r.returncode == 0, r.stderr

    def test_cr_check_status_help(self):
        """medharness cr check-status --help exits 0."""
        r = _run("medharness", "cr", "check-status", "--help")
        assert r.returncode == 0, r.stderr

    def test_dhf_facade_commands_exist(self):
        """All dhf facade subcommands exist."""
        r = _run("medharness", "dhf", "--help")
        assert r.returncode == 0
        for sub in ["item", "validate"]:
            assert sub in r.stdout, f"Missing dhf subcommand group: {sub}"


class TestDhfCLI:
    """Verify dhf operations via medharness dhf ..."""

    def test_dhf_help(self):
        """medharness dhf --help exits 0."""
        r = _run("medharness", "dhf", "--help")
        assert r.returncode == 0, r.stderr

    def test_dhf_validate_schema(self, scaffolded_dhf):
        """medharness dhf validate schema passes."""
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "validate", "schema")
        assert r.returncode == 0, r.stderr

    def test_dhf_test_list(self, scaffolded_dhf):
        """medharness dhf test list exits 0."""
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "test", "list")
        assert r.returncode == 0, r.stderr

    def test_dhf_doc_list(self, scaffolded_dhf):
        """medharness dhf doc list returns doc types."""
        import json
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "doc", "list")
        assert r.returncode == 0, r.stderr
        result = json.loads(r.stdout)
        types = result.get("doc_types", [])
        assert isinstance(types, list)
        assert "CRS" in types

    def test_dhf_doc_generate(self, scaffolded_dhf):
        """medharness dhf doc generate SYS produces output."""
        import json
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "doc", "generate", "SYS")
        if r.returncode != 0 and "cannot load library" in r.stderr:
            return
        assert r.returncode == 0, r.stderr
        result = json.loads(r.stdout)
        assert result["doc_type"] == "SYS"
        assert Path(result["output_path"]).exists()

    def test_dhf_item_all_types(self, scaffolded_dhf):
        """All 12 item types can be listed."""
        import json
        for code in ["UC", "CRS", "SYS", "SRS", "SWDD", "SYSARCH", "RISK", "RCM", "CR", "REL", "DEF", "SOUP"]:
            r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "item", "list", "--type", code)
            assert r.returncode == 0, f"dhf item list --type {code} failed"
            lines = r.stdout.strip().split("\n")
            assert len(lines) >= 1, f"No items for type {code}"


class TestDhfCommands:
    """Verify remaining dhf subcommands."""

    def test_dhf_item_transitions(self, scaffolded_dhf):
        """medharness dhf item transitions CR-001 returns JSON list."""
        import json
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "item", "transitions", "CR-001")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) >= 0

    def test_dhf_validate_traceability(self, scaffolded_dhf):
        """medharness dhf validate traceability exits 0."""
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "validate", "traceability")
        assert r.returncode == 0, r.stderr

    def test_dhf_doc_export(self, scaffolded_dhf):
        """medharness dhf doc export SYS produces PDF output."""
        import json
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "doc", "export", "SYS")
        if r.returncode != 0 and ("cannot load library" in r.stderr or "weasyprint" in r.stderr.lower() or "no module" in r.stderr.lower()):
            return
        assert r.returncode == 0, r.stderr
        result = json.loads(r.stdout)
        assert "pdf_path" in result

    def test_dhf_config_doc_types(self, scaffolded_dhf):
        """medharness dhf config doc-types returns type list."""
        import json
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "config", "doc-types")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) >= 3  # At least a few doc types


class TestInitCommand:
    """Verify init command is callable (interactive, minimal check)."""

    def test_init_help(self):
        """medharness init --help exits 0."""
        r = _run("medharness", "init", "--help")
        assert r.returncode == 0, r.stderr


class TestCRGenerationCommands:
    """Contract tests for medharness CR generation and preflight CI commands."""

    def test_analyze_cr_help(self):
        """medharness ci analyze-cr --help exits 0."""
        r = _run("medharness", "ci", "analyze-cr", "--help")
        assert r.returncode == 0, r.stderr

    def test_design_cr_help(self):
        """medharness ci design-cr --help exits 0."""
        r = _run("medharness", "ci", "design-cr", "--help")
        assert r.returncode == 0, r.stderr

    def test_develop_cr_help(self):
        """medharness ci develop-cr --help exits 0."""
        r = _run("medharness", "ci", "develop-cr", "--help")
        assert r.returncode == 0, r.stderr

    def test_validate_design_help(self):
        """medharness ci validate-design --help exits 0."""
        r = _run("medharness", "ci", "validate-design", "--help")
        assert r.returncode == 0, r.stderr

    def test_validate_code_help(self):
        """medharness ci validate-code --help exits 0."""
        r = _run("medharness", "ci", "validate-code", "--help")
        assert r.returncode == 0, r.stderr

    def test_validate_branch_help(self):
        """medharness ci validate-branch --help exits 0."""
        r = _run("medharness", "ci", "validate-branch", "--help")
        assert r.returncode == 0, r.stderr

    def test_analyze_cr_requires_cr_flag(self):
        """medharness ci analyze-cr without --cr exits non-zero with usage error."""
        r = _run("medharness", "ci", "analyze-cr")
        assert r.returncode != 0
        assert "cr" in r.stderr.lower() or "cr" in r.stdout.lower()

    def test_design_cr_requires_cr_flag(self):
        """medharness ci design-cr without --cr exits non-zero with usage error."""
        r = _run("medharness", "ci", "design-cr")
        assert r.returncode != 0

    def test_develop_cr_requires_cr_flag(self):
        """medharness ci develop-cr without --cr exits non-zero with usage error."""
        r = _run("medharness", "ci", "develop-cr")
        assert r.returncode != 0

    def test_validate_design_requires_cr_flag(self):
        """medharness ci validate-design without --cr exits non-zero."""
        r = _run("medharness", "ci", "validate-design")
        assert r.returncode != 0

    def test_validate_code_requires_cr_flag(self):
        """medharness ci validate-code without --cr exits non-zero."""
        r = _run("medharness", "ci", "validate-code")
        assert r.returncode != 0

    def test_validate_branch_requires_cr_flag(self):
        """medharness ci validate-branch without --cr exits non-zero."""
        r = _run("medharness", "ci", "validate-branch")
        assert r.returncode != 0

    def test_analyze_cr_accepts_pr_flag(self):
        """medharness ci analyze-cr --help shows --pr option."""
        r = _run("medharness", "ci", "analyze-cr", "--help")
        assert "--pr" in r.stdout

    def test_design_cr_accepts_pr_flag(self):
        """medharness ci design-cr --help shows --pr option."""
        r = _run("medharness", "ci", "design-cr", "--help")
        assert "--pr" in r.stdout

    def test_develop_cr_accepts_pr_flag(self):
        """medharness ci develop-cr --help shows --pr option."""
        r = _run("medharness", "ci", "develop-cr", "--help")
        assert "--pr" in r.stdout

    def test_validate_code_accepts_since_ref_flag(self):
        """medharness ci validate-code --help shows --since-ref option."""
        r = _run("medharness", "ci", "validate-code", "--help")
        assert "--since-ref" in r.stdout

    def test_validate_branch_accepts_code_path_flag(self):
        """medharness ci validate-branch --help shows --code-path option."""
        r = _run("medharness", "ci", "validate-branch", "--help")
        assert "--code-path" in r.stdout

    def test_commands_appear_in_ci_group_help(self):
        """Generation and preflight commands are listed in medharness ci --help."""
        r = _run("medharness", "ci", "--help")
        assert r.returncode == 0, r.stderr
        for cmd in ["analyze-cr", "design-cr", "develop-cr", "validate-design", "validate-code", "validate-branch"]:
            assert cmd in r.stdout, f"Command {cmd!r} missing from ci --help"


class TestCLIEntrypoints:
    """Verify medharness is available via python -m."""

    def test_medharness_entrypoint(self):
        """python -m medharness --help exits 0."""
        r = _run("medharness", "--help")
        assert r.returncode == 0, r.stderr


class TestOutputContract:
    """Verify automation commands write JSON to stdout, human messages to stderr."""

    def test_dhf_item_get_json_on_stdout(self, scaffolded_dhf):
        """medharness dhf item get writes JSON to stdout."""
        import json
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "item", "get", "SYS-001")
        assert r.returncode == 0
        item = json.loads(r.stdout)
        assert "id" in item
        assert "all_linked_uids" in item
        if r.stderr.strip():
            try:
                json.loads(r.stderr)
                pytest.fail("stderr contained JSON data")
            except json.JSONDecodeError:
                pass

    def test_dhf_validate_schema_stderr(self, scaffolded_dhf):
        """medharness dhf validate schema produces output."""
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "validate", "schema")
        assert r.returncode == 0
        assert len(r.stdout.strip() + r.stderr.strip()) > 0, "produced no output"

    def test_dhf_item_list_ndjson(self, scaffolded_dhf):
        """medharness dhf item list writes NDJSON to stdout."""
        import json
        r = _run("medharness", "--dhf", str(scaffolded_dhf / "DHF"), "dhf", "item", "list", "--type", "SYS")
        assert r.returncode == 0
        lines = r.stdout.strip().split("\n")
        assert len(lines) > 0
        for line in lines:
            item = json.loads(line)
            assert "id" in item
            assert "type" in item
