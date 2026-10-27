"""Seeded omissions: how many of the ways a change request can leave something out the gates stop.

The charter's first measure. One honest change request passes every pre-merge gate; each case
leaves one thing out of it, the way an agent might. A case is stopped when any gate exits non-zero.
Omissions the gates do not stop today are `xfail(strict=True)` with the charter gap they belong to,
so the summary line (passed, xfailed) is the catch rate, and closing a gap turns its cases into
failures until they are moved to the stopped side.

The project and the omissions are `medharness.validation.seeded`, which `build validation` runs
too; the stopped omissions are traced to their requirements there.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from medharness.validation import seeded


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    seeded.honest_change(tmp_path)
    return tmp_path


def test_the_honest_change_passes_every_gate(repo: Path) -> None:
    """The control: without it, a case 'stopped' by a fixture the gates reject anyway would count as caught."""
    assert seeded.stopped_by(repo) == {}


def _missed(gap: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{gap}: {why}")


OMISSIONS: list = [
    *(pytest.param(omit, gate) for omit, gate, _, _ in seeded.STOPPED),
    pytest.param(seeded.changed_requirement_lost_its_test, "verify tests"),
    pytest.param(seeded.old_test_point_kept, None, marks=_missed("warning", "test_points_unchanged warns, it does not stop")),
    pytest.param(seeded.new_hazard_not_recorded, None, marks=_missed("G2", "a hazard linked to nothing has no way in")),
    pytest.param(seeded.verifying_test_weakened, None, marks=_missed("adequacy", "a passing test is taken at its word")),
]


@pytest.mark.parametrize(("omit", "gate"), OMISSIONS, ids=[p.values[0].__name__ for p in OMISSIONS])
def test_a_seeded_omission_is_stopped(repo: Path, omit: Callable[[Path], None], gate: str | None) -> None:
    """Stopped by the gate whose job it is, not by a side effect of the seeding; a known miss by any gate at all."""
    omit(repo)
    stopped = seeded.stopped_by(repo)
    assert stopped, f"{omit.__name__} passed every gate: {omit.__doc__}"
    assert gate is None or gate in stopped, f"{omit.__name__} was stopped by {sorted(stopped)}, not {gate}"
