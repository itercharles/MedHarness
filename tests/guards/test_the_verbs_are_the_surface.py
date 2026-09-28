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
RETIRED_GROUPS = ("change", "automation", "soup-sync", "upgrade", "context", "doctor", "workflow")

#: old invocation -> what replaced it.
RENAMED = {
    "change verify-completion": "verify completion",
    "change verify-branch": "verify changes",
    "change verify-approval": "GitHub branch protection",
    "change plan": "build plan",
    "change implement": "build code",
    "automation github-event": "the workflow's own `if:`",
    # 0.33.0. Both named the object; the commands ask a question about it.
    "workflow approval": "GitHub branch protection",
    "workflow branch": "verify changes",
    # 0.37.0 folded three context commands into one; 0.39.0 removed it, since
    # the AI stages call services.context directly and nothing ran the command.
    "context overview": "medharness item list",
    "context implementation": "medharness item get",
    "context for-stage": "medharness item get",
    "medharness context": "medharness item list",
    "doc generate": "build release",
    "doc export": "build release",
    "validate schema": "verify dhf",
    # 0.40.0. The name said the whole DHF; it syncs SOUP. Event routing is the
    # CI workflow's own job.
    "build dhf": "build soup",
    "workflow github-event": "the workflow's own `if:`",
    # 0.44.0. One CLI: dhfkit is a library, and its commands moved to where
    # the verbs put them.
    "dhfkit item": "medharness item",
    "dhfkit validate": "medharness verify dhf",
    "dhfkit doc": "medharness build release",
    "dhfkit sbom": "medharness build release",
    # 0.45.0. Documents are what a release ships; a preview is a release
    # without --write.
    "build doc": "build release",
    "dhfkit init": "medharness init",
    # 0.47.0. The diff check runs locally too, so it is a verify; approval is
    # what GitHub's branch protection already enforces.
    "workflow check-changes": "verify changes",
    "workflow check-approval": "GitHub branch protection",
}

#: Stage names from before the verbs, which messages kept after the commands went.
RETIRED_STAGES = ("generate-dhf", "develop-cr", "cr-complete", "soup-sync")

#: What the tools print and what the AI stages are told: messages, help, prompts.
SOURCES = sorted(
    p for root in ("medharness", "dhfkit") for p in (ROOT / root).rglob("*")
    if p.suffix in {".py", ".md", ".j2", ".yaml", ".yml"}
    and "tests" not in p.relative_to(ROOT).parts
)

#: Everything an adopter reads to learn the commands.
DOCS = sorted(
    [ROOT / "README.md", ROOT / "CLAUDE.md"]
    + list((ROOT / "docs").glob("*.md"))
    + list((ROOT / "dhfkit" / "templates").rglob("*.md"))
    + list((ROOT / "dhfkit" / "templates").rglob("*.yml"))
    + list((ROOT / "dhfkit" / "templates").rglob("*.yaml"))
)


def test_the_verbs_exist() -> None:
    """Without this the absence checks below pass on a CLI that failed to load."""
    for verb in ("item", "verify", "build"):
        assert verb in main.commands, f"`{verb}` is not registered"


@pytest.mark.parametrize("name", RETIRED_GROUPS)
def test_a_retired_group_is_not_registered(name: str) -> None:
    assert name not in main.commands, (
        f"`medharness {name}` still resolves; a pipeline on the old name would "
        f"keep passing and never learn it was renamed"
    )


def _resolves(path: list[str]) -> bool:
    """Whether a command path names a command in the CLI's tree."""
    import click

    node = main
    for token in path:
        if not isinstance(node, click.Group) or token not in node.commands:
            return False
        node = node.commands[token]
    return True


@pytest.mark.parametrize("old", sorted(RENAMED), ids=lambda s: s)
def test_a_renamed_command_no_longer_exists(old: str) -> None:
    """By the command tree, not by running it: a group's `--help` can exit 0
    for a subcommand that is gone."""
    assert not _resolves(old.split()), f"`{old}` is still a command"


def test_the_resolver_sees_current_commands() -> None:
    """Otherwise the test above passes on anything."""
    assert _resolves(["verify", "dhf"]) and _resolves(["item", "list"])


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_no_document_teaches_a_retired_name(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    offenders = {
        old: replacement
        for old, replacement in RENAMED.items()
        if re.search(rf"\b{re.escape(old)}\b", text)
    }
    if re.search(r"\bsoup-sync\b", text):
        offenders["soup-sync"] = "build soup"
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


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_message_or_prompt_names_a_retired_command(path: Path) -> None:
    """A gate that says "re-run generate-dhf" sends the reader to a command
    that no longer exists."""
    text = path.read_text(encoding="utf-8")
    found = [
        name for name in [*RENAMED, *RETIRED_STAGES]
        if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text)
    ]
    assert not found, f"{path.relative_to(ROOT)} names {', '.join(found)}"


def test_the_source_scan_read_something() -> None:
    assert any(p.name == "cr_generate_dhf.md" for p in SOURCES)
    assert any(p.name == "verify_completion.py" for p in SOURCES)
