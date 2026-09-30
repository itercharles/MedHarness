"""Every command answers bad input with an exit code and a reason, never a traceback.

These run the real CLI against a scaffolded project. They are the tests that
matter most: a defect in any helper shows up here, as a wrong exit code, a
missing reason, or a file changed when it should not have been. Two were found
by writing them — `--data '[1]'` crashed `item create` and `item update`, and
`build release --version ''` was accepted.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def project(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Edge")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def _run(project: Path, *args: str):
    result = CliRunner().invoke(main, ["--dhf", str(project / "DHF"), *args])
    assert "Traceback" not in (result.stderr or "") + result.output, result.stderr
    return result


def _envelope(result) -> dict:
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 1, f"expected one JSON line, got {result.stdout!r}"
    return json.loads(lines[0])


class TestItemCommands:
    @pytest.mark.parametrize("args,reason", [
        (["get", "NOPE-1"], "not found"),
        (["update", "NOPE-1", "--data", "{}"], "not found"),
        (["transition", "NOPE-1"], "not found"),
        (["create", "--type", "ZZZ", "--data", "{}"], "Unknown doc type"),
        (["create", "--type", "SRS", "--data", "not json"], "not valid JSON"),
        (["create", "--type", "SRS", "--data", "[1]"], "must be a JSON object"),
        (["create", "--type", "SRS", "--data", "null"], "must be a JSON object"),
        (["update", "SRS-001", "--data", '"text"'], "must be a JSON object"),
        (["update", "SRS-001", "--data", '{"nope": 1}'], "Unknown field"),
        (["transition", "CR-001", "completed"], "not allowed"),
    ])
    def test_a_bad_request_exits_1_with_the_reason_and_no_stdout(
        self, project: Path, args: list[str], reason: str,
    ) -> None:
        result = _run(project, "item", *args)
        assert result.exit_code == 1
        assert result.stdout == ""
        assert reason in result.stderr

    def test_a_refused_update_leaves_the_file_as_it_was(self, project: Path) -> None:
        path = next((project / "DHF" / "items").rglob("SRS-001.yaml"))
        before = path.read_bytes()
        assert _run(project, "item", "update", "SRS-001", "--data", '{"nope": 1}').exit_code == 1
        assert path.read_bytes() == before

    def test_a_refused_create_writes_no_file(self, project: Path) -> None:
        before = sorted((project / "DHF" / "items").rglob("*.yaml"))
        assert _run(project, "item", "create", "--type", "SRS", "--data", '{"bogus": 1}').exit_code == 1
        assert sorted((project / "DHF" / "items").rglob("*.yaml")) == before

    def test_listing_an_unknown_type_is_empty_not_an_error(self, project: Path) -> None:
        result = _run(project, "item", "list", "--type", "ZZZ")
        assert result.exit_code == 0 and result.stdout == ""


class TestVerifyOnABrokenDhf:
    def test_a_dangling_link_fails_and_names_it(self, project: Path) -> None:
        path = next((project / "DHF" / "items").rglob("SRS-001.yaml"))
        data = yaml.safe_load(path.read_text())
        data["derives_from"] = ["SYS-404"]
        path.write_text(yaml.safe_dump(data))
        result = _run(project, "verify", "dhf")
        envelope = _envelope(result)
        assert result.exit_code == 1 and envelope["passed"] is False
        assert any("SYS-404" in e for e in envelope["errors"])

    def test_a_file_that_is_not_yaml_is_named(self, project: Path) -> None:
        path = next((project / "DHF" / "items").rglob("SRS-001.yaml"))
        path.write_text("id: SRS-001\n: [broken\n")
        result = _run(project, "verify", "dhf")
        assert result.exit_code == 1
        assert any("SRS-001.yaml" in e for e in _envelope(result)["errors"])

    def test_a_missing_dhf_is_reported_not_crashed_on(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(main, ["--dhf", str(tmp_path / "nowhere"), "verify", "dhf"])
        assert result.exit_code == 1 and result.stdout == ""
        assert "could not be read" in result.stderr

    def test_the_verdict_always_agrees_with_the_exit_code(self, project: Path) -> None:
        for flags in ([], ["--strict"]):
            result = _run(project, "verify", "dhf", *flags)
            assert _envelope(result)["passed"] == (result.exit_code == 0)


class TestVerifyArguments:
    def test_a_junit_path_that_does_not_exist_is_a_usage_error(self, project: Path) -> None:
        result = _run(project, "verify", "tests", "--junit", str(project / "no-such"))
        assert result.exit_code == 2 and result.stdout == ""

    def test_an_unknown_option_is_a_usage_error(self, project: Path) -> None:
        assert _run(project, "verify", "dhf", "--nope").exit_code == 2

    def test_a_missing_required_option_is_a_usage_error(self, project: Path) -> None:
        assert _run(project, "verify", "completion").exit_code == 2

    def test_completion_of_an_unknown_cr_fails_with_json(self, project: Path) -> None:
        result = _run(project, "verify", "completion", "--cr", "CR-999")
        assert result.exit_code == 1 and _envelope(result)["errors"]

    def test_changes_against_a_ref_that_does_not_exist_fails_with_json(self, project: Path) -> None:
        result = _run(project, "verify", "changes", "--cr", "CR-001", "--since-ref", "no-such-ref")
        assert result.exit_code == 1
        assert any("no-such-ref" in e for e in _envelope(result)["errors"])


class TestBuildArguments:
    @pytest.mark.parametrize("version", ["", " ", "../evil", "1.0/../../x", "a b"])
    def test_a_release_version_that_cannot_name_a_file_is_refused(
        self, project: Path, version: str,
    ) -> None:
        result = _run(project, "build", "release", "--version", version, "--out-dir", str(project / "r"))
        assert result.exit_code == 2
        assert not (project / "r").exists() and not (project.parent / "evil").exists()

    def test_a_release_without_write_leaves_the_dhf_alone(self, project: Path) -> None:
        before = {p: p.read_bytes() for p in (project / "DHF").rglob("*.yaml")}
        result = _run(project, "build", "release", "--version", "1.0.0", "--out-dir", str(project / "r"))
        assert result.exit_code == 0 and json.loads(result.stdout)["rel_uid"] in (None, "")
        assert {p: p.read_bytes() for p in (project / "DHF").rglob("*.yaml")} == before

    def test_a_manifest_that_does_not_exist_is_a_usage_error(self, project: Path) -> None:
        result = _run(project, "build", "soup", "--manifest", str(project / "no-such.txt"))
        assert result.exit_code == 2

    @pytest.mark.parametrize("stage", ["plan", "code"])
    @pytest.mark.parametrize("extra", [[], ["--prompt"]])
    def test_an_unknown_cr_is_refused_before_any_model_runs(
        self, project: Path, stage: str, extra: list[str],
    ) -> None:
        result = _run(project, "build", stage, "--cr", "CR-999", *extra)
        assert result.exit_code == 1 and "not found" in result.stderr

    @pytest.mark.parametrize("stage", ["plan", "code"])
    def test_a_finished_cr_accepts_no_more_work(self, project: Path, stage: str) -> None:
        path = next((project / "DHF" / "items").rglob("CR-001.yaml"))
        data = yaml.safe_load(path.read_text())
        data["status"] = "completed"
        path.write_text(yaml.safe_dump(data))
        result = _run(project, "build", stage, "--cr", "CR-001")
        assert result.exit_code == 1 and "completed" in result.stderr


class TestInit:
    def test_init_refuses_an_existing_dhf_and_changes_nothing(
        self, project: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def snapshot() -> dict:
            return {p: p.read_bytes() for p in project.rglob("*") if p.is_file() and ".git" not in p.parts}

        before = snapshot()
        monkeypatch.chdir(project)
        result = CliRunner().invoke(main, ["init"])
        assert result.exit_code == 1 and "already exists" in result.stderr
        assert snapshot() == before
