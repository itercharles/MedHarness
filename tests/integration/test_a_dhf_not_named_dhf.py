"""`--dhf` names the DHF directory; nothing may assume it is called `DHF`.

The branch diff looked under `DHF/items/` whatever `--dhf` said, so with the DHF in `Records/`
`verify changes` reported every promised item as unchanged, and the prompts told the agent to
run its commands against a directory that does not exist.
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


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def records(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Records")
    (tmp_path / "DHF").rename(tmp_path / "Records")
    keep_the_starter_text(tmp_path / "Records")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feat")
    return tmp_path / "Records"


def _edit(dhf: Path, name: str, **fields) -> None:
    path = next((dhf / "items").rglob(name))
    data = yaml.safe_load(path.read_text())
    data.update(fields)
    path.write_text(yaml.safe_dump(data))


def test_verify_changes_reads_the_items_of_the_dhf_it_is_given(records: Path) -> None:
    _edit(records, "SRS-001.yaml", content="Changed.")
    _edit(records, "CR-001.yaml", affected_items=["SRS-001"], reviewed_items=["SWDD-001"])

    result = CliRunner().invoke(main, ["--dhf", str(records), "verify", "changes", "--cr", "CR-001",
                                       "--since-ref", "main"])
    errors = json.loads(result.stdout.splitlines()[0])["errors"]
    assert not [e for e in errors if "does not change" in e or "not change them" in e], errors


def test_the_prompts_name_the_dhf_directory_in_use(records: Path) -> None:
    _edit(records, "CR-001.yaml", implementation_notes="Plan.")
    for stage in ("plan", "code"):
        out = CliRunner().invoke(main, ["--dhf", str(records), "build", stage, "--cr", "CR-001", "--prompt"]).stdout
        assert "--dhf Records" in out and "--dhf DHF" not in out, stage
