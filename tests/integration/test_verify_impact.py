"""`verify impact`: the CR's record of its impact, judged on whatever is on the machine.

`build plan` makes this judgement before it finishes; a coding agent that wrote the record itself had no
command that made it, and handed in a design `verify dhf` and `verify changes` passed and `build plan` would
have refused (an anchor neither changed nor reviewed).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf

REVIEWED = ["CRS-001", "SRS-001", "SYSARCH-001", "RCM-001"]
DIMENSIONS = ("product", "requirements", "architecture", "risk", "soup", "test", "regulatory", "security", "usability")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _edit(repo: Path, name: str, **fields) -> None:
    path = next((repo / "DHF" / "items").rglob(name))
    data = yaml.safe_load(path.read_text())
    data.update(fields)
    path.write_text(yaml.safe_dump(data))


def _analysis(**overrides) -> dict:
    record = {
        "assumptions": ["the request means what it says"],
        "anchors": [{"id": "SYS-001", "evidence": "named in the request"}],
        "unchanged": [{"id": uid, "reason": "still holds"} for uid in REVIEWED],
        "created": [],
        "dimensions": [{"dimension": d, "verdict": "not_required", "reason": "no effect", "items": []}
                       for d in DIMENSIONS],
    }
    return {**record, **overrides}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """SYS-001 changed, the CR settling everything it reaches."""
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Impact")
    keep_the_starter_text(tmp_path / "DHF")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feat")
    _edit(tmp_path, "SYS-001.yaml", content="Changed requirement.")
    _edit(tmp_path, "CR-001.yaml", affected_items=["SYS-001"], reviewed_items=REVIEWED,
          affected_risk_items=["RCM-001", "RISK-001"], impact_analysis=_analysis())
    return tmp_path


def _run(repo: Path, *args: str):
    result = CliRunner().invoke(main, ["--dhf", str(repo / "DHF"), *args])
    assert "Traceback" not in (result.stderr or "")
    return result, json.loads(result.stdout.splitlines()[0])


def _impact(repo: Path, cr: str = "CR-001", *extra: str):
    return _run(repo, "verify", "impact", "--cr", cr, "--since-ref", "main", *extra)


def test_a_record_that_settles_what_the_branch_reaches_passes(repo: Path) -> None:
    result, answer = _impact(repo)
    assert result.exit_code == 0 and answer["passed"] is True, answer["errors"]


def test_a_cr_with_no_impact_analysis_fails_naming_what_is_missing(repo: Path) -> None:
    path = next((repo / "DHF" / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(path.read_text())
    del data["impact_analysis"]
    path.write_text(yaml.safe_dump(data))
    result, answer = _impact(repo)
    assert result.exit_code == 1
    assert any(e.startswith("impact_analysis") for e in answer["errors"]), answer["errors"]


def test_an_anchor_nobody_settled_fails(repo: Path) -> None:
    """The record `verify dhf` and `verify changes` both passed, and `build plan` refused."""
    _edit(repo, "CR-001.yaml", impact_analysis=_analysis(
        anchors=[{"id": "SYS-001", "evidence": "x"}, {"id": "UC-001", "evidence": "named in the request"}]))
    result, answer = _impact(repo)
    assert result.exit_code == 1
    assert any("anchor UC-001 is neither changed nor in `reviewed_items`" in e for e in answer["errors"])


def test_a_dependent_of_a_changed_item_nobody_reviewed_fails(repo: Path) -> None:
    _edit(repo, "CR-001.yaml", reviewed_items=["CRS-001", "SRS-001", "SYSARCH-001"])
    result, answer = _impact(repo)
    assert result.exit_code == 1
    assert any(e.startswith("impact.RCM-001") for e in answer["errors"]), answer["errors"]


def test_a_cr_triage_rejected_is_not_checked(repo: Path) -> None:
    path = next((repo / "DHF" / "items").rglob("CR-001.yaml"))
    data = yaml.safe_load(path.read_text())
    del data["impact_analysis"]
    data["triage_result"] = {"verdict": "rejected", "notes": "duplicate"}
    path.write_text(yaml.safe_dump(data))
    result, answer = _impact(repo)
    assert result.exit_code == 0, answer["errors"]


def test_a_cr_that_is_not_in_the_dhf_is_named(repo: Path) -> None:
    result, answer = _impact(repo, "CR-099")
    assert result.exit_code == 1 and answer["errors"][0].startswith("cr_item:")


def test_a_ref_that_cannot_be_reached_is_not_an_empty_diff(repo: Path) -> None:
    result, answer = _run(repo, "verify", "impact", "--cr", "CR-001", "--since-ref", "origin/nowhere")
    assert result.exit_code == 1 and answer["errors"][0].startswith("diff_unavailable:")


def test_verify_changes_no_longer_judges_impact(repo: Path) -> None:
    _edit(repo, "CR-001.yaml", reviewed_items=[])
    result, answer = _run(repo, "verify", "changes", "--cr", "CR-001", "--since-ref", "main")
    assert result.exit_code == 0, answer["errors"]
