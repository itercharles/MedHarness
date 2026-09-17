"""A session that cannot be resumed is not a failed generation.

`build plan --pr N` and `build code --pr N` store a Claude session id in
a PR comment and pass it to `claude --resume` on the next run. The transcript
lives in `~/.claude` on the machine that created it, and every CI runner is a
new machine, so in CI that resume always fails:

    $ claude -p "say ok" --resume 00000000-0000-0000-0000-000000000000
    No conversation found with session ID: 00000000-0000-0000-0000-000000000000
    rc=1

The step is critical, so one unusable session id turned the whole run into
`tool_error` and the CR stage never advanced. ContourLab's CR-014 sat there:
the review found three real defects, the fix pass resolved them, the second
review approved — and the run was discarded because of the first step.

The revision prompt tells the model to read the branch and carries the PR
feedback inline, so the session is continuity, not a precondition.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from medharness.services.cr_generation import _resume_unavailable, _run_claude_step

GONE = "No conversation found with session ID: 158a6d1a-29cc-408f-9787-551d67865578"


class TestTheDetector:
    def test_the_real_message_is_recognised(self) -> None:
        assert _resume_unavailable(GONE)

    def test_case_does_not_matter(self) -> None:
        assert _resume_unavailable(GONE.lower())

    def test_an_ordinary_failure_is_not_a_lost_session(self) -> None:
        assert not _resume_unavailable("Error: rate limit exceeded")

    def test_success_output_is_not_a_lost_session(self) -> None:
        assert not _resume_unavailable("Implementation complete.")


def _step(calls: list, outcomes: list[tuple[int, str, str]]):
    """Run one LLM step whose underlying runner returns `outcomes` in order."""
    def fake(prompt, *, config, resume_session=""):
        calls.append(resume_session)
        return outcomes[len(calls) - 1]

    steps: list[dict] = []
    warnings: list[dict] = []
    with patch("medharness.services.cr_generation._run_llm", side_effect=fake):
        rc, output, session_id = _run_claude_step(
            name="run_initial_generation",
            prompt="revise it",
            steps=steps,
            warnings=warnings,
            critical=True,
            resume_session="158a6d1a-29cc-408f-9787-551d67865578",
        )
    return rc, output, session_id, steps, warnings


class TestTheFallback:
    def test_a_lost_session_is_retried_without_one(self) -> None:
        calls: list[str] = []
        rc, _out, sid, steps, _w = _step(
            calls, [(1, GONE, ""), (0, "done", "new-session")]
        )
        assert calls == ["158a6d1a-29cc-408f-9787-551d67865578", ""], (
            "the retry must drop the session, not repeat it"
        )
        assert rc == 0, "a resumable-session problem became a failed generation"
        assert sid == "new-session"
        assert steps[-1]["outcome"] == "ok"

    def test_the_fallback_is_recorded(self) -> None:
        """A silent retry hides that continuity was lost."""
        _rc, _out, _sid, steps, warnings = _step(
            [], [(1, GONE, ""), (0, "done", "new-session")]
        )
        assert steps[-1]["details"]["resume_unavailable"] is True
        assert any(w["code"] == "resume_session_unavailable" for w in warnings)

    def test_a_real_failure_is_not_retried(self) -> None:
        """Retrying every failure would double the spend and mask the cause."""
        calls: list[str] = []
        rc, _out, _sid, steps, warnings = _step(
            calls, [(1, "Error: rate limit exceeded", ""), (0, "done", "x")]
        )
        assert len(calls) == 1, "a rate limit is not a lost session"
        assert rc == 1
        assert steps[-1]["outcome"] == "failed"
        assert any(w["code"] == "claude_step_failed" for w in warnings)

    def test_a_lost_session_that_fails_again_still_fails(self) -> None:
        calls: list[str] = []
        rc, _out, _sid, steps, _w = _step(
            calls, [(1, GONE, ""), (1, "Error: model unavailable", "")]
        )
        assert len(calls) == 2
        assert rc == 1, "the retry failed on its own merits and must be reported"
        assert steps[-1]["outcome"] == "failed"

    def test_nothing_changes_when_no_session_was_requested(self) -> None:
        calls: list[str] = []
        steps: list[dict] = []
        warnings: list[dict] = []

        def fake(prompt, *, config, resume_session=""):
            calls.append(resume_session)
            return (1, GONE, "")

        with patch("medharness.services.cr_generation._run_llm", side_effect=fake):
            rc, _o, _s = _run_claude_step(
                name="run_initial_generation", prompt="p", steps=steps,
                warnings=warnings, critical=True,
            )
        assert len(calls) == 1, "there was no session to drop"
        assert rc == 1


@pytest.mark.skipif(
    not __import__("shutil").which("claude"), reason="claude CLI not installed"
)
def test_the_cli_still_says_what_the_detector_matches() -> None:
    """The detector reads a message another tool owns, so check it is still that.

    A reworded error would turn the fallback off silently and the failure would
    come back as `tool_error`.
    """
    import subprocess

    result = subprocess.run(
        ["claude", "-p", "say ok", "--resume",
         "00000000-0000-0000-0000-000000000000", "--output-format", "json"],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode != 0
    assert _resume_unavailable(result.stdout + result.stderr), (
        f"the CLI no longer says what the detector matches: "
        f"{(result.stdout + result.stderr)[:200]!r}"
    )
