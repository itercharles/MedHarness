"""`--junit PATH` takes a file or a directory, on every command that reads JUnit."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.cli.options import collect_junit_paths


def test_a_file_and_a_directory_are_both_read_once(tmp_path: Path) -> None:
    results = tmp_path / "results"
    (results / "nested").mkdir(parents=True)
    a = results / "a.xml"
    b = results / "nested" / "b.xml"
    for f in (a, b):
        f.write_text("<testsuites/>")
    (results / "notes.txt").write_text("not junit")

    assert collect_junit_paths((a, results)) == [a, b]


@pytest.mark.parametrize("command", [
    ["verify", "tests"],
    ["verify", "completion", "--cr", "CR-001"],
    ["build", "release", "--version", "1.0.0", "--out-dir", "out"],
])
def test_a_path_that_does_not_exist_is_a_usage_error(command: list[str], tmp_path: Path) -> None:
    """A mistyped results path used to be skipped, and read as "no tests ran"."""
    result = CliRunner().invoke(main, [*command, "--junit", str(tmp_path / "missing")])
    assert result.exit_code == 2
    assert "does not exist" in result.output
