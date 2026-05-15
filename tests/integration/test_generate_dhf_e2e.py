"""Golden E2E integration test for generate_dhf and generate_code orchestration.

Exercises the full Python-side orchestration without invoking the Claude CLI:
  - scaffold real DHF, initialise git (CR-001 comes from the scaffold)
  - monkeypatch _run_claude to control exit code and output
  - call generate_dhf / generate_code directly
  - verify response structure, step names, outcome, and artifact shape

All operations run against real DHF fixtures. No network calls are made.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

from medharness.workflows.init import _scaffold_dhf, _replace_placeholders

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dhf_repo():
    """Scaffold a DHF with a git repo initialised at origin/main."""
    with tempfile.TemporaryDirectory() as tmp:
        dhf_dir = Path(tmp) / "e2e-dhf"
        _scaffold_dhf(dhf_dir)
        _replace_placeholders(dhf_dir, "E2E Test Project")
        for cmd in [
            ["git", "init", "-b", "main", str(dhf_dir)],
            ["git", "-C", str(dhf_dir), "config", "user.email", "e2e@test.local"],
            ["git", "-C", str(dhf_dir), "config", "user.name", "E2E Test"],
            ["git", "-C", str(dhf_dir), "add", "-A"],
            ["git", "-C", str(dhf_dir), "commit", "-m", "init"],
            # Create an origin remote alias so origin/main resolves locally.
            ["git", "-C", str(dhf_dir), "remote", "add", "origin", str(dhf_dir)],
            ["git", "-C", str(dhf_dir), "fetch", "origin"],
        ]:
            subprocess.run(cmd, capture_output=True, check=True)
        yield dhf_dir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUIRED_TOP_LEVEL_KEYS = {
    "cr_id", "stage", "outcome", "summary",
    "timing", "inputs", "progress", "steps",
    "artifacts", "diagnostics", "warnings", "errors",
}

_REQUIRED_ARTIFACT_KEYS_DHF = {"items_changed", "design_impact"}
_REQUIRED_ARTIFACT_KEYS_CODE = {"files_changed"}


def _step_names(result: dict) -> list[str]:
    return [s["name"] for s in result.get("steps", [])]


# ---------------------------------------------------------------------------
# generate_dhf — happy stub (Claude exits 0)
# ---------------------------------------------------------------------------

class TestGenerateDhfSuccessStub:
    """When _run_claude exits 0, outcome must not be tool_error."""

    @pytest.fixture(autouse=True)
    def stub_claude_ok(self, monkeypatch):
        monkeypatch.setattr(
            "medharness.services.cr_generation._run_claude",
            lambda prompt: (0, "DHF generation complete."),
        )

    def test_response_has_required_keys(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        assert _REQUIRED_TOP_LEVEL_KEYS <= result.keys(), (
            f"Missing keys: {_REQUIRED_TOP_LEVEL_KEYS - result.keys()}"
        )

    def test_cr_id_and_stage_echoed(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        assert result["cr_id"] == "CR-001"
        assert result["stage"] == "generate_dhf"

    def test_outcome_is_not_tool_error(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        assert result["outcome"] != "tool_error", (
            f"Expected non-tool_error outcome, got: {result['outcome']}\n"
            f"Warnings: {result.get('warnings')}"
        )

    def test_initial_generation_step_present(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        assert "run_initial_generation" in _step_names(result)

    def test_validate_step_present(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        names = _step_names(result)
        assert any(n.startswith("validate_") for n in names), (
            f"No validate_* step found in steps: {names}"
        )

    def test_artifacts_have_items_changed(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        artifacts = result.get("artifacts", {})
        assert _REQUIRED_ARTIFACT_KEYS_DHF <= artifacts.keys()
        ic = artifacts["items_changed"]
        assert "created" in ic and "updated" in ic and "deleted" in ic

    def test_timing_has_elapsed_ms(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        assert "elapsed_ms" in result["timing"]
        assert result["timing"]["elapsed_ms"] >= 0

    def test_errors_is_list(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        assert isinstance(result["errors"], list)

    def test_each_error_has_field_issue_fix(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        for err in result["errors"]:
            assert "field" in err, f"error missing 'field': {err}"
            assert "issue" in err, f"error missing 'issue': {err}"
            assert "fix" in err, f"error missing 'fix': {err}"


# ---------------------------------------------------------------------------
# generate_dhf — tool error stub (Claude exits non-zero)
# ---------------------------------------------------------------------------

class TestGenerateDhfToolErrorStub:
    """When _run_claude exits non-zero, outcome must be tool_error."""

    @pytest.fixture(autouse=True)
    def stub_claude_fail(self, monkeypatch):
        monkeypatch.setattr(
            "medharness.services.cr_generation._run_claude",
            lambda prompt: (1, "fatal: claude not found"),
        )

    def test_outcome_is_tool_error(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        assert result["outcome"] == "tool_error", (
            f"Expected tool_error, got {result['outcome']}"
        )

    def test_step_outcome_is_failed(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        gen_step = next(
            (s for s in result["steps"] if s["name"] == "run_initial_generation"),
            None,
        )
        assert gen_step is not None
        assert gen_step["outcome"] == "failed"

    def test_response_still_has_required_keys(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF")
        assert _REQUIRED_TOP_LEVEL_KEYS <= result.keys()


# ---------------------------------------------------------------------------
# generate_dhf — revision mode (pr_number supplied)
# ---------------------------------------------------------------------------

class TestGenerateDhfRevisionMode:
    """Revision mode (pr_number != None) must include a prepare_prompt step."""

    @pytest.fixture(autouse=True)
    def stub_claude_ok(self, monkeypatch):
        monkeypatch.setattr(
            "medharness.services.cr_generation._run_claude",
            lambda prompt: (0, "Revision complete."),
        )
        # Stub PR feedback fetch so no network call is made.
        monkeypatch.setattr(
            "medharness.services.cr_generation._get_pr_feedback",
            lambda pr_number: {
                "prompt_text": "(stubbed feedback)",
                "diagnostics": {"attempted": True, "pr_number": pr_number,
                                "comments_status": "ok", "reviews_status": "ok"},
                "warnings": [],
            },
        )

    def test_revision_mode_echoed_in_inputs(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF", pr_number=42)
        assert result["inputs"]["revision_mode"] is True
        assert result["inputs"]["pr_number"] == 42

    def test_fetch_pr_feedback_step_present(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF", pr_number=42)
        assert "fetch_pr_feedback" in _step_names(result)

    def test_outcome_not_tool_error_in_revision(self, dhf_repo):
        from medharness.services.cr_generation import generate_dhf
        result = generate_dhf("CR-001", dhf_repo / "DHF", pr_number=42)
        assert result["outcome"] != "tool_error"


# ---------------------------------------------------------------------------
# generate_code — happy stub
# ---------------------------------------------------------------------------

class TestGenerateCodeSuccessStub:
    """generate_code orchestration smoke test."""

    @pytest.fixture(autouse=True)
    def stub_claude_ok(self, monkeypatch):
        monkeypatch.setattr(
            "medharness.services.cr_generation._run_claude",
            lambda prompt: (0, "Implementation complete."),
        )

    def test_response_has_required_keys(self, dhf_repo):
        from medharness.services.cr_generation import generate_code
        result = generate_code("CR-001", dhf_repo / "DHF")
        assert _REQUIRED_TOP_LEVEL_KEYS <= result.keys()

    def test_stage_is_develop(self, dhf_repo):
        from medharness.services.cr_generation import generate_code
        result = generate_code("CR-001", dhf_repo / "DHF")
        assert result["stage"] == "develop"

    def test_outcome_not_tool_error(self, dhf_repo):
        from medharness.services.cr_generation import generate_code
        result = generate_code("CR-001", dhf_repo / "DHF")
        assert result["outcome"] != "tool_error"

    def test_artifacts_have_files_changed(self, dhf_repo):
        from medharness.services.cr_generation import generate_code
        result = generate_code("CR-001", dhf_repo / "DHF")
        artifacts = result.get("artifacts", {})
        assert _REQUIRED_ARTIFACT_KEYS_CODE <= artifacts.keys()
        fc = artifacts["files_changed"]
        assert "created" in fc and "updated" in fc and "deleted" in fc

    def test_run_review_step_present(self, dhf_repo):
        """generate_code always runs a soft review step at the end."""
        from medharness.services.cr_generation import generate_code
        result = generate_code("CR-001", dhf_repo / "DHF")
        assert "run_review" in _step_names(result)


# ---------------------------------------------------------------------------
# generate_dhf — fix-pass flow
#
# The first _run_claude call writes a real CRS item to the DHF via the CLI.
# git detects the new file; validate_generate_dhf fires the cascade check
# (CRS-002 has no SYS child) and returns errors.  The fix pass is triggered.
# The second _run_claude call noops.  validate_after_fix still finds errors
# (cascade unresolved), so outcome is "completed_with_errors".
#
# This exercises: initial_error_count > 0 → fix_attempted → run_fix_generation
# → validate_after_fix → completed_with_errors outcome.
# ---------------------------------------------------------------------------

def _make_fix_pass_dhf(tmp: str) -> Path:
    """Scaffold an isolated DHF with origin/main wired for the fix-pass tests."""
    dhf_dir = Path(tmp) / "fix-pass-dhf"
    _scaffold_dhf(dhf_dir)
    _replace_placeholders(dhf_dir, "Fix Pass Test")
    for cmd in [
        ["git", "init", "-b", "main", str(dhf_dir)],
        ["git", "-C", str(dhf_dir), "config", "user.email", "fix@test.local"],
        ["git", "-C", str(dhf_dir), "config", "user.name", "Fix Pass Test"],
        ["git", "-C", str(dhf_dir), "add", "-A"],
        ["git", "-C", str(dhf_dir), "commit", "-m", "init"],
        ["git", "-C", str(dhf_dir), "remote", "add", "origin", str(dhf_dir)],
        ["git", "-C", str(dhf_dir), "fetch", "origin"],
    ]:
        subprocess.run(cmd, capture_output=True, check=True)
    return dhf_dir


class TestGenerateDhfFixPassFlow:
    """Verify the validate→fix→validate cycle when initial generation has errors."""

    @pytest.fixture(scope="class")
    def fix_pass_result(self):
        """Run generate_dhf once with a stub that creates a bare CRS item on the
        first call (triggering the cascade check) and noops on the fix pass."""
        with tempfile.TemporaryDirectory() as tmp:
            dhf_dir = _make_fix_pass_dhf(tmp)
            dhf_path = dhf_dir / "DHF"
            call_count = {"n": 0}

            def _stub(prompt: str) -> tuple[int, str]:
                call_count["n"] += 1
                if call_count["n"] == 1:
                    # Create a CRS item with no SYS child — cascade check will fire.
                    subprocess.run(
                        [
                            sys.executable, "-m", "medharness",
                            "--dhf", str(dhf_path),
                            "dhf", "item", "create",
                            "--type", "CRS",
                            "--data", json.dumps({
                                "title": "Fix-Pass Test CRS",
                                "content": "Stub-created item for cascade test.",
                                "user_group": "Engineering",
                                "priority": "Low",
                            }),
                        ],
                        capture_output=True, cwd=str(REPO_ROOT),
                    )
                    # Commit the new file so `git diff origin/main` detects it.
                    # (git diff <tree> only sees committed or modified-tracked
                    # changes, not untracked or merely staged files.)
                    subprocess.run(["git", "-C", str(dhf_dir), "add", "-A"], capture_output=True)
                    subprocess.run(
                        ["git", "-C", str(dhf_dir), "commit", "-m", "stub: add CRS item"],
                        capture_output=True,
                    )
                # Fix-pass call (n >= 2): noop — cascade error remains.
                return 0, "ok"

            with mock.patch("medharness.services.cr_generation._run_claude", _stub):
                from medharness.services.cr_generation import generate_dhf
                result = generate_dhf("CR-001", dhf_path)

            yield result

    def test_fix_was_attempted(self, fix_pass_result):
        assert fix_pass_result["diagnostics"]["fix_attempted"] is True

    def test_initial_error_count_positive(self, fix_pass_result):
        assert fix_pass_result["diagnostics"]["initial_error_count"] > 0

    def test_run_fix_generation_step_present(self, fix_pass_result):
        assert "run_fix_generation" in _step_names(fix_pass_result)

    def test_validate_after_fix_step_present(self, fix_pass_result):
        assert "validate_after_fix" in _step_names(fix_pass_result)

    def test_outcome_is_completed_with_errors(self, fix_pass_result):
        assert fix_pass_result["outcome"] == "completed_with_errors"

    def test_cascade_error_present_in_errors(self, fix_pass_result):
        """At least one error must reference the cascade check for the new CRS item."""
        cascade_errors = [
            e for e in fix_pass_result["errors"]
            if e.get("field", "").startswith("cascade.")
        ]
        assert cascade_errors, (
            f"Expected a cascade.* error; got fields: "
            f"{[e.get('field') for e in fix_pass_result['errors']]}"
        )
