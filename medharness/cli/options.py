"""Option values more than one command reads the same way."""

from __future__ import annotations

from pathlib import Path

import click


def junit_option(help_text: str):
    return click.option("--junit", "junit_paths", multiple=True, metavar="PATH",
                        type=click.Path(exists=True, path_type=Path), help=help_text)


def collect_junit_paths(paths: tuple[Path, ...]) -> list[Path]:
    """The JUnit XML files named, and those under each directory named."""
    collected: dict[str, Path] = {}
    for path in paths:
        for xml in [path] if path.is_file() else sorted(path.rglob("*.xml")):
            if xml.is_file():
                collected.setdefault(str(xml.resolve()), xml)
    return list(collected.values())
