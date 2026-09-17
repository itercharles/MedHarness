"""The old command names are gone, and gone means gone.

`change`, `automation` and `soup-sync` were removed in 0.32.0. A rename that
leaves the old name working is not a rename — an adopter's pipeline keeps
passing, the docs say one thing and the CLI accepts another, and the old name
outlives the release that was supposed to retire it.

So this asserts absence at the CLI, and absence in every file a reader learns
the surface from. Prose about the history belongs in CHANGELOG.md, which is
excluded for exactly that reason.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from medharness.cli import main

ROOT = Path(__file__).resolve().parents[2]

#: Removed top-level groups and commands.
RETIRED_GROUPS = ("change", "automation", "soup-sync")

#: old invocation -> what replaced it.
RENAMED = {
    "change verify-completion": "verify completion",
    "change verify-branch": "workflow branch",
    "change verify-approval": "workflow approval",
    "change plan": "build plan",
    "change implement": "build code",
    "automation github-event": "workflow github-event",
}

#: Everything an adopter reads to learn the commands.
DOCS = sorted(
    [ROOT / "README.md", ROOT / "CLAUDE.md"]
    + list((ROOT / "docs").glob("*.md"))
    + list((ROOT / "dhfkit" / "templates").rglob("*.md"))
    + list((ROOT / "dhfkit" / "templates").rglob("*.yml"))
    + list((ROOT / "dhfkit" / "templates").rglob("*.yaml"))
)


def test_the_three_verbs_exist() -> None:
    """Without this the absence checks below pass on a CLI that failed to load."""
    for verb in ("verify", "build", "workflow"):
        assert verb in main.commands, f"`{verb}` is not registered"


@pytest.mark.parametrize("name", RETIRED_GROUPS)
def test_a_retired_group_is_not_registered(name: str) -> None:
    assert name not in main.commands, (
        f"`medharness {name}` still resolves; a pipeline on the old name would "
        f"keep passing and never learn it was renamed"
    )


@pytest.mark.parametrize("old", sorted(RENAMED), ids=lambda s: s)
def test_a_renamed_command_no_longer_runs(old: str) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "medharness", *old.split(), "--help"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert proc.returncode != 0, f"`medharness {old}` still runs"
    assert "No such command" in proc.stderr + proc.stdout


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_no_document_teaches_a_retired_name(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    offenders = {
        old: replacement
        for old, replacement in RENAMED.items()
        if re.search(rf"\b{re.escape(old)}\b", text)
    }
    if re.search(r"\bsoup-sync\b", text):
        offenders["soup-sync"] = "build dhf"
    assert not offenders, (
        f"{path.relative_to(ROOT)} still teaches: "
        + ", ".join(f"{old} (now {new})" for old, new in sorted(offenders.items()))
    )


def test_the_document_scan_read_something() -> None:
    """All of the above pass trivially on an empty file list."""
    assert len(DOCS) >= 5, f"only {len(DOCS)} documents scanned"
    assert any("verify dhf" in p.read_text(encoding="utf-8") for p in DOCS), (
        "no scanned document mentions a command at all — the glob is wrong"
    )
