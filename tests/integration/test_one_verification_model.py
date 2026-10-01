"""`verify tests`, `verify completion` and the release report agree on what a test verifies.

Three things read JUnit three ways. A requirement verified by Inspection failed
`verify tests` for having no test, so the only way through was a fake link; a test tagged
only in its name (`@links:SYS-001`) counted as coverage in one place and as no evidence in
another; and a link to an ID the DHF does not have was accepted without a word.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text

from medharness.cli import main
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Verify")
    keep_the_starter_text(tmp_path / "DHF")
    for name, methods in (("CRS-001.yaml", ["Test"]), ("SYS-001.yaml", ["Test"]), ("SRS-001.yaml", ["Test"])):
        _set(tmp_path / "DHF", name, verification_method=methods, verification_criteria="c")
    return tmp_path / "DHF"


def _set(dhf: Path, name: str, **fields) -> None:
    path = next((dhf / "items").rglob(name))
    data = yaml.safe_load(path.read_text())
    data.update(fields)
    path.write_text(yaml.safe_dump(data))


def _junit(tmp_path: Path, *cases: tuple[str, str | None, bool]) -> Path:
    """(name, medharness.links value or None, failed)."""
    xml = ["<testsuite>"]
    for name, links, failed in cases:
        props = f'<properties><property name="medharness.links" value="{links}"/></properties>' if links else ""
        failure = '<failure message="x"/>' if failed else ""
        xml.append(f'<testcase name="{name}" classname="c">{props}{failure}</testcase>')
    xml.append("</testsuite>")
    path = tmp_path / "r.xml"
    path.write_text("".join(xml))
    return path


def _tests(dhf: Path, junit: Path, *flags: str):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "tests", "--junit", str(junit), *flags])
    return result, json.loads(result.stdout.splitlines()[0])


def test_a_requirement_verified_by_inspection_needs_no_test(dhf: Path, tmp_path: Path) -> None:
    _set(dhf, "SRS-001.yaml", verification_method=["Inspection"])
    result, answer = _tests(dhf, _junit(tmp_path, ("t", "CRS-001,SYS-001", False)))
    assert result.exit_code == 0, answer["errors"]
    assert any("SRS-001: verified by Inspection" in w for w in answer["warnings"]), answer["warnings"]


def test_a_requirement_that_declares_a_test_still_needs_one(dhf: Path, tmp_path: Path) -> None:
    result, answer = _tests(dhf, _junit(tmp_path, ("t", "CRS-001,SYS-001", False)))
    assert result.exit_code == 1 and any(e.startswith("SRS:") for e in answer["errors"]), answer["errors"]


def test_a_failing_test_is_not_evidence(dhf: Path, tmp_path: Path) -> None:
    result, _ = _tests(dhf, _junit(tmp_path, ("t", "CRS-001,SYS-001,SRS-001", True)))
    assert result.exit_code == 1


def test_a_name_tag_counts_everywhere(dhf: Path, tmp_path: Path) -> None:
    junit = _junit(tmp_path, ("test_all @links:CRS-001 @links:SYS-001 @links:SRS-001", None, False))
    result, answer = _tests(dhf, junit)
    assert result.exit_code == 0, answer["errors"]
    assert not any("declares Test but no passing case" in e for e in answer["errors"])


def test_the_closure_gate_reads_name_tags_too(dhf: Path, tmp_path: Path) -> None:
    cr = next((dhf / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(cr.read_text())
    data.update({"implementation_notes": "n", "affected_risk_items": [], "triage_result": {"verdict": "approved"},
                 "affected_items": ["SYS-001"]})
    cr.write_text(yaml.safe_dump(data))
    junit = _junit(tmp_path, ("test_it @links:SYS-001", None, False))
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "completion", "--cr", "CR-001", "--junit", str(junit)])
    assert result.exit_code == 0, result.stdout


def test_a_link_to_an_id_the_dhf_does_not_have_warns_and_fails_under_strict(dhf: Path, tmp_path: Path) -> None:
    junit = _junit(tmp_path, ("test_gone", "CRS-001,SYS-001,SRS-001,SRS-999", False))
    loose, loose_answer = _tests(dhf, junit)
    strict, strict_answer = _tests(dhf, junit, "--strict")
    assert loose.exit_code == 0
    assert any("SRS-999: linked by 'test_gone' but not in the DHF" in w for w in loose_answer["warnings"])
    assert strict.exit_code == 1
    assert any("SRS-999: linked by 'test_gone'" in e for e in strict_answer["errors"])
