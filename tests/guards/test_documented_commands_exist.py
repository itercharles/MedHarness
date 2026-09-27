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
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Options that take a value, so the token after them is not a subcommand.
VALUE_FLAGS = {
    "--dhf", "--out-dir", "--junit", "--cr", "--version", "--manifest",
    "--output", "--approver", "--reviews-dir", "--project-dir", "--type",
    "--requirement-type", "--since-ref", "--code-path", "--offline-mode",
    "--coverage-pair", "--junit", "--doc-format", "--data", "--author", "--stage",
    "--project-name", "--event", "--github-output", "--token", "--pr",
}


def _documented_calls() -> list[tuple[str, tuple[str, ...], str]]:
    found: dict[tuple[str, tuple[str, ...]], str] = {}
    # Templates land in every project, and prompts are what the model runs:
    # a dead command in either is one somebody executes. The project README
    # named `dhfkit validate traceability` and `dhfkit report` unchecked.
    sources = (
        sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]
        + sorted((ROOT / "dhfkit" / "templates").rglob("*.md"))
        + sorted((ROOT / "medharness" / "prompts").rglob("*.md"))
    )
    for path in sources:
        for raw in path.read_text(encoding="utf-8").splitlines():
            # A command in a table cell or inline prose is documented just as
            # loudly as one on its own line, and was invisible here until the
            # README moved its command reference into a table — taking twelve
            # commands out of this guard's reach without failing anything.
            # And a command spelled as a Python argument list, which is how the
            # agent example kept calling `medharness gates` after it was removed.
            as_list = [
                " ".join(re.findall(r'"([^"]+)"', m))
                for m in re.findall(r'\[\s*("(?:dhfkit|medharness)"(?:\s*,\s*"[^"]*")+)', raw)
            ]
            for candidate in [raw] + re.findall(r"`([^`]+)`", raw) + as_list:
                for line in _alternatives(candidate.replace(r"\|", "|")):
                    call = _parse(line)
                    if call:
                        found.setdefault(call, path.name)
                        LINES.setdefault(line.strip().lstrip("$").strip(), path.name)
    return [(mod, toks, src) for (mod, toks), src in sorted(found.items())]


#: Every documented command line, whole, for the parse check below.
LINES: dict[str, str] = {}


def _alternatives(line: str) -> list[str]:
    """`build plan|implement` documents two commands, not one."""
    match = re.search(r"\b(\w+(?:\|\w+)+)", line)
    if not match:
        return [line]
    return [line.replace(match.group(1), alt) for alt in match.group(1).split("|")]


def _parse(line: str) -> tuple[str, tuple[str, ...]] | None:
    match = re.match(r"^(dhfkit|medharness)\s+(.+)$", line.strip().lstrip("$").strip())
    if not match:
        return None
    tokens, skip = [], False
    try:
        args = shlex.split(match.group(2))
    except ValueError:              # an unbalanced quote in prose
        args = match.group(2).split()
    for arg in args:
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
    assert len(CALLS) >= 15, f"only {len(CALLS)} documented commands found"


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
    # Positive, not just "no error string": dhfkit's root once raised before
    # Click could say "No such command", and every dhfkit case passed vacuously.
    assert result.returncode == 0 and "Usage:" in output, (
        f"{source} documents `{module} {' '.join(tokens)}`, and "
        f"`{module} {' '.join(tokens)} --help` failed:\n{output[-300:]}"
    )
    assert "No such command" not in output, (
        f"{source} documents `{module} {' '.join(tokens)}`, which does not exist"
    )
    assert "Got unexpected extra argument" not in output, (
        f"{source} documents `{module} {' '.join(tokens)}`, but "
        f"`{tokens[0]}` takes no subcommand"
    )


def _parse_error(line: str) -> str | None:
    """Click's own verdict on the line, or None when it parses.

    `--help` exits 0 before Click looks at the rest, so `medharness verify dhf
    traceability` and `verify tests --dhf DHF` passed the check above while
    failing for everyone who ran them — the second inside the prompt `build
    code` hands its agent.
    """
    import click

    from medharness.cli import main as medharness_main

    module, _, rest = line.partition(" ")
    try:
        args = shlex.split(rest)
    except ValueError:
        args = rest.split()
    args = [a for a in args if a != "\\"]          # a line continued below
    for i, arg in enumerate(args):
        if arg in {"|", "||", "&&", ";", "#", ">", ">>"} or arg.startswith("#"):
            args = args[:i]
            break
    node = medharness_main
    ctx = None
    while True:
        ctx = click.Context(node, parent=ctx, info_name=node.name)
        try:
            _, positional, _ = node.make_parser(ctx).parse_args(list(args))
        except click.UsageError as exc:
            return exc.format_message()
        if not isinstance(node, click.Group):
            allowed = sum(p.nargs if p.nargs > 0 else 99
                          for p in node.params if isinstance(p, click.Argument))
            return f"unexpected {positional[allowed:]}" if len(positional) > allowed else None
        if not positional:
            return None
        args = args[args.index(positional[0]) + 1:]
        node = node.commands.get(positional[0])
        if node is None:
            return f"no command {positional[0]}"


@pytest.mark.parametrize("line", sorted(LINES), ids=lambda l: l[:60])
def test_a_documented_command_line_parses(line: str) -> None:
    error = _parse_error(line)
    assert error is None, f"{LINES[line]} documents `{line}`: {error}"


def test_the_parse_check_catches_both_faults() -> None:
    assert _parse_error("medharness --dhf DHF verify dhf traceability")
    assert _parse_error("medharness verify tests --dhf DHF --junit x")
    assert _parse_error("medharness --dhf DHF verify tests --junit x") is None


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
