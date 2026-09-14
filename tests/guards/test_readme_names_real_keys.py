"""A key the README names must be a key the gate returns.

The `verify dhf` row documented `results.coverage`. There is no such key — the
coverage figures live at `results.traceability.coverage`, and `results` has a
separate `coverage_gaps`. `verify classification` named `safety_class`,
`missing_plans` and `rationale`; the gate returns none of the three. Anyone
building against the table got `None` and no error.

Nothing compared the documented names to the real output, so the tables drifted
the moment either side changed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Gate rows in the README's Commands section, and how to run each one.
#: The arguments only have to reach the gate's reporting path.
GATES = {
    "medharness verify dhf": [],
    "medharness verify tests": ["--junit-dir", "{dhf}/test-results"],
    "medharness verify soup": ["--offline-mode", "warn"],
    "medharness verify classification": [],
    "medharness change verify-branch": ["--cr", "CR-001"],
    "medharness change verify-completion": ["--cr", "CR-001"],
}

#: In this column a backticked span means an output key, so the only things to
#: skip are option flags and literals.
NOT_A_KEY = re.compile(r"^(--|\[\]$|\{)")


@pytest.fixture(scope="module")
def dhf(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("dhf")
    subprocess.run([sys.executable, "-c", "from medharness.cli import main; main()", "init"],
                   cwd=root, capture_output=True, check=False)
    path = root / "DHF"
    if not (path / "config" / "global.yaml").exists():
        pytest.skip("scaffold unavailable")
    return path


def _documented_keys() -> dict[str, list[str]]:
    """Key paths named in each gate's row of the README command tables."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    section = text.split("## Commands", 1)[1].split("\n## ", 1)[0]
    found: dict[str, list[str]] = {}
    for line in section.splitlines():
        if not line.startswith("| `medharness "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        command = cells[0].strip("`").split(" --")[0].strip()
        if command not in GATES:
            continue
        keys = [
            k for k in re.findall(r"`([A-Za-z_][\w.\[\]]*)`", cells[1])
            if not NOT_A_KEY.match(k)
        ]
        found[command] = keys
    return found


DOCUMENTED = _documented_keys()


def test_every_gate_row_was_found() -> None:
    missing = set(GATES) - set(DOCUMENTED)
    assert not missing, (
        f"these gates have no row the scan could read: {sorted(missing)} — the "
        f"parser is broken, so every assertion below passes vacuously"
    )
    assert all(DOCUMENTED.values()), (
        f"a row documented no keys at all: "
        f"{[c for c, k in DOCUMENTED.items() if not k]}"
    )


def _keys_in(obj, prefix: str = "") -> set[str]:
    out: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            out.add(path)
            out |= _keys_in(value, path)
    elif isinstance(obj, list) and obj:
        out |= _keys_in(obj[0], prefix)
    return out


@pytest.mark.parametrize("command", sorted(GATES), ids=lambda c: c)
def test_documented_keys_exist(command: str, dhf: Path) -> None:
    args = [a.format(dhf=dhf) for a in GATES[command]]
    result = subprocess.run(
        [sys.executable, "-m", "medharness", "--dhf", str(dhf),
         *command.removeprefix("medharness ").split(), *args],
        capture_output=True, text=True, cwd=ROOT,
    )
    lines = result.stdout.splitlines()
    assert lines, f"{command} wrote no JSON:\n{result.stderr[-400:]}"
    real = _keys_in(json.loads(lines[0])["details"])

    for documented in DOCUMENTED[command]:
        if "." in documented:
            # A dotted path claims a location, so the whole path must resolve.
            # Accepting its leaf instead is what let `results.coverage` stand
            # for `results.traceability.coverage`.
            ok = documented in real
        else:
            ok = any(k.rsplit(".", 1)[-1] == documented for k in real)
        assert ok, (
            f"the README row for `{command}` names `{documented}`, which the "
            f"gate does not return. Real keys: {sorted(real)[:12]}"
        )
