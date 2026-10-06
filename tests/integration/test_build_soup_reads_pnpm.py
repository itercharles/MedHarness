"""`build soup` reads a pnpm lockfile, and says so plainly about formats it no longer reads.

pnpm projects had no parser: only `package.json` ranges reached the SOUP register, never the
versions pnpm installed. It registers the dependencies a project declares, not the whole
transitive closure, which no one assesses one by one. Go, Cargo and Maven manifests, which no project used, were dropped; they go
through `--from-command` like any other ecosystem.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.tests.fixtures import bare_dhf
from medharness.cli import main

LOCK = """\
lockfileVersion: '9.0'
importers:
  .:
    dependencies:
      '@adobe/css-tools': {specifier: ^4.4.0, version: 4.4.4}
      react-dom: {specifier: ^18, version: 18.3.1(react@18.3.1)}
packages:
  '@adobe/css-tools@4.4.4':
    resolution: {integrity: sha512-a}
  react-dom@18.3.1:
    resolution: {integrity: sha512-b}
  react@18.3.1:
    resolution: {integrity: sha512-c}
  loose-envify@1.4.0:
    resolution: {integrity: sha512-d}
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    bare_dhf(tmp_path / "DHF")
    return tmp_path


def _soup(project: Path, *args: str):
    result = CliRunner().invoke(main, ["--dhf", str(project / "DHF"), "build", "soup", *args])
    return result, json.loads(result.stdout.splitlines()[0])


def test_a_pnpm_lockfile_is_found_without_any_option(project: Path) -> None:
    (project / "pnpm-lock.yaml").write_text(LOCK)

    result, answer = _soup(project)

    assert result.exit_code == 0, answer["errors"]
    assert answer["packages_found"] == 2, "the transitive packages are not registered"
    assert [Path(m).name for m in answer["manifests_parsed"]] == ["pnpm-lock.yaml"]


def test_each_direct_dependency_becomes_an_npm_soup_item(project: Path) -> None:
    (project / "pnpm-lock.yaml").write_text(LOCK)

    result, answer = _soup(project)

    assert result.exit_code == 0, answer["errors"]
    assert len(answer["items_created"]) == 2
    listed = CliRunner().invoke(main, ["--dhf", str(project / "DHF"), "item", "list", "--type", "SOUP"])
    items = {i["name"]: i for i in map(json.loads, listed.stdout.splitlines()) if "name" in i}
    assert set(items) == {"@adobe/css-tools", "react-dom"}
    assert items["@adobe/css-tools"]["version"] == "4.4.4" and items["react-dom"]["version"] == "18.3.1"
    assert items["react-dom"]["ecosystem"] == "npm"


def test_a_lockfile_pnpm_no_longer_writes_is_an_error_not_a_guess(project: Path) -> None:
    (project / "pnpm-lock.yaml").write_text("lockfileVersion: 5.4\ndependencies:\n  lodash: 4.17.21\n")

    result, answer = _soup(project, "--manifest", str(project / "pnpm-lock.yaml"))

    assert result.exit_code == 1 and answer["outcome"] == "completed_with_errors"
    assert any("lockfileVersion 5.4" in e for e in answer["errors"]), answer["errors"]


@pytest.mark.parametrize("name", ["go.mod", "Cargo.lock", "pom.xml"])
def test_a_manifest_that_was_dropped_is_reported_as_unsupported(project: Path, name: str) -> None:
    (project / name).write_text("")

    result, answer = _soup(project, "--manifest", str(project / name))

    assert result.exit_code == 1
    assert any(f"Unsupported manifest format: {name}" in e for e in answer["errors"]), answer["errors"]


def test_a_dropped_manifest_is_no_longer_discovered(project: Path) -> None:
    (project / "go.mod").write_text("module m\n\nrequire github.com/pkg/errors v0.9.1\n")

    _, answer = _soup(project)

    assert answer["packages_found"] == 0 and answer["manifests_parsed"] == []
