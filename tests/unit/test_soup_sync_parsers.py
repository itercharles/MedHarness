"""Tests for medharness.services.soup_sync manifest parsers and extension mechanisms."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from medharness.services.soup_sync import (
    _run_external_command,
    discover_manifests,
    load_soup_sources,
    parse_package_json,
    parse_package_lock_json,
    parse_pnpm_lock,
    parse_poetry_lock,
    parse_pyproject_toml,
    parse_requirements_txt,
    parse_uv_lock,
)


# ---------------------------------------------------------------------------
# requirements.txt
# ---------------------------------------------------------------------------

class TestRequirementsTxt:
    def test_pinned_packages(self, tmp_path: Path) -> None:
        f = tmp_path / "requirements.txt"
        f.write_text("requests==2.28.0\nclick==8.1.7\n")
        pkgs = parse_requirements_txt(f)
        assert len(pkgs) == 2
        assert pkgs[0] == {"name": "requests", "version": "2.28.0", "source": str(f), "ecosystem": "PyPI"}

    def test_extras_stripped(self, tmp_path: Path) -> None:
        f = tmp_path / "requirements.txt"
        f.write_text("uvicorn[standard]==0.20.0\n")
        pkgs = parse_requirements_txt(f)
        assert pkgs[0]["name"] == "uvicorn"
        assert pkgs[0]["version"] == "0.20.0"

    def test_unpinned_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "requirements.txt"
        f.write_text("requests>=2.0\nclick\n")
        assert parse_requirements_txt(f) == []

    def test_comments_and_blank_lines_ignored(self, tmp_path: Path) -> None:
        f = tmp_path / "requirements.txt"
        f.write_text("# comment\n\nrequests==2.28.0\n")
        pkgs = parse_requirements_txt(f)
        assert len(pkgs) == 1


# ---------------------------------------------------------------------------
# uv.lock
# ---------------------------------------------------------------------------

class TestUvLock:
    def test_parses_packages(self, tmp_path: Path) -> None:
        f = tmp_path / "uv.lock"
        f.write_text(textwrap.dedent("""\
            version = 1
            requires-python = ">=3.11"

            [[package]]
            name = "requests"
            version = "2.28.0"
            source = { registry = "https://pypi.org/simple" }

            [[package]]
            name = "click"
            version = "8.1.7"
            source = { registry = "https://pypi.org/simple" }
        """))
        pkgs = parse_uv_lock(f)
        assert len(pkgs) == 2
        names = {p["name"] for p in pkgs}
        assert names == {"requests", "click"}
        assert all(p["ecosystem"] == "PyPI" for p in pkgs)

    def test_version_is_string(self, tmp_path: Path) -> None:
        f = tmp_path / "uv.lock"
        f.write_text('version = 1\n\n[[package]]\nname = "lib"\nversion = "1.0.0"\n')
        pkgs = parse_uv_lock(f)
        assert isinstance(pkgs[0]["version"], str)


# ---------------------------------------------------------------------------
# poetry.lock
# ---------------------------------------------------------------------------

class TestPoetryLock:
    def test_parses_packages(self, tmp_path: Path) -> None:
        f = tmp_path / "poetry.lock"
        f.write_text(textwrap.dedent("""\
            [[package]]
            name = "requests"
            version = "2.28.0"
            description = "HTTP library"
            category = "main"

            [[package]]
            name = "certifi"
            version = "2023.7.22"
            description = "Certificates"
            category = "main"
        """))
        pkgs = parse_poetry_lock(f)
        assert len(pkgs) == 2
        assert pkgs[0]["ecosystem"] == "PyPI"


# ---------------------------------------------------------------------------
# pyproject.toml
# ---------------------------------------------------------------------------

class TestPyprojectToml:
    def test_pep621_pinned(self, tmp_path: Path) -> None:
        f = tmp_path / "pyproject.toml"
        f.write_text(textwrap.dedent("""\
            [project]
            dependencies = [
                "requests==2.28.0",
                "click>=8.0",
            ]
        """))
        pkgs = parse_pyproject_toml(f)
        assert len(pkgs) == 1  # only pinned (==)
        assert pkgs[0]["name"] == "requests"

    def test_poetry_section(self, tmp_path: Path) -> None:
        f = tmp_path / "pyproject.toml"
        f.write_text(textwrap.dedent("""\
            [tool.poetry.dependencies]
            python = "^3.11"
            requests = "2.28.0"
            click = {version = "8.1.7", optional = false}
        """))
        pkgs = parse_pyproject_toml(f)
        names = {p["name"] for p in pkgs}
        assert "requests" in names
        assert "click" in names
        assert "python" not in names


# ---------------------------------------------------------------------------
# package.json
# ---------------------------------------------------------------------------

class TestPackageJson:
    def test_parses_dependencies(self, tmp_path: Path) -> None:
        f = tmp_path / "package.json"
        f.write_text(json.dumps({
            "dependencies": {"express": "^4.18.2"},
            "devDependencies": {"jest": "^29.0.0"},
        }))
        pkgs = parse_package_json(f)
        assert len(pkgs) == 2
        assert all(p["ecosystem"] == "npm" for p in pkgs)
        express = next(p for p in pkgs if p["name"] == "express")
        assert express["version"] == "4.18.2"


# ---------------------------------------------------------------------------
# package-lock.json
# ---------------------------------------------------------------------------

class TestPackageLockJson:
    def test_v3_format(self, tmp_path: Path) -> None:
        f = tmp_path / "package-lock.json"
        f.write_text(json.dumps({
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "myapp", "version": "1.0.0"},
                "node_modules/express": {"version": "4.18.2"},
                "node_modules/lodash": {"version": "4.17.21"},
            },
        }))
        pkgs = parse_package_lock_json(f)
        names = {p["name"] for p in pkgs}
        assert "express" in names
        assert "lodash" in names
        assert "myapp" not in names  # root skipped

    def test_v1_fallback(self, tmp_path: Path) -> None:
        f = tmp_path / "package-lock.json"
        f.write_text(json.dumps({
            "lockfileVersion": 1,
            "dependencies": {
                "express": {"version": "4.18.2"},
            },
        }))
        pkgs = parse_package_lock_json(f)
        assert pkgs[0]["name"] == "express"
        assert pkgs[0]["version"] == "4.18.2"


# ---------------------------------------------------------------------------
# pnpm-lock.yaml
# ---------------------------------------------------------------------------

class TestPnpmLock:
    def test_v9_packages_scoped_and_not(self, tmp_path: Path) -> None:
        f = tmp_path / "pnpm-lock.yaml"
        f.write_text(textwrap.dedent("""\
            lockfileVersion: '9.0'
            importers:
              .:
                dependencies:
                  lodash:
                    specifier: ^4.17.0
                    version: 4.17.21
            packages:
              '@adobe/css-tools@4.4.4':
                resolution: {integrity: sha512-a}
              lodash@4.17.21:
                resolution: {integrity: sha512-b}
            snapshots:
              lodash@4.17.21: {}
            """))
        pkgs = parse_pnpm_lock(f)
        assert [(p["name"], p["version"]) for p in pkgs] == [("@adobe/css-tools", "4.4.4"), ("lodash", "4.17.21")]
        assert all(p["ecosystem"] == "npm" and p["source"] == str(f) for p in pkgs)

    def test_v6_keys_carry_a_slash_and_a_peer_suffix(self, tmp_path: Path) -> None:
        f = tmp_path / "pnpm-lock.yaml"
        f.write_text("lockfileVersion: '6.0'\npackages:\n  /react-dom@18.2.0(react@18.2.0):\n    resolution: {}\n"
                     "  /@babel/core@7.29.0:\n    resolution: {}\n")
        assert [(p["name"], p["version"]) for p in parse_pnpm_lock(f)] == [
            ("react-dom", "18.2.0"), ("@babel/core", "7.29.0")]

    def test_a_package_with_no_registry_version_is_left_out(self, tmp_path: Path) -> None:
        f = tmp_path / "pnpm-lock.yaml"
        f.write_text("lockfileVersion: '9.0'\npackages:\n  'left-pad@https://codeload.github.com/x/y/tar.gz/abc':\n"
                     "    resolution: {}\n  ok@1.0.0-beta.1:\n    resolution: {}\n")
        assert [(p["name"], p["version"]) for p in parse_pnpm_lock(f)] == [("ok", "1.0.0-beta.1")]

    def test_a_lockfile_older_than_v6_is_refused_not_misread(self, tmp_path: Path) -> None:
        f = tmp_path / "pnpm-lock.yaml"
        f.write_text("lockfileVersion: 5.4\npackages:\n  /lodash/4.17.21:\n    resolution: {}\n")
        with pytest.raises(ValueError, match="lockfileVersion 5.4"):
            parse_pnpm_lock(f)

    def test_no_packages_is_an_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "pnpm-lock.yaml"
        f.write_text("lockfileVersion: '9.0'\n")
        assert parse_pnpm_lock(f) == []


# ---------------------------------------------------------------------------
# Auto-discovery
# ---------------------------------------------------------------------------

class TestDiscoverManifests:
    def test_finds_requirements_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
        found = discover_manifests(tmp_path)
        assert any(p.name == "requirements.txt" for p in found)

    def test_finds_multiple(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("")
        (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
        found = discover_manifests(tmp_path)
        names = {p.name for p in found}
        assert {"requirements.txt", "pnpm-lock.yaml"} <= names

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert discover_manifests(tmp_path) == []


# ---------------------------------------------------------------------------
# External command
# ---------------------------------------------------------------------------

class TestRunExternalCommand:
    def test_parses_ndjson_output(self, tmp_path: Path) -> None:
        pkgs = _run_external_command(
            'printf \'{"name":"lib","version":"1.0","ecosystem":"PyPI"}\\n\'',
            cwd=tmp_path,
        )
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "lib"
        assert pkgs[0]["version"] == "1.0"
        assert pkgs[0]["ecosystem"] == "PyPI"
        assert pkgs[0]["source"].startswith("command: ")

    def test_default_ecosystem_applied(self, tmp_path: Path) -> None:
        pkgs = _run_external_command(
            'printf \'{"name":"lib","version":"1.0"}\\n\'',
            default_ecosystem="PyPI",
            cwd=tmp_path,
        )
        assert pkgs[0]["ecosystem"] == "PyPI"

    def test_nonzero_exit_raises(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError, match="exited"):
            _run_external_command("exit 1", cwd=tmp_path)

    def test_invalid_json_lines_skipped(self, tmp_path: Path) -> None:
        pkgs = _run_external_command(
            'printf "not-json\\n{\\"name\\":\\"lib\\",\\"version\\":\\"1.0\\",\\"ecosystem\\":\\"PyPI\\"}\\n"',
            cwd=tmp_path,
        )
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "lib"


# ---------------------------------------------------------------------------
# soup-sources.yaml
# ---------------------------------------------------------------------------

class TestLoadSoupSources:
    def _write_sources(self, dhf: Path, content: str) -> None:
        (dhf / "config").mkdir(parents=True, exist_ok=True)
        (dhf / "config" / "soup-sources.yaml").write_text(content)

    def test_manifest_entry(self, tmp_path: Path) -> None:
        dhf = tmp_path / "DHF"
        proj = tmp_path
        req = proj / "requirements.txt"
        req.write_text("requests==2.28.0\n")
        self._write_sources(dhf, "sources:\n  - type: manifest\n    path: requirements.txt\n")
        pkgs, errors = load_soup_sources(dhf, proj)
        assert errors == []
        assert any(p["name"] == "requests" for p in pkgs)

    def test_manual_entry(self, tmp_path: Path) -> None:
        dhf = tmp_path / "DHF"
        self._write_sources(dhf, textwrap.dedent("""\
            sources:
              - type: manual
                items:
                  - name: Ubuntu Server
                    version: "22.04.3 LTS"
                    manufacturer: Canonical
                    ecosystem: null
        """))
        pkgs, errors = load_soup_sources(dhf, tmp_path)
        assert errors == []
        assert pkgs[0]["name"] == "Ubuntu Server"
        assert pkgs[0]["version"] == "22.04.3 LTS"

    def test_command_entry(self, tmp_path: Path) -> None:
        dhf = tmp_path / "DHF"
        self._write_sources(dhf, textwrap.dedent("""\
            sources:
              - type: command
                run: 'printf "{\\"name\\":\\"mylib\\",\\"version\\":\\"1.0\\",\\"ecosystem\\":\\"PyPI\\"}\\n"'
        """))
        pkgs, errors = load_soup_sources(dhf, tmp_path)
        assert errors == []
        assert any(p["name"] == "mylib" for p in pkgs)

    def test_missing_manifest_reports_error(self, tmp_path: Path) -> None:
        dhf = tmp_path / "DHF"
        self._write_sources(dhf, "sources:\n  - type: manifest\n    path: nonexistent.txt\n")
        pkgs, errors = load_soup_sources(dhf, tmp_path)
        assert any("nonexistent" in e for e in errors)
        assert pkgs == []

    def test_no_sources_file_returns_empty(self, tmp_path: Path) -> None:
        dhf = tmp_path / "DHF"
        (dhf / "config").mkdir(parents=True, exist_ok=True)
        pkgs, errors = load_soup_sources(dhf, tmp_path)
        assert pkgs == []
        assert errors == []
