"""Every case of the shipped validation set passes, traced to the point it exercises.

`build validation` runs these cases on a user's machine. Running them here as tests puts each
point in the JUnit that `verify tests --strict` holds to MedHarness's own DHF and that the
release attaches, so a user's report and the vendor's run name the same cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dhfkit.store import open_store
from dhfkit.testing_points import parse_testing_points
from medharness.validation import CASES
from medharness.validation.case import Case, run_cases

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("case", [
    pytest.param(c, id=c.name, marks=[pytest.mark.dhf_links(c.requirement), pytest.mark.dhf_testing(*c.points)])
    for c in CASES
])
def test_the_case_passes(case: Case, tmp_path: Path) -> None:
    (outcome,) = run_cases([case], tmp_path)
    if outcome.status == "not_run":
        pytest.skip(outcome.message)
    assert outcome.status == "passed", outcome.message


def test_every_case_exercises_a_high_risk_point_of_the_dhf() -> None:
    high = {item["id"]: set(parse_testing_points(item.get("testing")))
            for item in open_store(ROOT / "DHF").list_items("SRS") if item.get("risk") == "high"}
    strays = [f"{c.name}: {c.requirement} {p}" for c in CASES for p in c.points
              if p not in high.get(c.requirement, set())]
    assert not strays, f"cases name points the high-risk requirements do not have: {strays}"


def test_case_names_are_unique() -> None:
    names = [c.name for c in CASES]
    assert len(names) == len(set(names))
