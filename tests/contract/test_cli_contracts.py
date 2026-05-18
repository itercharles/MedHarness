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
        """medharness dhf exists and exposes context subcommand."""
        r = _run("medharness", "dhf", "--help")
        assert r.returncode == 0
        assert "context" in r.stdout, "Missing dhf subcommand group: context"


class TestInitCommand:
    """Verify init command is callable (interactive, minimal check)."""

    def test_init_help(self):
        """medharness init --help exits 0."""
        r = _run("medharness", "init", "--help")
        assert r.returncode == 0, r.stderr


class TestCRGenerationCommands:
    """Contract tests for medharness CR generation and preflight CI commands."""

    def test_develop_cr_help(self):
        """medharness ci develop-cr --help exits 0."""
        r = _run("medharness", "ci", "develop-cr", "--help")
        assert r.returncode == 0, r.stderr

    def test_generate_dhf_help(self):
        """medharness ci generate-dhf --help exits 0."""
        r = _run("medharness", "ci", "generate-dhf", "--help")
        assert r.returncode == 0, r.stderr

    def test_validate_code_help(self):
        """medharness ci validate-code --help exits 0."""
        r = _run("medharness", "ci", "validate-code", "--help")
        assert r.returncode == 0, r.stderr
        assert "--dhf" not in r.stdout

    def test_validate_branch_help(self):
        """medharness ci validate-branch --help exits 0."""
        r = _run("medharness", "ci", "validate-branch", "--help")
        assert r.returncode == 0, r.stderr
        assert "--dhf" not in r.stdout

    def test_develop_cr_requires_cr_flag(self):
        """medharness ci develop-cr without --cr exits non-zero with usage error."""
        r = _run("medharness", "ci", "develop-cr")
        assert r.returncode != 0

    def test_generate_dhf_requires_cr_flag(self):
        """medharness ci generate-dhf without --cr exits non-zero."""
        r = _run("medharness", "ci", "generate-dhf")
        assert r.returncode != 0

    def test_validate_code_requires_cr_flag(self):
        """medharness ci validate-code without --cr exits non-zero."""
        r = _run("medharness", "ci", "validate-code")
        assert r.returncode != 0

    def test_validate_branch_requires_cr_flag(self):
        """medharness ci validate-branch without --cr exits non-zero."""
        r = _run("medharness", "ci", "validate-branch")
        assert r.returncode != 0

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
        for cmd in ["develop-cr", "generate-dhf", "validate-code", "validate-branch"]:
            assert cmd in r.stdout, f"Command {cmd!r} missing from ci --help"


class TestCLIEntrypoints:
    """Verify medharness is available via python -m."""

    def test_medharness_entrypoint(self):
        """python -m medharness --help exits 0."""
        r = _run("medharness", "--help")
        assert r.returncode == 0, r.stderr


class TestOutputContract:
    """Verify automation commands write JSON to stdout, human messages to stderr."""

    def test_dhfkit_item_get_json_on_stdout(self, scaffolded_dhf):
        """dhfkit item get writes JSON to stdout."""
        import json
        r = _run("dhfkit", "--dhf", str(scaffolded_dhf / "DHF"), "item", "get", "SYS-001")
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

    def test_dhfkit_validate_schema_output(self, scaffolded_dhf):
        """dhfkit validate schema produces output."""
        r = _run("dhfkit", "--dhf", str(scaffolded_dhf / "DHF"), "validate", "schema")
        assert r.returncode == 0
        assert len(r.stdout.strip() + r.stderr.strip()) > 0, "produced no output"

    def test_dhfkit_item_list_ndjson(self, scaffolded_dhf):
        """dhfkit item list writes NDJSON to stdout."""
        import json
        r = _run("dhfkit", "--dhf", str(scaffolded_dhf / "DHF"), "item", "list", "--type", "SYS")
        assert r.returncode == 0
        lines = r.stdout.strip().split("\n")
        assert len(lines) > 0
        for line in lines:
            item = json.loads(line)
            assert "id" in item
            assert "type" in item

    def test_dhfkit_report_stdout(self, scaffolded_dhf):
        """dhfkit report writes traceability report to stdout."""
        r = _run("dhfkit", "--dhf", str(scaffolded_dhf / "DHF"), "report")
        assert r.returncode in (0, 1), f"report crashed:\n{r.stderr}"
        assert "DHF Traceability Report" in r.stdout

    def test_dhfkit_report_json(self, scaffolded_dhf):
        """dhfkit report --format json writes JSON to stdout."""
        import json
        r = _run("dhfkit", "--dhf", str(scaffolded_dhf / "DHF"), "report", "--format", "json")
        assert r.returncode in (0, 1), f"report --format json crashed:\n{r.stderr}"
        result = json.loads(r.stdout)
        assert "passed" in result
        assert "coverage" in result
