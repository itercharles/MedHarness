"""CI names its test paths one by one, so a new directory runs nowhere.

`pytest tests/unit/ tests/integration/ tests/contract/ dhfkit/tests/` is four
literals in a workflow file. Adding a directory without editing that file gives
a green build that never opened it — the failure looks exactly like success.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-pipeline.yml"


def _directories_holding_tests() -> set[str]:
    found = set()
    for path in list(ROOT.glob("tests/**/test_*.py")) + list(ROOT.glob("dhfkit/tests/**/test_*.py")):
        found.add(str(path.parent.relative_to(ROOT)))
    return found


def test_the_scan_found_directories() -> None:
    dirs = _directories_holding_tests()
    assert len(dirs) >= 4, f"only found {dirs} — the scan is broken"


def test_ci_runs_every_directory_that_holds_tests() -> None:
    invoked = " ".join(re.findall(r"pytest\s+([^\n]*)", WORKFLOW.read_text()))
    unrun = sorted(d for d in _directories_holding_tests() if d not in invoked)
    assert not unrun, (
        "these directories hold tests that CI never runs:\n  "
        + "\n  ".join(unrun)
        + f"\n\nAdd them to a pytest invocation in {WORKFLOW.name}."
    )
