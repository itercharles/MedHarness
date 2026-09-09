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

from medharness.services.github_event import parse_github_event
from medharness.workflows import upgrade as U


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
            parse_github_event(broken)

    def test_a_legitimate_no_op_still_parses(self, tmp_path: pathlib.Path) -> None:
        """The distinction only means something if the other side still works."""
        ok = tmp_path / "event.json"
        ok.write_text(json.dumps({"action": "labeled", "label": {"name": "other"}}))
        context = parse_github_event(ok)
        assert context.cr_id is None and context.mode == "skip"

    def test_an_absent_payload_is_still_tolerated(self, tmp_path: pathlib.Path) -> None:
        """Absent is not corrupt: a manual run has no event file at all."""
        context = parse_github_event(tmp_path / "nothing.json", manual_cr_id="CR-001")
        assert context.cr_id == "CR-001"


    def test_an_unset_event_path_is_absent_not_unreadable(self, monkeypatch) -> None:
        """`Path("")` is `Path(".")`, and a directory passes `exists()`.

        Reporting unreadable payloads made this visible: a manual run with no
        GITHUB_EVENT_PATH tried to read the working directory and raised
        IsADirectoryError, which the old swallow had hidden. Absent has to be
        recognised as absent.
        """
        monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
        monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
        context = parse_github_event(manual_cr_id="CR-001")
        assert context.cr_id == "CR-001"

    def test_a_path_that_is_a_directory_is_not_read(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(tmp_path))
        monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
        context = parse_github_event(manual_cr_id="CR-002")
        assert context.cr_id == "CR-002"

    def test_the_cli_reports_it_within_the_contract(self, tmp_path: pathlib.Path) -> None:
        """exit 1, nothing on stdout, no traceback — docs/interface.md's
        'usage error raised before the command ran'."""
        broken = tmp_path / "event.json"
        broken.write_text("{not json")
        proc = subprocess.run(
            [sys.executable, "-m", "medharness", "automation", "github-event",
             "--event", str(broken)],
            capture_output=True, text=True,
            env={**os.environ, "GITHUB_EVENT_NAME": "pull_request"},
        )
        assert proc.returncode == 1
        assert not proc.stdout.strip()
        assert "Traceback" not in proc.stderr
        assert "could not be read" in proc.stderr


class TestAnUnreadableTemplateIsAccountedFor:
    """A template that exists but cannot be read fell out of every bucket.

    `check_upgrade` sorts files into up_to_date / outdated / missing /
    unavailable. A missing template was reported; an unreadable one two lines
    later was skipped, so it appeared in none of them and the summary counted a
    smaller total while still saying everything was current.
    """

    @pytest.fixture
    def project(self, tmp_path: pathlib.Path) -> pathlib.Path:
        from medharness.workflows.init import _replace_placeholders, _scaffold_dhf
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Unreadable")
        return tmp_path

    @pytest.fixture
    def unreadable_template(self):
        target = U._TEMPLATES_DIR / "config" / "doc_types" / "apr.yaml"
        mode = target.stat().st_mode
        os.chmod(target, 0o000)
        try:
            yield target
        finally:
            os.chmod(target, mode)

    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads anything")
    def test_it_is_reported_as_unavailable(self, project, unreadable_template) -> None:
        report = U.check_upgrade(project)
        files = {u["file"] for u in report["unavailable"]}
        assert any("apr.yaml" in f for f in files), (
            f"the unreadable template vanished from the report: {report['unavailable']}"
        )

    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads anything")
    def test_apply_keeps_the_warning_in_its_summary(self, project, unreadable_template) -> None:
        """`apply_upgrade` rewrites the summary, and dropped this line.

        The count and the entries survived in the payload; the one line a person
        reads said "Applied 0 update(s). 27 already current." — which is true,
        and reads as nothing being wrong.
        """
        (project / "DHF" / "config" / "doc_types" / "apr.yaml").unlink()
        report = U.apply_upgrade(project)
        assert any("apr.yaml" in u["file"] for u in report["unavailable"])
        assert "this build cannot manage them" in report["summary"], report["summary"]

    def test_a_healthy_install_reports_neither(self, project) -> None:
        report = U.apply_upgrade(project)
        assert not report.get("failed")
        assert "could not be written" not in report["summary"]
