"""A package.json range is not the version that ships; the lockfile beside it is.

`^2.1.0` was recorded as 2.1.0, the floor of the range. verify soup then asked OSV about versions
nobody runs: 21 advisories where the installed versions had 9.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.tests.fixtures import bare_dhf
from medharness.cli import main

PNPM = """\
lockfileVersion: '9.0'
importers:
  .:
    dependencies:
      left-pad: {specifier: ^1.0.0, version: 1.3.0}
  apps/client:
    devDependencies:
      vitest: {specifier: ^2.1.0, version: 2.1.9(@types/node@20.1.0)}
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    bare_dhf(tmp_path / "DHF")
    (tmp_path / ".git").mkdir()
    return tmp_path


def _manifest(directory: Path, **deps: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "package.json"
    path.write_text(json.dumps({"devDependencies": deps}))
    return path


def _versions(project: Path, manifest: Path) -> dict[str, str]:
    result = CliRunner().invoke(main, ["--dhf", str(project / "DHF"), "build", "soup",
                                       "--manifest", str(manifest)])
    assert result.exit_code == 0, result.stderr
    items = {}
    for path in (project / "DHF" / "items").rglob("SOUP-*.yaml"):
        text = path.read_text(encoding="utf-8")
        name = next(l.split(": ", 1)[1] for l in text.splitlines() if l.startswith("name:")).strip("'\"")
        version = next(l.split(": ", 1)[1] for l in text.splitlines() if l.startswith("version:")).strip("'\"")
        items[name] = version
    return items


def test_a_workspace_member_gets_the_version_its_importer_installed(project: Path) -> None:
    (project / "pnpm-lock.yaml").write_text(PNPM)
    manifest = _manifest(project / "apps" / "client", vitest="^2.1.0")

    assert _versions(project, manifest) == {"vitest": "2.1.9"}


def test_a_package_lock_beside_the_manifest_is_read(project: Path) -> None:
    (project / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {
        "": {"name": "app"}, "node_modules/express": {"version": "4.19.2"}}}))
    manifest = _manifest(project, express="^4.18.0")

    assert _versions(project, manifest) == {"express": "4.19.2"}


def test_a_dependency_the_lockfile_does_not_list_keeps_the_range_floor(project: Path) -> None:
    (project / "pnpm-lock.yaml").write_text(PNPM)
    manifest = _manifest(project / "apps" / "client", vitest="^2.1.0", missing="^3.0.0")

    assert _versions(project, manifest) == {"vitest": "2.1.9", "missing": "3.0.0"}


def test_a_lockfile_above_the_repository_root_is_not_read(tmp_path: Path) -> None:
    (tmp_path / "pnpm-lock.yaml").write_text(PNPM)
    repo = tmp_path / "repo"
    bare_dhf(repo / "DHF")
    (repo / ".git").mkdir()
    manifest = _manifest(repo, **{"left-pad": "^1.0.0"})

    assert _versions(repo, manifest) == {"left-pad": "1.0.0"}
