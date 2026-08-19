"""Guard: every scaffold template must survive packaging.

`templates/github/workflows` was excluded from the wheel via
`exclude-package-data`, so `medharness init` silently created no CI workflow and
`medharness upgrade` reported "all up to date" about a file it never opened.
Nothing caught it: the scaffold CI job installs with `pip install -e .`, where
the repo tree stands in for the package and every template is present.

These tests check the built distribution, which is the only place the fault is
visible.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from medharness.workflows.upgrade import _TEMPLATES_DIR, _UPGRADE_MAP

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestTemplateSourcesExist:
    """Cheap check: the upgrade map and the template tree agree."""

    def test_every_mapped_template_exists(self) -> None:
        missing = [rel for rel, _ in _UPGRADE_MAP if not (_TEMPLATES_DIR / rel).exists()]
        assert missing == [], f"upgrade map references absent templates: {missing}"

    def test_ci_workflow_template_is_mapped(self) -> None:
        mapped = {proj for _, proj in _UPGRADE_MAP}
        assert ".github/workflows/dhf.yml" in mapped


_BUILD_NOISE = shutil.ignore_patterns(
    ".git", ".venv", "build", "dist", "*.egg-info", "__pycache__", ".pytest_cache",
)


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a wheel the way release.yml does, from a pristine copy of the tree.

    Two details are load-bearing:

    * ``python -m build`` — `uv build` resolves a different setuptools, and
      applies ``exclude-package-data`` globs differently, so it does not
      reproduce what actually gets published.
    * A clean copy — a stale ``*.egg-info/SOURCES.txt`` in the working tree is
      reused by setuptools and masks exclusion changes entirely.

    Getting either wrong yields a test that passes while the bug ships.
    """
    try:
        import build  # noqa: F401
    except ImportError:
        pytest.skip("the 'build' package is required to inspect packaging")

    src = tmp_path_factory.mktemp("src") / "repo"
    shutil.copytree(REPO_ROOT, src, ignore=_BUILD_NOISE)
    out = tmp_path_factory.mktemp("dist")

    proc = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out)],
        cwd=src, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        pytest.fail(f"wheel build failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    wheels = list(out.glob("*.whl"))
    assert wheels, "build produced no wheel"
    return wheels[0]


class TestWheelContents:
    def test_ci_workflow_template_is_packaged(self, built_wheel: Path) -> None:
        with zipfile.ZipFile(built_wheel) as zf:
            names = zf.namelist()
        assert "dhfkit/templates/github/workflows/dhf.yml" in names, (
            "the CI workflow template is missing from the wheel — `medharness init` "
            "would scaffold no .github/workflows/dhf.yml"
        )

    def test_every_upgrade_template_is_packaged(self, built_wheel: Path) -> None:
        with zipfile.ZipFile(built_wheel) as zf:
            names = set(zf.namelist())
        absent = [
            rel for rel, _ in _UPGRADE_MAP
            if f"dhfkit/templates/{rel}" not in names
        ]
        assert absent == [], (
            f"templates managed by `medharness upgrade` are absent from the wheel: {absent}"
        )

    def test_tests_are_not_packaged(self, built_wheel: Path) -> None:
        """The exclusion that does belong stays in force."""
        with zipfile.ZipFile(built_wheel) as zf:
            names = zf.namelist()
        assert not [n for n in names if n.startswith("dhfkit/tests/")]


class TestUpgradeReportsUnavailableTemplates:
    """A template absent from the install must be reported, not skipped."""

    def test_unavailable_template_is_surfaced(self, tmp_path: Path, monkeypatch) -> None:
        from medharness.workflows import upgrade as upgrade_mod

        empty = tmp_path / "no-templates"
        empty.mkdir()
        monkeypatch.setattr(upgrade_mod, "_TEMPLATES_DIR", empty)

        result = upgrade_mod.check_upgrade(tmp_path / "project")
        assert len(result["unavailable"]) == len(_UPGRADE_MAP)
        assert "cannot manage them" in result["summary"]

    def test_healthy_install_reports_none_unavailable(self, tmp_path: Path) -> None:
        from medharness.workflows.init import _replace_placeholders, _scaffold_dhf
        from medharness.workflows.upgrade import check_upgrade

        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Trial")
        assert check_upgrade(tmp_path)["unavailable"] == []
