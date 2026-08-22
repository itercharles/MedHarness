"""medharness init — zero-prompt onboarding command.

Run from inside the project folder after creating a venv and installing medharness:

    mkdir myproject && cd myproject
    python -m venv .venv && source .venv/bin/activate
    pip install medharness
    medharness init

Scaffolds a single-repo project with DHF integrated alongside source code.
No prompts — everything is derived from the current directory.
"""

from __future__ import annotations

import os
import shutil
from importlib.metadata import version as pkg_version
from pathlib import Path

import click

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "dhfkit" / "templates"


# ---------------------------------------------------------------------------
# DHF scaffold
# ---------------------------------------------------------------------------

def _scaffold_dhf(project_dir: Path) -> None:
    """Create DHF structure inside project_dir from bundled templates."""
    project_dir.mkdir(parents=True, exist_ok=True)

    def _cp(rel_src: str, rel_dst: str) -> None:
        src = _TEMPLATES_DIR / rel_src
        dst = project_dir / rel_dst
        if not src.exists():
            return
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                src, dst, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # DHF content
    _cp("config", "DHF/config")
    _cp("specs", "DHF/documents/specs")
    _cp("plans", "DHF/documents/plans")
    _cp("items", "DHF/items")
    _cp("reviews", "docs/reviews")

    # DHF README goes inside DHF/ — root README is the project README
    _cp("README.md", "DHF/README.md")

    # AI prompts only. The CI workflow is not part of the release payload —
    # adopters copy it from docs/adopting.md and own it from there, so scaffolding
    # it here would silently do nothing on an installed package.
    _cp("github/prompts", ".github/prompts")

    # AI agent context file
    _cp("AI-harness", "AI-harness")

    # Empty test-results dir
    results_dir = project_dir / "DHF" / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / ".gitkeep").touch(exist_ok=True)


# Directories that may sit inside a project root but are never scaffold output.
# A virtualenv is the dangerous one: the documented setup creates .venv inside
# the project, so an unrestricted walk rewrote the installed package's own
# templates — permanently, and for every later project built from that venv.
_NON_SCAFFOLD_DIRS = frozenset({
    ".venv", "venv", ".git", "node_modules", "__pycache__",
    "site-packages", ".tox", ".mypy_cache", ".pytest_cache",
})

def _substitutable_files(project_dir: Path):
    """Yield project files, pruning trees the scaffold never owns.

    Pruning rather than allow-listing: an allow-list would silently stop
    covering any directory the scaffold gains later, while the failure this
    guards against is specifically a walk descending into an environment
    directory that happens to sit inside the project root.
    """
    for dirpath, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = [d for d in dirnames if d not in _NON_SCAFFOLD_DIRS]
        for filename in filenames:
            yield Path(dirpath) / filename


def _replace_placeholders(project_dir: Path, project_name: str) -> None:
    """Substitute template placeholders in scaffolded content."""
    try:
        medharness_version = pkg_version("medharness")
    except Exception:
        medharness_version = "latest"

    text_extensions = {".md", ".yaml", ".yml", ".j2", ".css", ".txt", ".gitkeep"}

    for path in _substitutable_files(project_dir):
        if path.suffix not in text_extensions:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        except OSError:
            continue  # read-only or otherwise unreadable — not ours to rewrite
        original = text
        text = text.replace("{{project_name}}", project_name)
        text = text.replace("{{medharness_version}}", medharness_version)
        text = text.replace("{{medharness_repo}}", "itercharles/MedHarness")
        text = text.replace("{{primary_test_tool}}", "pytest")
        if text != original:
            path.write_text(text)

    global_yaml = project_dir / "DHF" / "config" / "global.yaml"
    if global_yaml.exists():
        content = global_yaml.read_text()
        content = content.replace(
            'project_name: "My Medical Device Software"',
            f'project_name: "{project_name}"',
        )
        global_yaml.write_text(content)


# ---------------------------------------------------------------------------
# File writers
# ---------------------------------------------------------------------------

def _write_claude_md(project_dir: Path, project_name: str) -> Path:
    """Write CLAUDE.md for a single-repo project layout."""
    project_dir.mkdir(parents=True, exist_ok=True)
    dest = project_dir / "CLAUDE.md"
    dest.write_text(f"""\
# CLAUDE.md

## Project

{project_name} — medical device software developed under design control.

## Repo Structure

| Directory | Purpose |
|-----------|---------|
| `DHF/` | Design History File — requirements, risks, traceability |
| `src/` | Product source code |
| `tests/` | Product test suite |
| `.github/` | Optional repo-local automation and prompts |

## Key Rules

- PR title must include a CR ID (e.g. `feat(CR-012): description`)
- DHF mutations go through `dhfkit --dhf DHF item` commands
- `verify tests` enforces requirement→test coverage on every PR
- Evidence bundle is produced on merge to `main`
- Canonical product docs live in `DHF/documents/`:
  - `DHF/documents/specs/customer_requirement_specification.md`
  - `DHF/documents/specs/architecture_design_specification.md`
  - `DHF/documents/plans/development_plan.md`
""")
    return dest


def _write_gitignore(project_dir: Path) -> Path:
    dest = project_dir / ".gitignore"
    if dest.exists():
        return dest
    dest.write_text("""\
.venv/
venv/
__pycache__/
*.pyc
*.pyo
.DS_Store

# Transient JUnit output from local test runs. DHF/test-results/ is deliberately
# NOT ignored: it holds the result store, which carries verification evidence —
# including manual review records that exist nowhere else — and must be
# committed alongside the items it verifies.
/test-results/
artifacts/
*.egg-info/
dist/
build/
.pytest_cache/
""")
    return dest


def _write_tests_stub(project_dir: Path) -> Path:
    tests_dir = project_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / ".gitkeep").touch(exist_ok=True)
    return tests_dir


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run_init() -> None:
    """Zero-prompt onboarding: scaffold a single-repo project in the current directory."""
    project_dir = Path.cwd()
    raw_name = project_dir.name
    project_name = raw_name.replace("-", " ").replace("_", " ").title()

    click.echo()
    click.secho("MedHarness Init", bold=True)
    click.echo("━" * 45)
    click.echo()
    click.echo(f"  Directory  : {project_dir}")
    click.echo(f"  Project    : {project_name}")
    click.echo()

    if (project_dir / "DHF").exists():
        raise click.ClickException(
            "DHF/ already exists in this directory. "
            "Remove it or run from a fresh directory."
        )

    steps = [
        "Scaffold DHF structure",
        "Write CLAUDE.md",
        "Write .gitignore",
    ]
    total = len(steps)
    n = 0

    def _step(msg: str) -> None:
        nonlocal n
        n += 1
        click.echo(f"[{n}/{total}] {msg}...", nl=False)

    _step("Scaffold DHF structure")
    _scaffold_dhf(project_dir)
    _replace_placeholders(project_dir, project_name)
    click.secho(" ✓", fg="green")

    _step("Write CLAUDE.md")
    _write_claude_md(project_dir, project_name)
    click.secho(" ✓", fg="green")

    _step("Write .gitignore")
    _write_gitignore(project_dir)
    click.secho(" ✓", fg="green")

    click.echo()
    click.echo("━" * 45)
    click.secho("Done. Next steps:", bold=True, fg="green")
    click.echo()
    click.secho("  1. Initialize git and make first commit:", bold=True)
    click.echo(f"       git init && git add -A")
    click.echo(f'       git commit -m "feat: initialize {project_name} with MedHarness"')
    click.echo()
    click.secho("  2. Push to GitHub:", bold=True)
    click.echo(f"       git remote add origin https://github.com/<org>/{raw_name}")
    click.echo(f"       git push -u origin main")
    click.echo()
    click.secho("  3. Wire your automation around the CLI:", bold=True)
    click.echo("       medharness verify dhf --dhf DHF")
    click.echo("       medharness verify tests --dhf DHF --junit-dir test-results")
    click.echo("       medharness --dhf DHF evidence bundle --out-dir artifacts --junit-dir test-results")
    click.echo()
    click.secho("  4. Replace sample DHF content:", bold=True)
    click.echo(f"       Edit AI-harness/context.md with your product description.")
    click.echo(f"       Edit DHF/items/ with your real requirements, risks, and CRs.")
    click.echo(f"       Validate: dhfkit --dhf DHF validate schema")
    click.echo()
