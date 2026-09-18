"""Contract tests: verify all stable CLI commands exist and are callable.

These tests protect the public CLI surface defined in compatibility-contracts.md.

"""

import json

from medharness.services.ci import ENVELOPE_KEYS

ENVELOPE = set(ENVELOPE_KEYS)
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
        """medharness verify tests --help exits 0."""
        r = _run("medharness", "verify", "tests", "--help")
        assert r.returncode == 0, r.stderr

    def test_ci_dhf_validate_help(self):
        """medharness verify dhf --help exits 0."""
        r = _run("medharness", "verify", "dhf", "--help")
        assert r.returncode == 0, r.stderr

    def test_ci_evidence_bundle_help(self):
        """medharness evidence bundle --help exits 0."""
        r = _run("medharness", "evidence", "bundle", "--help")
        assert r.returncode == 0, r.stderr


    def test_context_commands_exist(self):
        """medharness dhf exists and exposes context subcommand."""
        r = _run("medharness", "context", "--help")
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
        """medharness build code --help exits 0."""
        r = _run("medharness", "build", "code", "--help")
        assert r.returncode == 0, r.stderr

    def test_generate_dhf_help(self):
        """medharness build plan --help exits 0."""
        r = _run("medharness", "build", "plan", "--help")
        assert r.returncode == 0, r.stderr


    def test_validate_branch_help(self):
        """medharness workflow check-changes --help exits 0.

        It carries its own --dhf like the other DHF-reading gates. It was the
        one that did not, so a caller building from the gate manifest hit a
        usage error on the option every sibling accepts.
        """
        r = _run("medharness", "workflow", "check-changes", "--help")
        assert r.returncode == 0, r.stderr
        assert "--dhf" in r.stdout

    def test_develop_cr_requires_cr_flag(self):
        """medharness build code without --cr exits non-zero with usage error."""
        r = _run("medharness", "build", "code")
        assert r.returncode != 0

    def test_generate_dhf_requires_cr_flag(self):
        """medharness build plan without --cr exits non-zero."""
        r = _run("medharness", "build", "plan")
        assert r.returncode != 0

    def test_validate_code_requires_cr_flag(self):
        """medharness verify code without --cr exits non-zero."""
        r = _run("medharness", "verify", "code")
        assert r.returncode != 0

    def test_validate_branch_requires_cr_flag(self):
        """medharness workflow check-changes without --cr exits non-zero."""
        r = _run("medharness", "workflow", "check-changes")
        assert r.returncode != 0

    def test_develop_cr_accepts_pr_flag(self):
        """medharness build code --help shows --pr option."""
        r = _run("medharness", "build", "code", "--help")
        assert "--pr" in r.stdout


    def test_validate_branch_accepts_code_path_flag(self):
        """medharness workflow check-changes --help shows --code-path option."""
        r = _run("medharness", "workflow", "check-changes", "--help")
        assert "--code-path" in r.stdout

    def test_commands_appear_in_help_groups(self):
        """Each verb lists its own commands, so `--help` finds them all."""
        expected = {
            "verify": ["dhf", "tests", "soup", "completion"],
            "build": ["plan", "code", "dhf"],
            "workflow": ["check-changes", "check-approval", "github-event"],
        }
        for verb, commands in expected.items():
            r = _run("medharness", verb, "--help")
            assert r.returncode == 0, r.stderr
            for cmd in commands:
                assert cmd in r.stdout, f"{cmd!r} missing from `{verb} --help`"

    def test_upgrade_help(self):
        """medharness upgrade --help exits 0."""
        r = _run("medharness", "upgrade", "--help")
        assert r.returncode == 0, r.stderr
        assert "--apply" in r.stdout

    def test_verify_soup_help(self):
        """medharness verify soup --help exits 0."""
        r = _run("medharness", "verify", "soup", "--help")
        assert r.returncode == 0, r.stderr


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



    def test_verify_completion_output_shape(self, scaffolded_dhf, tmp_path):
        """verify completion writes JSON with all required keys to stdout."""
        import json, importlib.resources
        dhf = scaffolded_dhf / "DHF"
        # Install CR doc type (not in default scaffold)
        cr_src = importlib.resources.files("dhfkit").joinpath(
            "templates/config/doc_types/cr.yaml"
        )
        (dhf / "config" / "doc_types" / "cr.yaml").write_bytes(cr_src.read_bytes())
        # Write a minimal CR with all mandatory closure fields
        cr_dir = dhf / "items" / "07_cr"
        cr_dir.mkdir(parents=True, exist_ok=True)
        (cr_dir / "CR-CONTRACT.yaml").write_text(
            "id: CR-CONTRACT\n"
            "title: Contract test CR\n"
            "implementation_notes: 'plan'\n"
            "affected_risk_items: []\n"
            "triage_result:\n  verdict: approved\n"
            "proposed_new_items: []\n"
        )
        # Write an approved design review file (required by closure gate)
        review_dir = scaffolded_dhf / "docs" / "reviews"
        review_dir.mkdir(parents=True, exist_ok=True)
        (review_dir / "CR-CONTRACT-Design-Review.md").write_text(
            "# Design Review: CR-CONTRACT\n\n**Verdict:** Approved\n"
        )
        r = _run("medharness", "--dhf", str(dhf), "verify", "completion", "--cr", "CR-CONTRACT")
        payload = json.loads(r.stdout.splitlines()[0])
        assert payload.keys() == ENVELOPE, (
            f"stdout is the envelope and nothing else; got {sorted(payload)}"
        )
        assert isinstance(payload["passed"], bool)
        assert isinstance(payload["errors"], list)
        assert isinstance(payload["warnings"], list)

    def test_verify_soup_output_shape(self, scaffolded_dhf):
        """verify soup writes JSON with all required keys to stdout."""
        import json
        dhf = scaffolded_dhf / "DHF"
        r = _run("medharness", "--dhf", str(dhf), "verify", "soup")
        # No SOUP items with ecosystem → passes with checked_count=0
        assert r.returncode == 0, r.stderr
        payload = json.loads(r.stdout.splitlines()[0])
        assert payload.keys() == ENVELOPE, (
            f"stdout is the envelope and nothing else; got {sorted(payload)}"
        )
        assert isinstance(payload["passed"], bool)
        assert payload["summary"], "a pass with no summary cannot be told from an empty check"

    def test_upgrade_output_shape(self, scaffolded_dhf):
        """upgrade writes JSON with all required keys to stdout."""
        import json
        r = _run("medharness", "upgrade", "--project-dir", str(scaffolded_dhf))
        # A freshly scaffolded DHF should be up to date
        assert r.returncode == 0, r.stderr
        payload = json.loads(r.stdout.splitlines()[0])
        required_keys = {"installed_version", "files_checked", "up_to_date", "outdated", "missing", "summary"}
        assert required_keys <= payload.keys(), f"Missing keys: {required_keys - payload.keys()}"
        assert isinstance(payload["up_to_date"], list)
        assert isinstance(payload["outdated"], list)
        assert isinstance(payload["missing"], list)
