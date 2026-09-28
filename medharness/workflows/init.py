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

from dhfkit.paths import DEFAULTS_DIR as _TEMPLATES_DIR

#: The project's whole config at the start. Everything else is a default the
#: project inherits — and keeps inheriting as MedHarness changes it.
_GLOBAL_YAML = """\
# This DHF's config. Anything not set here comes from MedHarness's defaults:
# the 13 item types, their lifecycle, and which links are required.
#   https://github.com/itercharles/MedHarness/tree/v{{medharness_version}}/dhfkit/templates/config
#
# To change a default, set its key here — it replaces the default key — or put
# a doc type file in doc_types/, which replaces the default type of that code.

project_name: "{{project_name}}"

# Item types this project does not use, e.g. [UC].
omit_doc_types: []
"""


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

    config = project_dir / "DHF" / "config" / "global.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(_GLOBAL_YAML, encoding="utf-8")
    _cp("items", "DHF/items")
    # DHF README goes inside DHF/ — root README is the project README
    _cp("README.md", "DHF/README.md")


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
        if text != original:
            path.write_text(text, encoding="utf-8")



# ---------------------------------------------------------------------------
# File writers
# ---------------------------------------------------------------------------

#: How any coding agent works on the DHF. Plain text in AGENTS.md, which most
#: agents read; the steps themselves come from the installed package.
DHF_INSTRUCTIONS = """\
## Design History File

This repository keeps its Design History File in `DHF/`, checked by MedHarness.
A change to what the product does is not finished until its DHF is.

- **Start a change:** `medharness item create --type CR --data '{"title": "…", "description": "…"}'`,
  then `medharness item transition CR-NNN design`.
- **Design it:** run `medharness build plan --cr CR-NNN --prompt` and do what it says.
- **Build it:** run `medharness build code --cr CR-NNN --prompt` and do what it says.
- **Check it**, and fix what they report:
  - `medharness verify dhf`
  - `medharness verify completion --cr CR-NNN --junit <results>`
  - `medharness verify changes --cr CR-NNN`
- **Close it:** `medharness item transition CR-NNN completed`.

Change items with `medharness item create|update|transition`, never by editing IDs.
"""

_PRODUCT_TEMPLATE = """\
# {name}

Instructions for coding agents. Replace each placeholder with what an engineer
new to the product would need to know.

## Product

{name}: <what it does, in two or three sentences>

## Architecture

<subsystems, technology stack, where the source lives, how to build and test>

## Scope

In scope: <…>
Out of scope: <…>

"""


def _write_agent_files(project_dir: Path, project_name: str) -> None:
    """AGENTS.md for every agent, and a CLAUDE.md that imports it.

    Claude Code reads CLAUDE.md, and AGENTS.md only when there is none. Files
    that exist are added to, never replaced.
    """
    agents = project_dir / "AGENTS.md"
    if not agents.exists():
        agents.write_text(_PRODUCT_TEMPLATE.format(name=project_name) + DHF_INSTRUCTIONS,
                          encoding="utf-8")
    elif "## Design History File" not in agents.read_text(encoding="utf-8"):
        with agents.open("a", encoding="utf-8") as f:
            f.write("\n" + DHF_INSTRUCTIONS)
    claude = project_dir / "CLAUDE.md"
    if not claude.exists():
        claude.write_text("@AGENTS.md\n", encoding="utf-8")
    elif "@AGENTS.md" not in claude.read_text(encoding="utf-8"):
        with claude.open("a", encoding="utf-8") as f:
            f.write("\n@AGENTS.md\n")


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
        ("Write AGENTS.md and CLAUDE.md", lambda: _write_agent_files(project_dir, project_name)),
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
    say("       Describe the product in AGENTS.md — every coding agent reads it.")
    say("       Edit DHF/items/ with your real requirements, risks, and CRs.")
    say()
    say("  3. Check it, from this directory:", bold=True)
    say("       medharness verify dhf")
    say("       medharness verify tests --junit test-results")
    say()
    say("  4. Add CI: copy the recipe in docs/adopting.md, 'Setting up CI'.", bold=True)
    say()

    return {"project_dir": str(project_dir), "project_name": project_name, "created": created}
