"""A step the model is told to run is listed once.

Merging `validate schema` into `verify dhf` left three instructions that said
`medharness --dhf DHF verify dhf` twice in a row: in the plan prompt and in two
fix prompts built in `cr_generation.py`. Each read as two different checks.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMMAND = re.compile(r"medharness(?: --dhf \S+)? (?:item|verify|build)\b[^\"'`\\]*")
FILES = sorted((ROOT / "medharness" / "prompts").glob("*.md")) + sorted((ROOT / "medharness").rglob("*.py"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_command_is_listed_twice_in_a_row(path: Path) -> None:
    previous = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = COMMAND.search(line)
        current = match.group(0).strip() if match else None
        assert not (current and current == previous), (
            f"{path.relative_to(ROOT)}:{number} repeats `{current}` on the line above"
        )
        previous = current
