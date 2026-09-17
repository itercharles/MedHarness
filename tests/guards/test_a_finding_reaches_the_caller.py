"""Every finding a gate prints must be in what it returns.

`verify soup` rendered two findings to stderr and returned `warnings: []`. A
caller reading the JSON saw a clean run while the log showed two warnings. The
gate returns from three places and only one of them assembled the messages.

That was invisible while a structured copy sat under `details` — the information
existed, just not where a caller looks. `details` is no longer emitted, so the
messages are the whole answer and a gap in them is a gap.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from medharness.services.ci import ENVELOPE_KEYS

ROOT = Path(__file__).resolve().parents[2]

#: Every gate, and arguments enough to reach its reporting path.
GATES = {
    "verify dhf": [],
    "verify tests": ["--junit-dir", "{dhf}/test-results"],
    "verify soup": ["--offline-mode", "warn"],
    "workflow branch": ["--cr", "CR-001"],
    "verify completion": ["--cr", "CR-001"],
}

#: stderr lines that report a finding. PASS records what held, not what failed.
FINDING = re.compile(r"^\s*(FAIL|WARN)\b\s*(\[[^\]]*\])?\s*(?P<body>.+)$")


@pytest.fixture(scope="module")
def dhf(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("dhf")
    subprocess.run([sys.executable, "-c", "from medharness.cli import main; main()", "init"],
                   cwd=root, capture_output=True, check=False)
    path = root / "DHF"
    if not (path / "config" / "global.yaml").exists():
        pytest.skip("scaffold unavailable")
    # A cycle, so at least one gate has something to report.
    crs = path / "items" / "01_crs" / "CRS-001.yaml"
    crs.write_text(
        crs.read_text().replace("derives_from:\n  - UC-001",
                                "derives_from:\n  - UC-001\n  - SYS-001"),
        encoding="utf-8",
    )
    return path


def _run(command: str, dhf: Path):
    args = [a.format(dhf=dhf) for a in GATES[command]]
    proc = subprocess.run(
        [sys.executable, "-m", "medharness", "--dhf", str(dhf), *command.split(), *args],
        capture_output=True, text=True, cwd=ROOT,
    )
    lines = proc.stdout.splitlines()
    assert lines, f"{command} wrote no JSON:\n{proc.stderr[-400:]}"
    return json.loads(lines[0]), proc.stderr


@pytest.mark.parametrize("command", sorted(GATES), ids=lambda c: c)
def test_stdout_is_the_envelope_and_nothing_else(command: str, dhf: Path) -> None:
    payload, _ = _run(command, dhf)
    assert set(payload) == set(ENVELOPE_KEYS), (
        f"{command} emits {sorted(set(payload) ^ set(ENVELOPE_KEYS))} beyond the envelope"
    )


@pytest.mark.parametrize("command", sorted(GATES), ids=lambda c: c)
def test_every_finding_in_the_log_is_in_the_answer(command: str, dhf: Path) -> None:
    payload, stderr = _run(command, dhf)
    answered = " || ".join(payload["errors"] + payload["warnings"])

    for line in stderr.splitlines():
        match = FINDING.match(line)
        if not match:
            continue
        body = match.group("body").strip()
        # Compare on the first clause: the log prefixes a tag and may append a
        # fix hint, but the substance has to be there.
        core = re.split(r" — | \(fix| \. ", body)[0].strip()[:40]
        assert core and core in answered, (
            f"{command} printed a finding a caller never receives:\n"
            f"  log:    {line.strip()}\n"
            f"  answer: {payload['errors'] + payload['warnings']}"
        )


@pytest.mark.parametrize("command", sorted(GATES), ids=lambda c: c)
def test_a_failing_gate_says_what_failed(command: str, dhf: Path) -> None:
    payload, _ = _run(command, dhf)
    if payload["passed"]:
        pytest.skip(f"{command} passes on this DHF")
    assert payload["errors"], (
        f"{command} failed with an empty `errors` — nothing for a caller to act on"
    )


def test_the_scan_saw_findings(dhf: Path) -> None:
    """All of the above pass trivially if no gate reports anything."""
    total = 0
    for command in GATES:
        payload, _ = _run(command, dhf)
        total += len(payload["errors"]) + len(payload["warnings"])
    assert total >= 3, f"only {total} findings across every gate — the fixture is too clean"


def test_soup_reports_what_it_could_not_check(dhf: Path) -> None:
    """Pins the content, not just the agreement between the two channels.

    Consistency alone cannot see a finding dropped from both at once: `soup_gate`
    returns from three places, and silencing the one this DHF takes removed the
    warning from the log and the answer together.
    """
    payload, _ = _run("verify soup", dhf)
    assert any("SOUP-001" in w for w in payload["warnings"]), (
        f"the starter SOUP item has no ecosystem and is in no manifest; the gate "
        f"reported neither: {payload['warnings']}"
    )
