"""The README's command reference must list every command.

It had drifted twice: `medharness verify dhf` appeared on two rows with
different descriptions after a bulk edit replaced `dhfkit validate links` with
it, and eight commands were absent entirely. `test_documented_commands_exist`
checks that what the docs name is real; nothing checked the other direction.
"""

from __future__ import annotations

import re
from pathlib import Path

import click

from dhfkit.cli import main as dhfkit_main
from medharness.cli import main as medharness_main

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"


def _leaves(group: click.Group) -> list[str]:
    found: list[str] = []

    def walk(cmd, path):
        if isinstance(cmd, click.Group):
            for name, sub in sorted(cmd.commands.items()):
                walk(sub, path + [name])
        else:
            found.append(" ".join(path))

    walk(group, [])
    return found


ALL = [("dhfkit", c) for c in _leaves(dhfkit_main)] + [
    ("medharness", c) for c in _leaves(medharness_main)
]


def test_the_scan_found_commands() -> None:
    assert len(ALL) >= 25, f"only {len(ALL)} — the walk is broken"


def _commands_section() -> str:
    """Only the reference section counts.

    Searching the whole README passes on a command named anywhere in prose —
    deleting a row from the table left this guard green, which is how it was
    found.
    """
    text = README.read_text(encoding="utf-8")
    start = text.index("## Commands")
    rest = text[start + len("## Commands"):]
    end = rest.find("\n## ")
    return rest[: end if end != -1 else len(rest)]


def test_every_command_appears_in_the_readme() -> None:
    text = _commands_section()
    # A command may be named on its own row or inline in a neighbour's
    # description — `item get` rides along with `item list`.
    absent = [
        f"{cli} {cmd}"
        for cli, cmd in ALL
        if not re.search(re.escape(cmd).replace(r"\ ", r"[\s`]+"), text)
    ]
    assert not absent, (
        "these commands exist but the README never names them:\n  "
        + "\n  ".join(absent)
    )


def test_no_command_is_given_two_rows() -> None:
    """Two rows for one command means two different descriptions of it."""
    text = README.read_text(encoding="utf-8")
    rows = re.findall(r"^\| `((?:dhfkit|medharness) [^`]+)`", text, re.M)
    heads = [" ".join(r.split()[:3]) for r in rows]
    dupes = sorted({h for h in heads if heads.count(h) > 1})
    assert not dupes, f"listed more than once: {dupes}"
