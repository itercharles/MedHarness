"""No command may answer a bad invocation with a traceback.

`medharness dhf context overview` without `--dhf` reached pathlib with `None`
and raised `TypeError: expected str, bytes or os.PathLike object, not
NoneType`. Three sibling commands wrote the check by hand; this one did not, so
the fix belongs in the shared helper rather than in a fourth copy.

**Every invocation runs in a throwaway directory.** The first version of this
file ran them in the repository root, and `medharness init` — a command like
any other to a walk of the command tree — scaffolded a DHF over the checkout
and substituted the placeholders inside `dhfkit/templates/` itself. A test that
walks a CLI is running arbitrary commands; the cwd is not incidental.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _leaf_commands(module: str, prefix: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    out = subprocess.run(
        [sys.executable, "-m", module, *prefix, "--help"],
        capture_output=True, text=True,
    ).stdout
    if "Commands:" not in out:
        return [prefix]
    section = out.split("Commands:", 1)[1]
    subs = [m.group(1) for m in re.finditer(r"^  ([a-z][a-z-]+)", section, re.M)]
    return [leaf for s in subs for leaf in _leaf_commands(module, prefix + (s,))]


LEAVES = [(m, path) for m in ("dhfkit", "medharness") for path in _leaf_commands(m)]


def test_the_walk_found_the_cli() -> None:
    """A walk that resolved nothing would make every case below vacuous."""
    assert len(LEAVES) >= 25, f"only {len(LEAVES)} leaf commands found"


@pytest.mark.parametrize("module,path", LEAVES,
                         ids=[f"{m} {' '.join(p)}" for m, p in LEAVES])
def test_a_bare_invocation_does_not_traceback(
    module: str, path: tuple[str, ...], tmp_path: Path
) -> None:
    """Run it with no arguments — the rudest thing a user can do.

    `cwd=tmp_path`, never the checkout: some of these commands write files.
    """
    proc = subprocess.run(
        [sys.executable, "-m", module, *path],
        capture_output=True, text=True, cwd=str(tmp_path),
        env={**__import__("os").environ, "COMPLIANTFLOW_DHF": ""},
    )
    assert "Traceback" not in proc.stderr, (
        f"{module} {' '.join(path)} crashed on a bare invocation:\n"
        f"{proc.stderr[-400:]}"
    )


def test_the_walk_does_not_touch_the_checkout(tmp_path: Path) -> None:
    """The failure this file caused once: init scaffolded over the repo.

    Runs the one command that writes the most, in a temp directory, and checks
    the checkout is untouched.
    """
    before = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(ROOT)
    ).stdout
    subprocess.run(
        [sys.executable, "-m", "medharness", "init"],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    after = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(ROOT)
    ).stdout
    assert after == before, f"running init changed the checkout:\n{after}"


class TestTheHelperIsWhereTheCheckLives:
    def test_a_none_dhf_is_rejected_cleanly(self) -> None:
        import click

        from medharness._helpers import _make_adapter

        with pytest.raises(click.ClickException) as excinfo:
            _make_adapter(None)
        assert "--dhf is required" in str(excinfo.value)
