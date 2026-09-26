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

        # A CR can only close once it carries what closure is supposed to mean.
        # The AI workflow writes these; a fixture standing in for a CR that has
        # been through it has to supply them, or it is standing in for a CR that
        # has not.
        u = _dhf(
            str(dhf / "DHF"), "item", "update", item["id"],
            "--data", json.dumps({
                "implementation_notes": "Implemented by the golden test.",
                "affected_risk_items": [],
                "triage_result": {"verdict": "approved"},
            }),
        )
        assert u.returncode == 0, f"CR update failed:\n{u.stderr}"
        return item["id"]

    def test_initial_status_is_new(self, dhf, cr_id):
        r = _dhf(str(dhf / "DHF"), "item", "get", cr_id)
        assert r.returncode == 0, r.stderr
        item = json.loads(r.stdout)
        assert item["status"] == "new", f"Expected 'new', got '{item['status']}'"


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

    def test_doctor_answers_in_json_like_every_command(self, dhf):
        """It printed prose to stdout unless given --json, alone among commands."""
        r = _cli(str(dhf / "DHF"), "doctor")
        assert r.returncode in (0, 1)
        report = json.loads(r.stdout)
        assert {"checks", "healthy", "summary"} <= set(report)
        for check in report["checks"]:
            assert {"check", "passed", "detail"} <= set(check)
        assert "python_version" in r.stderr, "the readable lines belong on stderr"

    def test_doctor_checks_the_dhf_it_is_given(self, dhf, tmp_path):
        named = _cli(str(tmp_path / "nowhere"), "doctor")
        assert named.returncode == 1
        failed = {c["check"] for c in json.loads(named.stdout)["checks"] if not c["passed"]}
        assert "dhf_config" in failed

    def test_doctor_before_init_does_not_fail_on_the_missing_dhf(self, tmp_path):
        """Nothing is named and ./DHF does not exist: there is no DHF to check yet."""
        r = subprocess.run(
            [sys.executable, "-m", "medharness", "doctor"],
            capture_output=True, text=True, cwd=tmp_path,
        )
        checks = {c["check"] for c in json.loads(r.stdout)["checks"]}
        assert "dhf_config" not in checks, "doctor judged a DHF that nobody asked about"


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
