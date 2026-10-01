"""Text that stands in for content does not pass `verify dhf --strict`, and cannot ship.

The untouched starter DHF — every item titled "Replace with your own" — passed
`verify dhf --strict`, the setting the CI recipe uses, and `build release` shipped it.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


def _project(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Floor")
    return tmp_path / "DHF"


def _verify(dhf: Path, *flags: str):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf", *flags])
    return result, json.loads(result.stdout.splitlines()[0])


def _item(dhf: Path, name: str) -> Path:
    return next((dhf / "items").rglob(name))


def _write(path: Path, **fields) -> None:
    data = yaml.safe_load(path.read_text())
    data.update(fields)
    path.write_text(yaml.safe_dump(data))


def test_the_starter_dhf_warns_and_fails_only_under_strict(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    loose, loose_answer = _verify(dhf)
    strict, strict_answer = _verify(dhf, "--strict")

    assert loose.exit_code == 0 and any("SRS-001: placeholder text in title, content" in w for w in loose_answer["warnings"])
    assert strict.exit_code == 1
    assert any("SRS-001: placeholder text in title, content" in e for e in strict_answer["errors"])
    assert "[placeholder] SRS-001" in strict.stderr


def test_one_finding_per_item_not_per_field(tmp_path: Path) -> None:
    _, answer = _verify(_project(tmp_path))
    mentions = [w for w in answer["warnings"] if w.startswith("SRS-001: placeholder")]
    assert len(mentions) == 1


def test_real_text_clears_the_finding(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    _write(_item(dhf, "SRS-001.yaml"), title="Password length", content="The system rejects passwords under 12 characters.")
    _, answer = _verify(dhf, "--strict")
    assert not any(e.startswith("SRS-001:") for e in answer["errors"])


def test_only_a_whole_placeholder_matches_the_short_patterns(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    path = _item(dhf, "SRS-001.yaml")
    _write(path, title="TBD", content="The TBD in the spec is resolved by SRS-002.")
    _, answer = _verify(dhf)
    finding = next(w for w in answer["warnings"] if w.startswith("SRS-001: placeholder"))
    assert finding.endswith("in title"), finding


def test_a_project_sets_its_own_patterns(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    global_yaml = dhf / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text() + "\nplaceholder_patterns:\n- '^FIXME'\n")
    _write(_item(dhf, "SRS-001.yaml"), title="FIXME name this", content="Real content here.")

    _, answer = _verify(dhf)

    placeholders = [w for w in answer["warnings"] if "placeholder text" in w]
    assert placeholders == ["SRS-001: placeholder text in title"], placeholders


def test_a_project_can_opt_out(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    global_yaml = dhf / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text() + "\nplaceholder_patterns: []\n")
    result, answer = _verify(dhf, "--strict")
    assert result.exit_code == 0 and not any("placeholder" in m for m in answer["errors"] + answer["warnings"])


def test_the_starter_dhf_cannot_be_released(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "release", "--version", "1.0.0",
                                       "--out-dir", str(tmp_path / "rel")])
    report = json.loads(result.stdout.splitlines()[0])
    assert result.exit_code == 1 and any("placeholder text" in e for e in report["errors"])
