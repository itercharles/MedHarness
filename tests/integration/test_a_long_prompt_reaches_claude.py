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
