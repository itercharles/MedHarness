"""Option values more than one command reads the same way."""

from __future__ import annotations

from pathlib import Path

import click


def collect_junit_paths(junit_files: tuple[Path, ...] = (),
                         junit_dirs: tuple[Path, ...] = ()) -> list[Path]:
    """Collect JUnit XML files from explicit files and directories."""
    collected: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        resolved = str(path.resolve())
        if resolved in seen:
            return
        seen.add(resolved)
        collected.append(path)

    for junit_file in junit_files:
        if not junit_file.exists():
            raise click.ClickException(f"JUnit file '{junit_file}' not found.")
        if not junit_file.is_file():
            raise click.ClickException(f"JUnit path '{junit_file}' is not a file.")
        _add(junit_file)

    for junit_dir in junit_dirs:
        if not junit_dir.exists():
            continue
        if not junit_dir.is_dir():
            raise click.ClickException(f"JUnit path '{junit_dir}' is not a directory.")
        for xml_path in sorted(junit_dir.rglob("*.xml")):
            if xml_path.is_file():
                _add(xml_path)

    return collected
