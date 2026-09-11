"""Every command shown in the docs must exist.

Documentation drift has been the recurring fault in this repo: a CLI table that
omitted the whole gate surface, a `soup-sources.yaml` example that could never
run, an interface document whose sample manifest had superseded wording. Each
was found by someone reading, not by anything checking.

This closes the simplest half — a command that no longer exists — for every
command line in README.md and docs/.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Options that take a value, so the token after them is not a subcommand.
VALUE_FLAGS = {
    "--dhf", "--out-dir", "--junit-dir", "--cr", "--version", "--manifest",
    "--output", "--approver", "--reviews-dir", "--project-dir", "--type",
    "--requirement-type", "--since-ref", "--code-path", "--offline-mode",
    "--coverage-pair", "--junit", "--doc-format", "--data", "--author", "--stage",
}


def _documented_calls() -> list[tuple[str, tuple[str, ...], str]]:
    found: dict[tuple[str, tuple[str, ...]], str] = {}
    sources = sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]
    for path in sources:
        for raw in path.read_text(encoding="utf-8").splitlines():
            # A command in a table cell or inline prose is documented just as
            # loudly as one on its own line, and was invisible here until the
            # README moved its command reference into a table — taking twelve
            # commands out of this guard's reach without failing anything.
            for candidate in [raw] + re.findall(r"`([^`]+)`", raw):
                for line in _alternatives(candidate.replace(r"\|", "|")):
                    call = _parse(line)
                    if call:
                        found.setdefault(call, path.name)
    return [(mod, toks, src) for (mod, toks), src in sorted(found.items())]


def _alternatives(line: str) -> list[str]:
    """`change plan|implement` documents two commands, not one."""
    match = re.search(r"\b(\w+(?:\|\w+)+)", line)
    if not match:
        return [line]
    return [line.replace(match.group(1), alt) for alt in match.group(1).split("|")]


def _parse(line: str) -> tuple[str, tuple[str, ...]] | None:
    match = re.match(r"^(dhfkit|medharness)\s+(.+)$", line.strip().lstrip("$").strip())
    if not match:
        return None
    tokens, skip = [], False
    for arg in match.group(2).split():
        if skip:
            skip = False
            continue
        if arg in VALUE_FLAGS:
            skip = True
            continue
        # "..." stands in for arguments the prose is not spelling out.
        if arg.startswith(("-", "<", "|", "#")) or set(arg) == {"."}:
            continue
        tokens.append(arg)
    return (match.group(1), tuple(tokens[:2])) if tokens else None


CALLS = _documented_calls()


def test_the_docs_actually_show_commands() -> None:
    """A scan finding nothing would make every case below vacuous."""
    assert len(CALLS) >= 20, f"only {len(CALLS)} documented commands found"


@pytest.mark.parametrize(
    "module,tokens,source", CALLS,
    ids=[f"{m} {' '.join(t)}" for m, t, _s in CALLS],
)
def test_a_documented_command_exists(
    module: str, tokens: tuple[str, ...], source: str
) -> None:
    result = subprocess.run(
        [sys.executable, "-m", module, *tokens, "--help"],
        capture_output=True, text=True,
    )
    output = result.stderr + result.stdout
    assert "No such command" not in output, (
        f"{source} documents `{module} {' '.join(tokens)}`, which does not exist"
    )
    assert "Got unexpected extra argument" not in output, (
        f"{source} documents `{module} {' '.join(tokens)}`, but "
        f"`{tokens[0]}` takes no subcommand"
    )


def test_readme_pins_the_current_version() -> None:
    """The README's copy-paste CI snippet names a real, current version.

    docs/adopting.md uses a `{{medharness_version}}` placeholder, which cannot
    go stale. The README shows a concrete version so the snippet runs as pasted,
    and that one does — silently, on every release, telling new users to install
    whatever was current when the line was last touched.
    """
    pinned = re.search(r"pip install medharness==([\d.]+)", (ROOT / "README.md").read_text())
    assert pinned, "the README no longer shows a pinned install"
    current = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)
    assert pinned.group(1) == current.group(1), (
        f"README pins medharness=={pinned.group(1)} but pyproject.toml is at "
        f"{current.group(1)} — update the README in the release PR"
    )
