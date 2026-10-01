"""Helpers for tests that run on the scaffolded starter DHF."""

from __future__ import annotations

from pathlib import Path


def keep_the_starter_text(dhf: Path) -> None:
    """Opt a project out of the placeholder check, as a project may in `global.yaml`.

    The starter items say "Replace with your own", which `verify dhf --strict` and
    `build release` rightly refuse. A test of something else — a release's
    mechanics, say — runs on them anyway.
    """
    global_yaml = dhf / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text() + "\nplaceholder_patterns: []\n", encoding="utf-8")
