"""A DHF file that will not load is named, never crashed on, never dropped.

Three ways this failed, each worse than the last:

- A config file that was not valid YAML, or not a mapping, or had a field of the
  wrong type, raised straight out of the loader. Every gate answered with a
  traceback and nothing on stdout.
- An item file in the same state was caught by a bare `except Exception` that
  `print`ed to **stdout** — so the first line of a gate's answer was
  `Error loading …` rather than the envelope — and returned None.
- That None was then dropped. The item left every coverage denominator it
  belonged to: a broken SRS turned `1/3 covered` into `1/2`, and a gate whose
  remaining rows were green would have passed.

`test_no_command_tracebacks` walks bad *invocations* against a good DHF, so it
never saw any of this. These are good invocations against a bad DHF.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

ROOT = Path(__file__).resolve().parents[2]

#: Every command that loads the DHF, with arguments enough to get that far.
COMMANDS = [
    "verify dhf",
    "verify tests --junit-dir {dhf}/none",
    "verify soup --offline-mode warn",
    "verify completion --cr CR-001",
    "workflow check-changes --cr CR-001",
    "context",
]


def _first_srs(dhf: Path) -> Path:
    return next((dhf / "items").rglob("SRS-*.yaml"))


def _first_doc_type(dhf: Path) -> Path:
    """A project override of a default type — the file a project would edit."""
    return dhf / "config" / "doc_types" / "srs.yaml"


#: name -> (which file, what to write). Each is a mistake a hand edit makes.
FAULTS = {
    "global.yaml is not YAML": (lambda d: d / "config" / "global.yaml", "not: yaml: [\n"),
    "global.yaml is a list": (lambda d: d / "config" / "global.yaml", "- a\n- b\n"),
    "a doc type is not YAML": (_first_doc_type, "not: yaml: [\n"),
    "an item is not YAML": (_first_srs, "not: yaml: [\n"),
    "an item is a list": (_first_srs, "- x\n"),
    # `workflow check-changes` caught FileNotFoundError and skipped the promise
    # check, so a CR that broke its promise passed once the config was gone.
    "global.yaml is missing": (lambda d: d / "config" / "global.yaml", None),
}


def _commit_with_origin_main(root: Path) -> None:
    """So `workflow check-changes` gets past the diff and reaches the DHF."""
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "base"],
                 ["update-ref", "refs/remotes/origin/main", "HEAD"]):
        subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)


@pytest.fixture
def broken(request, tmp_path: Path) -> tuple[Path, Path]:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Broken")
    _commit_with_origin_main(tmp_path)
    dhf = tmp_path / "DHF"
    locate, content = FAULTS[request.param]
    target = locate(dhf)
    if content is None:
        target.unlink()
    else:
        target.parent.mkdir(exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return dhf, target


def _run(command: str, dhf: Path) -> subprocess.CompletedProcess:
    args = command.format(dhf=dhf).split()
    return subprocess.run(
        [sys.executable, "-m", "medharness", "--dhf", str(dhf), *args],
        capture_output=True, text=True, cwd=ROOT,
    )


@pytest.mark.parametrize("broken", sorted(FAULTS), indirect=True)
@pytest.mark.parametrize("command", COMMANDS)
def test_the_command_names_the_file_and_stops(command: str, broken) -> None:
    dhf, target = broken
    proc = _run(command, dhf)

    assert "Traceback" not in proc.stderr, (
        f"`{command}` crashed on {target.name}:\n{proc.stderr[-600:]}"
    )
    assert proc.returncode == 1, (
        f"`{command}` exited {proc.returncode} on a DHF it could not read"
    )
    if command == "verify dhf" and target.parent.parent.name == "items":
        # A malformed item is exactly what `verify dhf` exists to report, so it
        # answers — a failing envelope naming the file — rather than stopping.
        result = json.loads(proc.stdout.splitlines()[0])
        assert result["passed"] is False
        assert any(target.name in e for e in result["errors"]), result["errors"]
        return
    # interface.md: exit 1 with nothing on stdout means the gate never ran. A
    # stray line there breaks every caller that parses the first line as JSON.
    assert proc.stdout == "", (
        f"`{command}` wrote to stdout while failing to read {target.name}: "
        f"{proc.stdout[:200]!r}"
    )
    assert target.name in proc.stderr, (
        f"`{command}` did not say which file it could not read:\n{proc.stderr[-400:]}"
    )


def test_a_broken_item_does_not_leave_the_denominator(tmp_path: Path) -> None:
    """The quiet case, pinned by what it cost rather than by how it looked.

    Before, `verify tests` still produced an answer — a smaller one. Asserting
    the command stops is what rules that out; this names why it matters.
    """
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Shrink")
    dhf = tmp_path / "DHF"
    _first_srs(dhf).write_text("- x\n", encoding="utf-8")

    proc = _run("verify tests --junit-dir {dhf}/none", dhf)
    answered = [line for line in proc.stdout.splitlines() if line.startswith("{")]
    assert not answered, (
        f"verify tests answered without SRS-001 in it: "
        f"{json.loads(answered[0])['summary']}"
    )


@pytest.mark.parametrize("broken", ["an item is not YAML", "an item is a list"], indirect=True)
def test_the_schema_validator_reports_it_as_a_finding(broken) -> None:
    """`dhfkit validate schema` exists to report a bad item, so it answers.

    The loader's error is only half of what it runs: the duplicate-ID scan
    re-reads every file afterwards, and it assumed each one was a mapping.
    """
    dhf, target = broken
    proc = subprocess.run(
        [sys.executable, "-m", "dhfkit", "--dhf", str(dhf), "validate", "schema"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert "Traceback" not in proc.stderr, proc.stderr[-600:]
    result = json.loads(proc.stdout.splitlines()[-1])
    assert result["valid"] is False
    assert any(target.name in e for e in result["errors"]), result["errors"]
