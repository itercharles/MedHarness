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

import shutil
from importlib.metadata import version as pkg_version
from pathlib import Path

import click

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "dhfkit" / "templates"


# ---------------------------------------------------------------------------
# DHF scaffold
# ---------------------------------------------------------------------------

def _scaffold_dhf(project_dir: Path) -> None:
    """Create DHF structure inside project_dir from bundled templates.

    ci.yml is intentionally omitted — its checks are merged into
    engineering-control.yml for the single-repo layout.
    """
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

    # DHF README goes inside DHF/ — root README is the project README
    _cp("README.md", "DHF/README.md")

    # GitHub AI prompts
    _cp("github/prompts", ".github/prompts")

    # DHF AI workflows — ci.yml omitted (merged into engineering-control.yml)
    for wf in ("cr-analyze.yml", "cr-develop.yml", "cr-spec-iterate.yml", "cr-transition.yml"):
        _cp(f"github/workflows/dhf/{wf}", f".github/workflows/{wf}")

    # Empty test-results dir
    results_dir = project_dir / "DHF" / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / ".gitkeep").touch(exist_ok=True)


def _replace_placeholders(project_dir: Path, project_name: str) -> None:
    """Substitute template placeholders in scaffolded content."""
    try:
        medharness_version = pkg_version("medharness")
    except Exception:
        medharness_version = "latest"

    text_extensions = {".md", ".yaml", ".yml", ".j2", ".css", ".txt", ".gitkeep"}

    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in text_extensions:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
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
| `.github/workflows/` | CI: design gate, test coverage, evidence bundle |

## Key Rules

- PR title must include a CR ID (e.g. `feat(CR-012): description`)
- DHF mutations go through `medharness --dhf DHF dhf item` commands
- `ci test-coverage` enforces requirement→test coverage on every PR
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
test-results/
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


def _write_engineering_control_yml(project_dir: Path) -> Path:
    dest = project_dir / ".github" / "workflows" / "engineering-control.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_generate_engineering_control_yaml())
    return dest


def _write_cr_complete_yml(project_dir: Path) -> Path:
    dest = project_dir / ".github" / "workflows" / "cr-complete.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    template = _TEMPLATES_DIR / "github" / "workflows" / "product" / "cr-complete.yml"
    dest.write_text(template.read_text(encoding="utf-8"))
    return dest


def _write_review_pr_yml(project_dir: Path) -> Path:
    dest = project_dir / ".github" / "workflows" / "review-pr.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    template = _TEMPLATES_DIR / "github" / "workflows" / "product" / "review-pr.yml"
    dest.write_text(template.read_text(encoding="utf-8"))
    return dest



# ---------------------------------------------------------------------------
# Engineering control workflow generation
# ---------------------------------------------------------------------------

def _generate_engineering_control_yaml() -> str:
    """Generate the single-repo engineering-control.yml.

    Phases:
      cr-validation  — PR gate: verify CR exists in DHF
      dhf-validation — PR gate: schema + traceability coverage
      test-coverage  — PR gate: run tests, check requirement→TC coverage
      evidence-bundle — post-merge: produce signed evidence artifact
    """
    return """\
name: Engineering Control CI

on:
  push:
    branches: [ main ]
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read

jobs:

  cr-validation:
    name: CR Validation
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4

      - name: Extract CR IDs from PR title
        id: extract-cr
        env:
          PR_TITLE: ${{ github.event.pull_request.title }}
        run: |
          CR_IDS=$(echo "$PR_TITLE" | grep -oE 'CR-[0-9]+' | sort -u | tr '\\n' ' ' || true)
          echo "cr_ids=$CR_IDS" >> "$GITHUB_OUTPUT"
          if [ -z "$CR_IDS" ]; then
            echo "✗ No CR ID in PR title. Format: feat(CR-012): description" >&2
            exit 1
          fi

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install MedHarness
        run: pip install medharness

      - name: Check CR status
        env:
          CR_IDS: ${{ steps.extract-cr.outputs.cr_ids }}
        run: |
          FAILED=0
          for CR_ID in $CR_IDS; do
            medharness --dhf DHF dhf item get "$CR_ID" > /dev/null || { echo "✗ $CR_ID not found in DHF" >&2; FAILED=1; }
          done
          [ "$FAILED" -eq 0 ] || exit 1

  dhf-validation:
    name: DHF Validation
    runs-on: ubuntu-latest
    needs: cr-validation
    if: always() && (needs.cr-validation.result == 'success' || needs.cr-validation.result == 'skipped')
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install MedHarness
        run: pip install medharness

      - name: Validate DHF schema and traceability
        run: |
          medharness ci dhf-validate \\
            --dhf DHF \\
            --run-schema \\
            --run-traceability \\
            --coverage-pair UC:CRS \\
            --coverage-pair CRS:SYS \\
            --coverage-pair SYS:SRS \\
            --coverage-pair SRS:SWDD \\
            --fail-on-uncovered

  test-coverage:
    name: Test Coverage Gate
    runs-on: ubuntu-latest
    needs: dhf-validation
    if: always() && needs.dhf-validation.result != 'failure'
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install MedHarness
        run: pip install medharness

      - name: Run tests
        run: |
          mkdir -p test-results/
          # Replace with your test runner. Must output JUnit XML to test-results/.
          # pytest:  pytest tests/ -v --junitxml=test-results/results.xml
          # Jest:    jest --reporters=jest-junit  (JEST_JUNIT_OUTPUT_DIR=test-results)
          # Maven:   mvn test -Dsurefire.reportsDirectory=test-results/
          # Go:      go test ./... | go-junit-report > test-results/results.xml
          echo "No tests configured yet — add your test command above."

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: test-results/

      - name: Check test coverage gate
        run: |
          medharness ci test-coverage \\
            --dhf DHF \\
            --junit-dir test-results

  evidence-bundle:
    name: Evidence Bundle
    runs-on: ubuntu-latest
    needs: [test-coverage]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main' && !cancelled()
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install MedHarness
        run: pip install medharness

      - name: Download test results
        uses: actions/download-artifact@v4
        with:
          name: test-results
          path: test-results/

      - name: Generate evidence bundle
        run: |
          medharness --dhf DHF ci evidence bundle \\
            --out-dir artifacts \\
            --junit-dir test-results

      - name: Upload evidence bundle
        uses: actions/upload-artifact@v4
        with:
          name: dhf-evidence-bundle
          path: artifacts/
"""


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
        "Write engineering-control.yml",
        "Write cr-complete.yml",
        "Write review-pr.yml",
        "Write Claude Code skills",
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

    _step("Write engineering-control.yml")
    _write_engineering_control_yml(project_dir)
    click.secho(" ✓", fg="green")

    _step("Write cr-complete.yml")
    _write_cr_complete_yml(project_dir)
    click.secho(" ✓", fg="green")

    _step("Write review-pr.yml")
    _write_review_pr_yml(project_dir)
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
    click.secho("  3. Optional secrets (Settings → Secrets):", bold=True)
    click.echo(f"       ANTHROPIC_API_KEY — enables AI CR analysis and development workflows")
    click.echo()
    click.secho("  4. Replace sample DHF content:", bold=True)
    click.echo(f"       Edit DHF/items/ with your real requirements, risks, and CRs.")
    click.echo(f"       Validate: medharness --dhf DHF dhf validate schema")
    click.echo()
