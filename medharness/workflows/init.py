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
            text = path.read_text(encoding="utf-8")
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
            path.write_text(text, encoding="utf-8")

    global_yaml = project_dir / "DHF" / "config" / "global.yaml"
    if global_yaml.exists():
        content = global_yaml.read_text(encoding="utf-8")
        content = content.replace(
            'project_name: "My Medical Device Software"',
            f'project_name: "{project_name}"',
        )
        global_yaml.write_text(content, encoding="utf-8")


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
""", encoding="utf-8")
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

# Transient JUnit output from local test runs. Evidence of verification is the
# bundle a run produces, not anything left in the working tree.
/test-results/
artifacts/

# Regenerated on demand from the items, and date-stamped, so a new set appears
# every day an evidence bundle runs.
DHF/documents/exports/
*.egg-info/
dist/
build/
.pytest_cache/
""", encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run_init() -> dict:
    """Zero-prompt onboarding: scaffold a single-repo project in the current directory.

    Returns the project and the files written. The walkthrough goes to stderr,
    so stdout carries only the answer, as it does for every other command.
    """
    project_dir = Path.cwd()
    raw_name = project_dir.name
    project_name = raw_name.replace("-", " ").replace("_", " ").title()

    def say(text: str = "", **style) -> None:
        click.secho(text, err=True, **style)

    say()
    say("MedHarness Init", bold=True)
    say("━" * 45)
    say()
    say(f"  Directory  : {project_dir}")
    say(f"  Project    : {project_name}")
    say()

    if (project_dir / "DHF").exists():
        raise click.ClickException(
            "DHF/ already exists in this directory. "
            "Remove it or run from a fresh directory."
        )

    before = {f for f in project_dir.rglob("*") if f.is_file()}
    steps = [
        ("Scaffold DHF structure", lambda: (_scaffold_dhf(project_dir),
                                            _replace_placeholders(project_dir, project_name))),
        ("Write CLAUDE.md", lambda: _write_claude_md(project_dir, project_name)),
        ("Write .gitignore", lambda: _write_gitignore(project_dir)),
    ]
    for n, (label, run) in enumerate(steps, start=1):
        click.echo(f"[{n}/{len(steps)}] {label}...", nl=False, err=True)
        run()
        click.secho(" ✓", fg="green", err=True)
    created = sorted(
        str(f.relative_to(project_dir))
        for f in project_dir.rglob("*") if f.is_file() and f not in before
    )

    say()
    say("━" * 45)
    say("Done. Next steps:", bold=True, fg="green")
    say()
    say("  1. Initialize git and make first commit:", bold=True)
    say("       git init && git add -A")
    say(f'       git commit -m "feat: initialize {project_name} with MedHarness"')
    say()
    say("  2. Replace the sample content:", bold=True)
    say("       Edit AI-harness/context.md with your product description.")
    say("       Edit DHF/items/ with your real requirements, risks, and CRs.")
    say()
    say("  3. Check it, from this directory:", bold=True)
    say("       medharness verify dhf")
    say("       medharness verify tests --junit-dir test-results")
    say()
    say("  4. Add CI: copy the recipe in docs/adopting.md, 'Setting up CI'.", bold=True)
    say()

    return {"project_dir": str(project_dir), "project_name": project_name, "created": created}
