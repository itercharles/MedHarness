"""Failures that used to look like nothing happening.

Two of them, found by sweeping for `except ...: pass` and `continue` sites and
asking one question of each: does swallowing this make a failure indistinguishable
from success?

Most of the twenty-two such sites are honest best-effort work. These two were
not — each produced output a caller reads as "checked, and fine".
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from medharness.services.github_event import parse_github_event, read_event


class TestAnUnreadableEventPayloadIsNotANoOp:
    """`{}` and a malformed payload parsed to byte-identical output.

    A corrupted GITHUB_EVENT_PATH gave `cr_id=None, mode="skip"`, exit 0 — the
    same as an event with genuinely nothing to do. Every downstream job skipped
    and the run was green, which in a compliance pipeline is the worst outcome:
    not a red build, but a green one that checked nothing.
    """

    def test_a_malformed_payload_raises(self, tmp_path: pathlib.Path) -> None:
        broken = tmp_path / "event.json"
        broken.write_text('{"pull_request": {"number": 1, "head"')
        with pytest.raises(ValueError, match="could not be read"):
            read_event(broken, environ={})

    def test_a_legitimate_no_op_still_parses(self, tmp_path: pathlib.Path) -> None:
        """The distinction only means something if the other side still works."""
        ok = tmp_path / "event.json"
        ok.write_text(json.dumps({"action": "labeled", "label": {"name": "other"}}))
        event, _ = read_event(ok, environ={})
        context = parse_github_event(event, "label")
        assert context.cr_id is None and context.mode == "skip"

    def test_an_absent_payload_is_still_tolerated(self, tmp_path: pathlib.Path) -> None:
        """Absent is not corrupt: a manual run has no event file at all."""
        assert read_event(tmp_path / "nothing.json", environ={}) == ({}, "")


    def test_an_unset_event_path_is_absent_not_unreadable(self) -> None:
        """`Path("")` is `Path(".")`, and a directory passes `exists()`.

        Reporting unreadable payloads made this visible: a manual run with no
        GITHUB_EVENT_PATH tried to read the working directory and raised
        IsADirectoryError, which the old swallow had hidden. Absent has to be
        recognised as absent.
        """
        env = {"GITHUB_EVENT_NAME": "workflow_dispatch"}
        assert read_event(environ=env) == ({}, "workflow_dispatch")

    def test_a_path_that_is_a_directory_is_not_read(self, tmp_path) -> None:
        env = {"GITHUB_EVENT_PATH": str(tmp_path), "GITHUB_EVENT_NAME": "workflow_dispatch"}
        assert read_event(environ=env) == ({}, "workflow_dispatch")

    def test_the_cli_reports_it_within_the_contract(self, tmp_path: pathlib.Path) -> None:
        """exit 1, nothing on stdout, no traceback — docs/interface.md's
        'usage error raised before the command ran'."""
        broken = tmp_path / "event.json"
        broken.write_text("{not json")
        proc = subprocess.run(
            [sys.executable, "-m", "medharness", "workflow", "github-event",
             "--event", str(broken)],
            capture_output=True, text=True,
            env={**os.environ, "GITHUB_EVENT_NAME": "pull_request"},
        )
        assert proc.returncode == 1
        assert not proc.stdout.strip()
        assert "Traceback" not in proc.stderr
        assert "could not be read" in proc.stderr
