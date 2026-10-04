"""Guards on what the wheel does and does not carry.

The CI workflow is deliberately not part of the release payload — adopters copy
it from `docs/adopting.md` and own it. That policy had drifted: `scaffold_dhf`
copied the template, `_UPGRADE_MAP` claimed to manage it, and the README showed
it as init output, while `exclude-package-data` kept it out of the wheel. So
`init` silently created no workflow and `upgrade` reported "all up to date"
about a file it never opened.

Nothing caught it, because the scaffold CI job installs with `pip install -e .`,
where the repo tree stands in for the package and every template is present.
These tests check the built distribution, which is the only place the split
between policy and payload is visible.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from dhfkit.paths import DEFAULTS_DIR as _TEMPLATES_DIR

REPO_ROOT = Path(__file__).resolve().parents[2]


WORKFLOW_TEMPLATE = REPO_ROOT / "dhfkit" / "templates" / "github" / "workflows" / "dhf.yml"
ADOPTING_DOC = REPO_ROOT / "docs" / "ci.md"


class TestDocumentedRecipeMatchesTemplate:
    """The docs are the only delivery path for the CI recipe, so pin them to it."""

    def test_adopting_doc_embeds_the_template_verbatim(self) -> None:
        recipe = WORKFLOW_TEMPLATE.read_text().rstrip("\n")
        doc = ADOPTING_DOC.read_text()
        assert recipe in doc, (
            "docs/ci.md no longer embeds the workflow template verbatim — "
            "adopters copy the recipe from there, so the two must not drift"
        )

    def test_setup_section_exists(self) -> None:
        assert "## Setting up CI" in ADOPTING_DOC.read_text()


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
    def test_workflow_templates_are_not_packaged(self, built_wheel: Path) -> None:
        """Mirrors scripts/audit_oss_delivery.sh, but fails in the dev loop."""
        with zipfile.ZipFile(built_wheel) as zf:
            names = zf.namelist()
        bundled = [n for n in names if "templates/github/workflows/" in n]
        assert bundled == [], (
            f"the CI workflow is not part of the release payload, but the wheel "
            f"carries {bundled}"
        )

    def test_tests_are_not_packaged(self, built_wheel: Path) -> None:
        """The exclusion that does belong stays in force."""
        with zipfile.ZipFile(built_wheel) as zf:
            names = zf.namelist()
        assert not [n for n in names if n.startswith("dhfkit/tests/")]


def _recipe_commands() -> list[tuple[str, ...]]:
    """Every medharness/dhfkit invocation in the CI recipe, one per entry."""
    text = WORKFLOW_TEMPLATE.read_text()
    text = re.sub(r"\$\{\{[^}]*\}\}", "X", text)
    text = re.sub(r"\\\n\s*", " ", text)
    calls = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(-\s*)?(name:.*|run:\s*)", "", line).strip()
        if re.match(r"^(medharness|dhfkit)\s", line):
            calls.append(tuple(line.split()))
    return calls


RECIPE_CALLS = _recipe_commands()


class TestRecipeCommandsParse:
    """The recipe is copy-paste deployment, so its options must exist.

    `test_documented_commands_exist` strips every flag before checking, so it
    verifies the command path and nothing else. The recipe shipped
    `evidence bundle --dhf DHF` for months; `--dhf` is a group option there, not
    a command one, and the job died with exit 2 on the adopter's first merge.
    """

    def test_the_scan_found_commands(self) -> None:
        """Both jobs' commands: `verify dhf` on every PR, `build release` on tags."""
        found = {call[3:5] for call in RECIPE_CALLS}
        assert found == {("verify", "dhf"), ("build", "release")}, f"found {RECIPE_CALLS}"

    @pytest.mark.parametrize(
        "call", RECIPE_CALLS, ids=[" ".join(c[:3]) for c in RECIPE_CALLS]
    )
    def test_a_recipe_command_parses(self, call: tuple[str, ...]) -> None:
        result = subprocess.run(
            [sys.executable, "-m", call[0], *call[1:], "--help"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        output = result.stderr + result.stdout
        for fault in ("No such option", "No such command", "Got unexpected extra argument"):
            assert fault not in output, (
                f"the CI recipe runs `{' '.join(call)}`, which fails: {fault}"
            )


class TestTheWheelCarriesTheDefaults:
    """Every DHF reads its defaults from the installed package, so a template
    missing from the wheel is missing from every project. `docs/reviews/.gitkeep`
    once never reached the wheel — the build drops dotfiles."""

    def test_every_template_init_copies_is_packaged(self, built_wheel: Path) -> None:
        with zipfile.ZipFile(built_wheel) as zf:
            packaged = {n.split("dhfkit/templates/", 1)[1] for n in zf.namelist()
                        if "dhfkit/templates/" in n and not n.endswith("/")}
        source = {
            str(p.relative_to(_TEMPLATES_DIR))
            for p in _TEMPLATES_DIR.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
            # The CI recipe is published through the docs, not the package.
            and p.relative_to(_TEMPLATES_DIR).parts[:2] != ("github", "workflows")
        }
        assert source - packaged == set(), f"not in the wheel: {sorted(source - packaged)}"
