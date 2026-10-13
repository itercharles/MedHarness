"""A prompt too long for one argv entry must still reach the `claude` CLI.

Linux caps a single argument at 128 KiB; a prompt carrying the DHF context can be
larger, so it travels on stdin.
"""

from __future__ import annotations

import stat
from pathlib import Path

from medharness.services.llm import _run_claude

FAKE_CLAUDE = """#!/bin/sh
printf '{"result": "%s", "session_id": "s"}' "$(wc -c | tr -d ' ')"
"""


def test_a_prompt_over_the_argument_limit_arrives_whole(tmp_path: Path, monkeypatch) -> None:
    claude = tmp_path / "claude"
    claude.write_text(FAKE_CLAUDE)
    claude.chmod(claude.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")

    rc, output, session = _run_claude("x" * 300_000)

    assert (rc, output, session) == (0, "300000", "s")



def _fake(tmp_path: Path, monkeypatch, body: str) -> None:
    claude = tmp_path / "claude"
    claude.write_text("#!/bin/sh\n" + body)
    claude.chmod(claude.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")


def test_a_model_call_that_hangs_is_stopped(tmp_path: Path, monkeypatch) -> None:
    _fake(tmp_path, monkeypatch, "sleep 30\n")
    monkeypatch.setenv("MEDHARNESS_MODEL_TIMEOUT", "1")

    rc, output, _ = _run_claude("x")

    assert rc == 1 and "did not finish within 1 s" in output


def test_the_agent_does_not_inherit_the_tokens_the_harness_pushes_with(tmp_path: Path, monkeypatch) -> None:
    """The agent has a shell; a review on the PR is text it acts on."""
    _fake(tmp_path, monkeypatch,
          'printf \'{"result": "%s|%s|%s", "session_id": "s"}\' "${GH_TOKEN:-none}" "${GITHUB_TOKEN:-none}" "${ANTHROPIC_API_KEY:-none}"\n')
    monkeypatch.setenv("GH_TOKEN", "gh-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "model-key")

    _, output, _ = _run_claude("x")

    assert output == "none|none|model-key"
