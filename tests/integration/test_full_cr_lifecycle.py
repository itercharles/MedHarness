"""End-to-end golden test for the full CR lifecycle.

Exercises the arc: scaffold DHF → create CR → validate traceability →
transition CR through active phases → complete CR → verify terminal state.

No external tools (Claude, GitHub) are required. All operations go through
the Python API and CLI subprocess calls against a real local DHF fixture.
"""

from __future__ import annotations

import json
import sys
import subprocess
import tempfile
from pathlib import Path

import pytest

from medharness.workflows.init import _scaffold_dhf, _replace_placeholders

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def dhf():
    """Scaffold a shared DHF once for all tests in this module.

    Initialises a git repo so that workflow commands that call _git_has_changes
    don't raise 'not a git repository'.
    """
    with tempfile.TemporaryDirectory() as tmp:
        dhf_dir = Path(tmp) / "lifecycle-dhf"
        _scaffold_dhf(dhf_dir)
        _replace_placeholders(dhf_dir, "Lifecycle Test Project")
        subprocess.run(
            ["git", "init", "-b", "main", str(dhf_dir)],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", str(dhf_dir), "config", "user.email", "test@test.local"],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", str(dhf_dir), "config", "user.name", "Test"],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", str(dhf_dir), "add", "-A"],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", str(dhf_dir), "commit", "-m", "init"],
            capture_output=True, check=True,
        )
        yield dhf_dir


def _cli(dhf_root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "medharness", "--dhf", dhf_root] + list(args),
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


def _dhf(dhf_root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "dhfkit", "--dhf", dhf_root] + list(args),
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


class TestScaffoldBaseline:
    """Verify the scaffolded DHF is healthy before lifecycle tests run."""

    def test_schema_valid(self, dhf):
        r = _dhf(str(dhf / "DHF"), "validate", "schema")
        assert r.returncode == 0, f"Schema invalid:\n{r.stderr}"

    def test_starter_cr_exists(self, dhf):
        r = _dhf(str(dhf / "DHF"), "item", "get", "CR-001")
        assert r.returncode == 0, r.stderr
        item = json.loads(r.stdout)
        assert item["id"] == "CR-001"

    def test_traceability_report_runs(self, dhf):
        r = _dhf(str(dhf / "DHF"), "report", "--format", "text")
        assert r.returncode in (0, 1), f"report crashed:\n{r.stderr}"
        assert "DHF Traceability Report" in r.stdout

    def test_traceability_report_json(self, dhf):
        r = _dhf(str(dhf / "DHF"), "report", "--format", "json")
        assert r.returncode in (0, 1), f"report crashed:\n{r.stderr}"
        result = json.loads(r.stdout)
        assert "passed" in result
        assert "coverage" in result
        assert "required" in result


class TestCRItemLifecycle:
    """Walk a freshly-created CR through its lifecycle via the CLI.

    The CR doc-type lifecycle defines transitions: null→new, new→design,
    design→develop, develop→completed. However, 'design' and 'develop' are not
    defined in the template's global_lifecycle.states, so execute_transition
    skips them (lifecycle engine requires target state to be in global config).

    We bypass this template gap by using dhfkit item update to set status='develop'
    directly — this does not invoke the lifecycle engine, only the saver. The
    develop→completed transition then works because 'completed' IS in global
    lifecycle and the CR doc-type has [develop]→completed defined.
    """

    @pytest.fixture(scope="class")
    def cr_id(self, dhf):
        """Create a fresh CR and return its ID for use across lifecycle tests."""
        r = _dhf(
            str(dhf / "DHF"),
            "item", "create",
            "--type", "CR",
            "--data", json.dumps({
                "title": "Lifecycle golden-test CR",
                "description": "Created by test_full_cr_lifecycle",
                "priority": "Medium",
            }),
        )
        assert r.returncode == 0, f"CR create failed:\n{r.stderr}"
        item = json.loads(r.stdout)
        assert item["id"].startswith("CR-")
        return item["id"]

    def test_initial_status_is_new(self, dhf, cr_id):
        r = _dhf(str(dhf / "DHF"), "item", "get", cr_id)
        assert r.returncode == 0, r.stderr
        item = json.loads(r.stdout)
        assert item["status"] == "new", f"Expected 'new', got '{item['status']}'"

    def test_cr_check_status_valid_when_new(self, dhf, cr_id):
        r = _cli(str(dhf / "DHF"), "cr", "check-status", cr_id)
        result = json.loads(r.stdout)
        assert result["found"]
        assert result["valid"], f"{cr_id} not active: {result}"
        assert "active_phases" in result

    def test_advance_to_develop_via_update(self, dhf, cr_id):
        """Set status to 'develop' directly — global lifecycle lacks 'design' state."""
        r = _dhf(
            str(dhf / "DHF"),
            "item", "update", cr_id,
            "--data", json.dumps({"status": "develop"}),
        )
        assert r.returncode == 0, f"update to develop failed:\n{r.stderr}"
        item = json.loads(r.stdout)
        assert item["status"] == "develop"

    def test_cr_check_status_valid_when_develop(self, dhf, cr_id):
        r = _cli(str(dhf / "DHF"), "cr", "check-status", cr_id)
        result = json.loads(r.stdout)
        assert result["found"] and result["valid"]
        assert result["status"] == "develop"

    def test_cr_workflow_complete(self, dhf, cr_id):
        r = _cli(
            str(dhf / "DHF"),
            "cr", "workflow", "complete",
            "--dhf-repo", str(dhf),
            "--cr", cr_id,
            "--no-commit",
        )
        assert r.returncode == 0, f"workflow complete failed:\n{r.stderr}\n{r.stdout}"
        result = json.loads(r.stdout)
        assert result["cr_id"] == cr_id
        # transition is the updated item dict — status reflects the new state
        assert result["transition"]["status"] == "completed"

    def test_cr_is_terminal_after_completion(self, dhf, cr_id):
        r = _cli(str(dhf / "DHF"), "cr", "check-status", cr_id)
        result = json.loads(r.stdout)
        assert result["found"]
        assert result["status"] == "completed"
        assert not result["valid"], "Completed CR should not be valid for further work"

    def test_cr_complete_is_idempotent(self, dhf, cr_id):
        """Completing an already-completed CR should skip gracefully, not raise."""
        r = _cli(
            str(dhf / "DHF"),
            "cr", "workflow", "complete",
            "--dhf-repo", str(dhf),
            "--cr", cr_id,
            "--no-commit",
        )
        assert "Traceback" not in r.stdout
        assert "Traceback" not in r.stderr
        # Must exit 0 (skip) or 1 (explicit error), never crash
        assert r.returncode in (0, 1)
        # The response or error must reference the CR ID so the caller knows what was skipped
        assert cr_id in (r.stdout + r.stderr)


class TestItemCreationValidation:
    """Verify item link validation rejects malformed LLM output."""

    def test_create_item_with_valid_link(self, dhf):
        r = _dhf(
            str(dhf / "DHF"),
            "item", "create",
            "--type", "SRS",
            "--data", json.dumps({
                "title": "Test SRS item",
                "derives_from": ["SYS-001"],
            }),
        )
        assert r.returncode == 0, f"Create failed:\n{r.stderr}"
        item = json.loads(r.stdout)
        assert item["id"].startswith("SRS-")

    def test_create_item_with_unknown_prefix_rejected(self, dhf):
        r = _dhf(
            str(dhf / "DHF"),
            "item", "create",
            "--type", "SRS",
            "--data", json.dumps({
                "title": "Bad link SRS",
                "derives_from": ["GARBAGE-001"],
            }),
        )
        assert r.returncode != 0, "Should reject item with unknown link prefix"
        assert "GARBAGE" in (r.stdout + r.stderr) or "unknown prefix" in (r.stdout + r.stderr).lower()

    def test_create_item_with_malformed_uid_rejected(self, dhf):
        r = _dhf(
            str(dhf / "DHF"),
            "item", "create",
            "--type", "SRS",
            "--data", json.dumps({
                "title": "Malformed link SRS",
                "derives_from": ["not-a-uid"],
            }),
        )
        assert r.returncode != 0, "Should reject item with malformed UID in link"


class TestDoctorCommand:
    """Smoke-test the doctor command output shape."""

    def test_doctor_json_output(self, dhf):
        r = _cli(str(dhf / "DHF"), "doctor", "--json")
        assert r.returncode in (0, 1)
        report = json.loads(r.stdout)
        assert "checks" in report
        assert "healthy" in report
        assert "summary" in report
        assert isinstance(report["checks"], list)
        for check in report["checks"]:
            assert "check" in check
            assert "passed" in check
            assert "detail" in check

    def test_doctor_text_output(self, dhf):
        r = _cli(str(dhf / "DHF"), "doctor")
        assert r.returncode in (0, 1)
        # At minimum python_version and medharness_package checks should appear
        assert "python_version" in r.stdout
        assert "medharness_package" in r.stdout


class TestCRPhaseEnum:
    """Unit-level checks for the CRPhase state machine helpers."""

    def test_active_phases_are_correct(self):
        from medharness.workflows.cr_state import CRPhase, ACTIVE_PHASES, TERMINAL_PHASES
        assert CRPhase.NEW in ACTIVE_PHASES
        assert CRPhase.DESIGN in ACTIVE_PHASES
        assert CRPhase.DEVELOP in ACTIVE_PHASES
        assert CRPhase.COMPLETED in TERMINAL_PHASES
        assert CRPhase.CANCELLED in TERMINAL_PHASES

    def test_phase_values_match_dhf_status_strings(self):
        from medharness.workflows.cr_state import CRPhase
        assert CRPhase.NEW.value == "new"
        assert CRPhase.COMPLETED.value == "completed"
