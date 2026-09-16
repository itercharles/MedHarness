"""A fix a gate suggests must be runnable, and must fix the thing.

The closure gate told a reader to run `medharness approval act`. No such command
exists — the `approval` group went when its one gate moved under `change`, and
the message kept naming it. A developer working by hand, without the AI, was
sent to a command that does not exist and away from the one that works.

`test_no_source_names_a_dead_command` missed it: that guard matches full command
lines (`python -m medharness …`), not a bare name quoted inside prose.

Checked end to end rather than by existence — the hint is extracted from the
gate's own error, run verbatim, and the gate re-run. A hint that parses but does
not resolve the finding is no better than a wrong one.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    subprocess.run([sys.executable, "-c", "from medharness.cli import main; main()", "init"],
                   cwd=tmp_path, capture_output=True, check=False)
    path = tmp_path / "DHF"
    if not (path / "config" / "global.yaml").exists():
        pytest.skip("scaffold unavailable")
    _dhfkit(path, "item", "create", "--type", "SRS", "--data", json.dumps({
        "title": "Hand written req", "derives_from": ["SYS-001"],
        "verification_method": ["Inspection"], "verification_criteria": "c",
    }))
    _dhfkit(path, "item", "update", "CR-001", "--data", json.dumps({
        "implementation_notes": "by hand", "affected_risk_items": [],
        "triage_result": {"verdict": "approved"},
        "proposed_new_items": [{"type": "SRS", "title": "Hand written req"}],
        "affected_items": ["SRS-002"],
    }))
    return path


def _dhfkit(dhf: Path, *args: str):
    return subprocess.run(
        [sys.executable, "-m", "dhfkit", "--dhf", str(dhf), *args],
        capture_output=True, text=True, cwd=ROOT,
    )


def _closure(dhf: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "medharness", "--dhf", str(dhf),
         "change", "verify-completion", "--cr", "CR-001"],
        capture_output=True, text=True, cwd=ROOT,
    )
    return json.loads(proc.stdout.splitlines()[0])


def _approval_error(payload: dict) -> str:
    return next(e for e in payload["errors"] if "no approval record" in e)


class TestTheHintIsUsable:
    def test_the_gate_asks_for_an_approval_on_a_hand_written_cr(self, dhf: Path) -> None:
        """The premise: a CR made by hand, no git, no AI, still needs a record."""
        assert _approval_error(_closure(dhf)), "nothing to fix — this test proves nothing"

    def test_running_the_hint_verbatim_clears_the_finding(self, dhf: Path) -> None:
        """The whole point: do what it says, and the gate stops saying it."""
        hint = _approval_error(_closure(dhf))
        match = re.search(r"(dhfkit --dhf DHF item create.*?\}')", hint)
        assert match, f"no runnable command found in the hint: {hint}"

        args = shlex.split(match.group(1))
        assert args[:3] == ["dhfkit", "--dhf", "DHF"]
        result = _dhfkit(dhf, *args[3:])
        assert result.returncode == 0, (
            f"the suggested command failed:\n{result.stderr[-400:]}"
        )

        after = _closure(dhf)
        assert not any("no approval record" in e for e in after["errors"]), (
            f"the fix ran but the gate still reports it: {after['errors']}"
        )
