"""A fix a gate suggests must be runnable, and must fix the thing.

The closure gate once told a reader to run `medharness approval act`. No such
command existed — the `approval` group had gone and the message kept the name.
That check is itself gone now (approval lives in the pull request, so
`workflow check-approval` owns it), but the failure mode is not specific to it:
any gate can print a hint that names a command nobody can run.

`test_no_source_names_a_dead_command` matches full command lines, not a bare
name quoted inside prose, which is why it missed the original.

Checked end to end rather than by existence: the hint is extracted from the
gate's own stderr, run verbatim, and the gate re-run. A hint that parses but
does not resolve the finding is no better than a wrong one.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: `Fix:` lines carry a runnable command. The hint spells the real --dhf path,
#: not a literal, so it is copy-pasteable as printed.
HINT = re.compile(r"Fix:\s*(dhfkit --dhf \S+ .*?\}')")


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    subprocess.run([sys.executable, "-c", "from medharness.cli import main; main()", "init"],
                   cwd=tmp_path, capture_output=True, check=False)
    path = tmp_path / "DHF"
    if not (path / "config" / "global.yaml").exists():
        pytest.skip("scaffold unavailable")
    return path


def _verify_dhf(dhf: Path) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "medharness", "--dhf", str(dhf), "verify", "dhf"],
        capture_output=True, text=True, cwd=ROOT,
    )
    return proc.stderr


class TestTheHintIsUsable:
    def test_the_gate_offers_a_fix_at_all(self, dhf: Path) -> None:
        """The premise. Without a hint on the starter DHF this proves nothing."""
        assert HINT.search(_verify_dhf(dhf)), (
            "verify dhf printed no runnable Fix: line on a fresh scaffold"
        )

    def test_running_the_hint_verbatim_clears_the_finding(self, dhf: Path) -> None:
        before = _verify_dhf(dhf)
        match = HINT.search(before)
        assert match, before[-400:]

        args = shlex.split(match.group(1))
        assert args[0] == "dhfkit" and args[1] == "--dhf"
        assert Path(args[2]) == dhf, (
            f"the hint names {args[2]}, not the DHF it was run against — a "
            f"reader pasting it would edit the wrong tree"
        )
        # The item the hint names, so the assertion below is about that one.
        item_id = args[args.index("update") + 1]

        result = subprocess.run(
            [sys.executable, "-m", "dhfkit", *args[1:]],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0, (
            f"the suggested command failed:\n{result.stderr[-400:]}"
        )

        after = _verify_dhf(dhf)
        assert item_id not in after or "verification_criteria is empty" not in after, (
            f"the fix ran but the gate still reports {item_id}:\n{after[-400:]}"
        )
