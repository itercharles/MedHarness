"""CLAUDE.md's CLI table is what an agent reads before touching this repo.

It once listed six dhfkit commands and described medharness in prose, and by the
time anyone noticed, whole groups — `verify`, the entire gate surface — were
missing from it. A stale instruction file is worse than a thin one: it is read
as current.
"""

from __future__ import annotations

import re
from pathlib import Path

import click

from medharness.cli import main

ROOT = Path(__file__).resolve().parents[2]


def _table() -> dict[str, set[str]]:
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    table = text.split("| Group | Touches", 1)[1].split("\n\n", 1)[0]
    rows = {}
    for line in table.splitlines()[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows[cells[0].strip("`")] = set(re.findall(r"`([a-z][a-z-]*)`", cells[2]))
    return rows


def _live() -> dict[str, set[str]]:
    return {name: set(cmd.commands) if isinstance(cmd, click.Group) else set()
            for name, cmd in main.commands.items()}


def test_the_table_matches_the_command_tree() -> None:
    table, live = _table(), _live()
    assert live, "the CLI exposed no commands — the probe is broken"
    assert table == live, f"CLAUDE.md lists {table}; the CLI has {live}"
