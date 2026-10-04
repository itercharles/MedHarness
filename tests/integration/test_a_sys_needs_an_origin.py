"""A system requirement comes from a customer need or exists to implement a risk control.

Nothing was required upstream of a SYS, so `SYS-002` with no CRS and no RCM passed
`verify dhf --strict`. The default rule is `SYS satisfies a CRS, or is covered by an
RCM`; it is a rule in `global.yaml` like the others, so a project changes or drops it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Origin")
    keep_the_starter_text(tmp_path / "DHF")
    return tmp_path / "DHF"


def _file(dhf: Path, name: str) -> Path:
    return next((dhf / "items").rglob(name))


def _new(dhf: Path, template: str, uid: str, **fields) -> None:
    source = _file(dhf, template)
    data = yaml.safe_load(source.read_text())
    data.update({"id": uid, "title": uid, "content": "c", **fields})
    (source.parent / f"{uid}.yaml").write_text(yaml.safe_dump(data))


def _verify(dhf: Path):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"])
    return result, json.loads(result.stdout.splitlines()[0])


def _sys_errors(answer: dict) -> list[str]:
    return [e for e in answer["errors"] if e.startswith("SYS-002")]


def test_a_sys_with_no_origin_fails(dhf: Path) -> None:
    _new(dhf, "SYS-001.yaml", "SYS-002", satisfies=[])
    result, answer = _verify(dhf)
    assert result.exit_code == 1
    assert _sys_errors(answer) == ["SYS-002: SYS satisfies → CRS (count=0, need ≥1), or covered by RCM"]


def test_a_sys_that_satisfies_a_crs_passes(dhf: Path) -> None:
    _new(dhf, "SYS-001.yaml", "SYS-002", satisfies=["CRS-001"])
    _, answer = _verify(dhf)
    assert _sys_errors(answer) == []


def test_a_sys_that_implements_a_risk_control_passes_without_a_crs(dhf: Path) -> None:
    _new(dhf, "SYS-001.yaml", "SYS-002", satisfies=[])
    _new(dhf, "RCM-001.yaml", "RCM-002", mitigates=["RISK-001"], implements=["SYS-002"])
    _, answer = _verify(dhf)
    assert _sys_errors(answer) == []


def _set_rules(dhf: Path, rules: str) -> None:
    global_yaml = dhf / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text() + "\n" + rules)


def test_a_project_can_require_a_crs_always(dhf: Path) -> None:
    _set_rules(dhf, """required_traceability:
- source_type: SYS
  direction: upstream
  field: satisfies
  target_type: CRS
  min_count: 1
""")
    _new(dhf, "SYS-001.yaml", "SYS-002", satisfies=[])
    _new(dhf, "RCM-001.yaml", "RCM-002", mitigates=["RISK-001"], implements=["SYS-002"])
    _, answer = _verify(dhf)
    assert _sys_errors(answer) == ["SYS-002: SYS satisfies → CRS (count=0, need ≥1)"]


def test_a_project_can_drop_the_rule(dhf: Path) -> None:
    _set_rules(dhf, "required_traceability: []\n")
    _new(dhf, "SYS-001.yaml", "SYS-002", satisfies=[])
    result, answer = _verify(dhf)
    assert result.exit_code == 0 and _sys_errors(answer) == []
