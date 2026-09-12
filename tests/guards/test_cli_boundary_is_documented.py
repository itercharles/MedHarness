"""CLAUDE.md's CLI table is what an agent reads before touching this repo.

It listed six dhfkit commands and described medharness in prose. By the time
anyone noticed, `dhfkit init` and `sbom` and `medharness automation`, `doctor`,
`init`, `upgrade` and `verify` were all missing from it — including `verify`,
the entire gate surface.

A stale instruction file is worse than a thin one: it is read as current.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _live_commands(module: str) -> set[str]:
    out = subprocess.run(
        [sys.executable, "-m", module, "--help"], capture_output=True, text=True,
    ).stdout
    section = out.split("Commands:", 1)[-1]
    return {m.group(1) for m in re.finditer(r"^  ([a-z][a-z-]+)", section, re.M)}


@pytest.fixture(scope="module")
def claude_md() -> str:
    return (ROOT / "CLAUDE.md").read_text()


@pytest.mark.parametrize("module", ["dhfkit", "medharness"])
def test_every_command_is_in_the_table(module: str, claude_md: str) -> None:
    live = _live_commands(module)
    assert live, f"{module} exposed no commands — the probe is broken"
    table = claude_md.split("| CLI | Owns", 1)[1].split("\n\n", 1)[0]
    missing = sorted(c for c in live if f"`{c}`" not in table)
    assert not missing, (
        f"{module} has commands the CLAUDE.md table does not list: {missing}"
    )


@pytest.mark.parametrize("module", ["dhfkit", "medharness"])
def test_the_table_lists_no_command_that_does_not_exist(
    module: str, claude_md: str
) -> None:
    """A stale entry points an agent at a command that is gone."""
    table = claude_md.split("| CLI | Owns", 1)[1].split("\n\n", 1)[0]
    row = next(r for r in table.splitlines() if f"`{module}`" in r)
    listed = set(re.findall(r"`([a-z][a-z-]+)`", row)) - {module}
    orphaned = sorted(listed - _live_commands(module))
    assert not orphaned, f"the table lists {orphaned}, which {module} does not have"


