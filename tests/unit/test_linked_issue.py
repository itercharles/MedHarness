"""`issue_number` in the event output, and why it is sometimes absent.

The reference project's workflow ran `automation github-event --github-output`
and then a second `enrich` step that re-read the same fields with
`jq -r '.cr_id // ""'` purely so it could add `issue_number` from a `gh api`
call. That re-read is where a failed parse became an empty `cr_id` flowing to
seven downstream jobs, each silently skipping — a green run that did nothing.

Emitting `issue_number` removes the reason that step exists.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from medharness.services.github_event import (
    GitHubEventContext,
    GitHubLifecyclePlan,
    _linked_issue,
    parse_github_event,
)


class TestOnlyAClosingKeywordLinksAnIssue:
    """A bare `#12` is a reference, not a link.

    Reporting it would name an issue the pull request does not close, which is
    worse than reporting nothing — a caller would act on it.
    """

    @pytest.mark.parametrize("body,expected", [
        ("Closes #42", 42),
        ("closes: #7", 7),
        ("Fixes #13", 13),
        ("fixed #3", 3),
        ("Resolves #21", 21),
        ("resolved #9", 9),
        ("Work on the toolbar.\n\nCloses #88\n", 88),
    ])
    def test_a_closing_keyword_links(self, body: str, expected: int) -> None:
        assert _linked_issue(body) == expected

    @pytest.mark.parametrize("body", [
        "see #99 for background",
        "related to #4",
        "#12",
        "Closes https://github.com/o/r/issues/5",   # URL form, not derivable here
        "",
    ])
    def test_anything_else_does_not(self, body: str) -> None:
        assert _linked_issue(body) is None


class TestItReachesTheOutput:
    def _event(self, tmp_path: Path, body: str) -> Path:
        p = tmp_path / "event.json"
        p.write_text(json.dumps({
            "pull_request": {"number": 117, "body": body,
                             "head": {"ref": "feat/CR-013"},
                             "labels": [], "merged": False},
            "action": "opened",
        }))
        return p

    def _run(self, event: Path, out: Path) -> tuple[dict, list[str]]:
        proc = subprocess.run(
            [sys.executable, "-m", "medharness", "automation", "github-event",
             "--event", str(event), "--github-output", str(out)],
            capture_output=True, text=True,
            env={**os.environ, "GITHUB_EVENT_NAME": "pull_request"},
        )
        assert "Traceback" not in proc.stderr, proc.stderr[-400:]
        payload = json.loads(proc.stdout.splitlines()[0])
        written = out.read_text().splitlines() if out.exists() else []
        return payload, written

    def test_a_linked_issue_reaches_json_and_github_output(self, tmp_path: Path) -> None:
        payload, written = self._run(
            self._event(tmp_path, "Toolbar work.\n\nCloses #88"), tmp_path / "out.txt"
        )
        assert payload["issue_number"] == 88
        assert "issue_number=88" in written

    def test_no_link_writes_nothing_rather_than_empty(self, tmp_path: Path) -> None:
        """An empty value is what the caller's `// ""` fallback turned into a
        silent skip. Absent is honest; empty is a value that looks real."""
        payload, written = self._run(
            self._event(tmp_path, "See #99 for background."), tmp_path / "out.txt"
        )
        assert payload["issue_number"] is None
        assert not any(l.startswith("issue_number") for l in written)

    def test_the_comment_path_reads_the_pull_request_body(self, tmp_path: Path) -> None:
        """On issue_comment, GitHub puts the PR body under `issue`."""
        p = tmp_path / "e.json"
        p.write_text(json.dumps({
            "issue": {"number": 117, "body": "Closes #55",
                      "title": "CR-013 toolbar", "pull_request": {}, "labels": []},
            "comment": {"body": "/approve"},
        }))
        proc = subprocess.run(
            [sys.executable, "-m", "medharness", "automation", "github-event",
             "--event", str(p)],
            capture_output=True, text=True,
            env={**os.environ, "GITHUB_EVENT_NAME": "issue_comment"},
        )
        assert json.loads(proc.stdout.splitlines()[0])["issue_number"] == 55


class TestEveryConstructionCarriesIt:
    """Two plan constructors exist and one was missed on the first pass.

    The field reached the parser, the CLI read `plan.issue_number`, and the
    early-return plan still defaulted to None — so it worked when called
    directly and returned nothing through the CLI. A field threaded by hand
    through fifteen constructors needs a check that counts them.
    """

    def _source(self) -> ast.Module:
        path = Path(__file__).resolve().parents[2] / "medharness" / "services" / "github_event.py"
        return ast.parse(path.read_text())

    @pytest.mark.parametrize("cls", ["GitHubEventContext", "GitHubLifecyclePlan"])
    def test_no_construction_omits_issue_number(self, cls: str) -> None:
        missing = [
            node.lineno
            for node in ast.walk(self._source())
            if isinstance(node, ast.Call)
            and getattr(node.func, "id", "") == cls
            and "issue_number" not in {k.arg for k in node.keywords}
        ]
        assert not missing, (
            f"{cls} built without issue_number at line(s) {missing} — it will "
            f"default to None and the field will vanish on that path"
        )

    def test_the_field_is_declared_on_both(self) -> None:
        for cls in (GitHubEventContext, GitHubLifecyclePlan):
            assert "issue_number" in cls.__dataclass_fields__

    def test_the_cli_emits_every_context_field_it_can(self) -> None:
        """A field added to the dataclass but not to --github-output is invisible."""
        path = Path(__file__).resolve().parents[2] / "medharness" / "cli" / "ci.py"
        text = path.read_text()
        assert '"issue_number"' in text, "issue_number is not in the --github-output key list"
