"""What we ship must not require branch protection to be off.

The scaffold's release job ran `git push origin HEAD:main` with `GITHUB_TOKEN`.
On any repository whose default branch requires a pull request — the normal
configuration for a controlled repo, and the one this tool exists to support —
that fails:

    remote: error: GH006: Protected branch update failed for refs/heads/main.

A tool premised on design control cannot ship a workflow that only runs where
design control is switched off. Pushing a *branch* is never blocked, so the
record reaches main through a pull request like every other DHF change.

The same file also carried `A || B && C`, which bash groups as `(A || B) && C`:
with nothing staged the commit was skipped and the push ran anyway.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]

SHIPPED = sorted(ROOT.glob("dhfkit/templates/**/*.yml")) + [ROOT / "docs" / "adopting.md"]

#: `git push <remote> HEAD:main`, `git push origin main`, and the ref-spec forms.
_PUSH_TO_DEFAULT = re.compile(
    r"git\s+push\b[^\n|;&]*?\b(?:HEAD:(?:refs/heads/)?(?:main|master)"
    r"|(?:origin|\$\w+)\s+(?:main|master)\b)"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_scan_reads_the_shipped_files() -> None:
    assert len(SHIPPED) >= 2, f"only {len(SHIPPED)} files found — the scan is broken"
    assert any("dhf.yml" in p.name for p in SHIPPED)


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.name)
def test_nothing_pushes_to_the_default_branch(path: Path) -> None:
    hits = _PUSH_TO_DEFAULT.findall(_text(path))
    assert not hits, (
        f"{path.relative_to(ROOT)} pushes straight to the default branch "
        f"({hits}). A repo that requires a pull request there — which a "
        f"controlled repo does — fails this with GH006. Push a branch and "
        f"open a pull request instead."
    )


def test_the_detector_would_catch_the_form_that_shipped() -> None:
    """The regex reads text nothing else checks; prove it matches the real line."""
    assert _PUSH_TO_DEFAULT.search("            git push origin HEAD:main")
    assert _PUSH_TO_DEFAULT.search("git push origin main")
    assert _PUSH_TO_DEFAULT.search("git push origin HEAD:refs/heads/main")
    assert not _PUSH_TO_DEFAULT.search('git push origin "$BRANCH"')
    assert not _PUSH_TO_DEFAULT.search("git push origin chore/release-baseline-1.0.0")


class TestTheReleaseJobCanDoWhatItNeeds:
    @pytest.fixture(scope="class")
    def job(self) -> dict:
        wf = yaml.safe_load(_text(ROOT / "dhfkit/templates/github/workflows/dhf.yml"))
        return wf["jobs"]["release-baseline"]

    def test_it_may_open_a_pull_request(self, job: dict) -> None:
        assert job["permissions"].get("pull-requests") == "write", (
            "the job opens a PR; without this permission gh pr create is refused"
        )

    def test_the_commit_is_conditional_on_there_being_one(self, job: dict) -> None:
        """`A || B && C` groups as `(A || B) && C` — nothing staged, push anyway."""
        script = "\n".join(
            str(step.get("run", "")) for step in job["steps"]
        )
        assert "|| \\" not in script, (
            "the chained form is back; use an explicit `if ! git diff --cached "
            "--quiet; then ... fi` so an empty change set pushes nothing"
        )
        assert "if git diff --cached --quiet; then" in script
