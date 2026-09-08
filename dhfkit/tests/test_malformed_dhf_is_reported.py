"""A DHF that cannot be read must produce a message, not a traceback.

A mistyped field in a hand-edited item is the likeliest mistake a DHF user
makes. It used to raise ValidationError out of nine of thirteen commands as a
traceback — including `verify dhf`, whose whole purpose is reporting exactly
that kind of problem, and `dhfkit validate schema` was the only command that
handled it.

Every command is checked, not a chosen few: the defect was that most of them
had never been run against a broken DHF at all.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

#: Every command that reads DHF items, with the arguments it needs to get there.
COMMANDS = [
    ("medharness", ["verify", "dhf"]),
    ("medharness", ["verify", "tests", "--junit-dir", "{dhf}/test-results"]),
    ("medharness", ["verify", "classification"]),
    ("medharness", ["verify", "plans"]),
    ("medharness", ["verify", "verification"]),
    ("medharness", ["verify", "completion", "--cr", "CR-001"]),
    ("medharness", ["verify", "soup", "--offline-mode", "warn"]),
    ("dhfkit", ["validate", "schema"]),
    ("dhfkit", ["validate", "traceability"]),
    ("dhfkit", ["report"]),
    ("dhfkit", ["sbom"]),
    ("dhfkit", ["item", "list"]),
    ("dhfkit", ["release-baseline", "--version", "1.0", "--out-dir", "{tmp}/out"]),
]


@pytest.fixture(scope="module")
def broken(tmp_path_factory) -> Path:
    """A DHF with one mistyped field — otherwise a clean scaffold."""
    root = tmp_path_factory.mktemp("broken")
    _scaffold_dhf(root)
    _replace_placeholders(root, "Broken")
    risk = next((root / "DHF" / "items").rglob("RISK-*.yaml"))
    risk.write_text(risk.read_text() + "typo_field: oops\n")
    return root


def _run(module: str, args: list[str], root: Path) -> subprocess.CompletedProcess:
    dhf = root / "DHF"
    resolved = [a.format(dhf=dhf, tmp=root) for a in args]
    return subprocess.run(
        [sys.executable, "-m", module, "--dhf", str(dhf), *resolved],
        capture_output=True, text=True, cwd=str(root),
    )


@pytest.mark.parametrize("module,args", COMMANDS,
                         ids=[f"{m} {' '.join(a[:2])}" for m, a in COMMANDS])
def test_no_command_shows_a_traceback(module: str, args: list[str], broken: Path) -> None:
    proc = _run(module, args, broken)
    assert "Traceback" not in proc.stderr, (
        f"{module} {' '.join(args)} crashed instead of reporting:\n{proc.stderr[-500:]}"
    )


@pytest.mark.parametrize("module,args", COMMANDS,
                         ids=[f"{m} {' '.join(a[:2])}" for m, a in COMMANDS])
def test_a_read_failure_names_the_file_and_the_field(
    module: str, args: list[str], broken: Path
) -> None:
    """A reader has to know which item to fix.

    Only commands that actually reached the item are checked. Some fail
    earlier for their own reasons — `verify tests` has no JUnit evidence, and
    `verify classification` is inert without a declared class — and those are
    correct outcomes, not misses.
    """
    proc = _run(module, args, broken)
    combined = proc.stderr + proc.stdout
    if "could not be read" not in combined:
        pytest.skip("this command did not reach the broken item")
    assert "RISK-001" in combined, f"the failing item is not named:\n{combined[-400:]}"
    assert "typo_field" in combined, f"the offending field is not named:\n{combined[-400:]}"


def test_the_fixture_actually_reaches_most_commands(broken: Path) -> None:
    """Otherwise every check above could pass by never getting there."""
    reached = [
        f"{m} {args[0]}" for m, args in COMMANDS
        if "could not be read" in (lambda p: p.stderr + p.stdout)(_run(m, args, broken))
    ]
    assert len(reached) >= 8, f"only {len(reached)} commands read the DHF: {reached}"


class TestAMissingDHFIsAlsoAMessage:
    def test_pointing_at_a_directory_that_is_not_a_dhf(self, tmp_path: Path) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "dhfkit", "--dhf", str(tmp_path / "nope"),
             "item", "list"],
            capture_output=True, text=True,
        )
        assert "Traceback" not in proc.stderr, proc.stderr[-400:]
        assert proc.returncode != 0
        assert "could not be read" in proc.stderr


class TestAHealthyDHFIsUnaffected:
    def test_commands_still_work(self, tmp_path: Path) -> None:
        from dhfkit.cli import main as dhfkit_main

        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Fine")
        r = CliRunner().invoke(dhfkit_main, ["--dhf", str(tmp_path / "DHF"), "item", "list"])
        assert r.exit_code == 0, r.output
