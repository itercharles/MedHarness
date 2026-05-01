"""compliantflow init — interactive onboarding command.

Sets up CompliantFlow infrastructure for a new project:
  1. Optionally fetches the DHF template from CompliantFlow-DHF
  2. Writes product repo files (CLAUDE.md, engineering-control.yml, cr-complete.yml)
  3. Prints git commands to push both repos and open a PR
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Optional

import click

DHF_TEMPLATE_REPO = "https://github.com/compliantflow/compliantflow-dhf"
DEFAULT_TEMPLATE_REF = "main"


# ---------------------------------------------------------------------------
# DHF template — fetched from CompliantFlow-DHF at runtime
# ---------------------------------------------------------------------------

def _fetch_dhf_template(dhf_dir: Path, ref: str) -> None:
    """Clone the DHF template from CompliantFlow-DHF into dhf_dir.

    The DHF repo contains DHF/ items, config, documents, and .github/ CI
    workflows.  We clone shallow then remove non-template files (dhf_util,
    tests, etc.) leaving only the DHF scaffolding and repo-level README.
    """
    dhf_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cf-dhf-") as tmp:
        repo_dir = Path(tmp) / "repo"
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", ref,
                 DHF_TEMPLATE_REPO, str(repo_dir)],
                check=True, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError as e:
            raise click.ClickException(
                f"Failed to fetch DHF template from {DHF_TEMPLATE_REPO} "
                f"(ref: {ref}).\n"
                f"git error: {e.stderr.strip() if e.stderr else str(e)}"
            ) from e

        # Copy template content: DHF/, .github/, dhf_util/, pyproject.toml, README.md
        for name in ["DHF", ".github", "dhf_util", "pyproject.toml", "README.md"]:
            src = repo_dir / name
            if not src.exists():
                continue
            dst = dhf_dir / name
            if src.is_dir():
                shutil.copytree(
                    src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
                )
            else:
                shutil.copy2(src, dst)


def _replace_placeholders(dhf_dir: Path, project_name: str, product_repo: Optional[str]) -> None:
    """Substitute placeholders in the fetched DHF template."""
    dhf_repo_name = (product_repo.split("/", 1)[1] + "-dhf"
                     if product_repo and "/" in product_repo else "your-product-dhf")
    github_org = (product_repo.split("/", 1)[0]
                  if product_repo and "/" in product_repo else "your-org")

    for path in dhf_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        original = text
        text = text.replace("{{project_name}}", project_name)
        text = text.replace("{{product_repo}}", product_repo or "your-org/your-product")
        text = text.replace("{{product_repo_name}}",
                            product_repo.split("/", 1)[1] if product_repo and "/" in product_repo else "your-product")
        text = text.replace("{{github_org}}", github_org)
        text = text.replace("{{dhf_repo_name}}", dhf_repo_name)
        if text != original:
            path.write_text(text)

    # Set project_name in global.yaml
    global_yaml = dhf_dir / "DHF" / "config" / "global.yaml"
    if global_yaml.exists():
        content = global_yaml.read_text()
        content = content.replace(
            'project_name: "My Medical Device Software"',
            f'project_name: "{project_name}"',
        )
        global_yaml.write_text(content)


# ---------------------------------------------------------------------------
# Product repo file writers
# ---------------------------------------------------------------------------

def _write_claude_md(product_dir: Path, project_name: str, dhf_repo: Optional[str]) -> Path:
    """Write a minimal CLAUDE.md entrypoint into product_dir."""
    dhf_ref = dhf_repo or "your-org/your-product-dhf"
    product_dir.mkdir(parents=True, exist_ok=True)
    dest = product_dir / "CLAUDE.md"
    dest.write_text(f"""# CLAUDE.md

## Project

{project_name} — medical device software developed under design control.

## Repo Responsibility

| Repo | Purpose |
|------|---------|
| This repo | Product source code, tests, CI |
| `{dhf_ref}` | Design History File — requirements, risks, traceability |

## Key Rules

- PR title must include a CR ID (e.g. `feat(CR-012): description`)
- DHF mutations go through `python -m dhf_util` in the DHF repo
- `ci test-coverage` enforces requirement→test coverage on every push
- Evidence bundle is produced on merge to `main`
- Canonical product docs live in the DHF repo:
  - `DHF/documents/specs/customer_requirement_specification.md`
  - `DHF/documents/specs/architecture_design_specification.md`
  - `DHF/documents/plans/development_plan.md`
- See [README.md](README.md) for project overview
""")
    return dest


def _write_engineering_control_yml(
    product_dir: Path,
    dhf_repo: Optional[str],
) -> Path:
    dest = product_dir / ".github" / "workflows" / "engineering-control.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_generate_engineering_control_yaml(dhf_repo))
    return dest


def _write_cr_complete_yml(product_dir: Path, dhf_repo: Optional[str]) -> Path:
    dhf_repo_value = dhf_repo or "your-org/your-product-dhf"
    dest = product_dir / ".github" / "workflows" / "cr-complete.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"""\
name: Complete CR In DHF

on:
  pull_request:
    types: [closed]
    branches: [main]

jobs:
  complete-cr:
    if: ${{{{ github.event.pull_request.merged == true }}}}
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Extract CR ID from PR title
        id: cr
        env:
          PR_TITLE: ${{{{ github.event.pull_request.title }}}}
        run: |
          CR_ID=$(echo "$PR_TITLE" | grep -oE 'CR-[0-9]+' | head -n 1 || true)
          if [ -z "$CR_ID" ]; then
            echo "No CR ID found in PR title; skipping."
            echo "skip=true" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          echo "cr_id=$CR_ID" >> "$GITHUB_OUTPUT"

      - name: Check out DHF repo
        if: steps.cr.outputs.skip != 'true'
        uses: actions/checkout@v4
        with:
          repository: {dhf_repo_value}
          token: ${{{{ secrets.DHF_REPO_TOKEN }}}}
          path: dhf

      - name: Set up Python
        if: steps.cr.outputs.skip != 'true'
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install DHF dependencies
        if: steps.cr.outputs.skip != 'true'
        run: |
          python -m pip install --upgrade pip
          pip install -e dhf/

      - name: Install CompliantFlow
        if: steps.cr.outputs.skip != 'true'
        run: pip install compliantflow

      - name: Complete CR in DHF
        if: steps.cr.outputs.skip != 'true'
        run: |
          cd dhf
          git config user.name "GitHub Actions [bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          cd ..
          compliantflow cr workflow complete-from-github-pr \\
            --dhf-repo dhf \\
            --event "$GITHUB_EVENT_PATH" \\
            --by "github-actions[bot]" \\
            --push
""")
    return dest


# ---------------------------------------------------------------------------
# Engineering control workflow generation
# ---------------------------------------------------------------------------

def _cf_version() -> str:
    try:
        return f"v{pkg_version('compliantflow')}"
    except Exception:
        return "latest"


def _generate_engineering_control_yaml(dhf_repo: Optional[str]) -> str:
    version = _cf_version()
    checkout_dhf = ""
    dhf_path_arg = "--dhf DHF"
    install_dhf = ""

    if dhf_repo:
        checkout_dhf = f"""\
      - name: Check out DHF
        uses: actions/checkout@v4
        with:
          repository: {dhf_repo}
          path: dhf
          token: ${{{{ secrets.DHF_REPO_TOKEN }}}}

"""
        dhf_path_arg = "--dhf dhf/DHF"
        install_dhf = "          pip install -e dhf/\n"

    return f"""\
name: Engineering Control CI

on:
  push:
    branches: [ main ]
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read

jobs:
  test-coverage:
    name: Test Coverage Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install test dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest
          # Add your project's own test dependencies here, e.g.:
          # pip install -e .

      - name: Run product tests
        run: |
          # Replace with your actual test runner command.
          # Must output JUnit XML to test-results/ for ci test-coverage.
          mkdir -p test-results/
          pytest tests/ -v --junitxml=test-results/product-test-results.xml

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: product-test-results
          path: test-results/

{checkout_dhf}{install_dhf}      - name: Install CompliantFlow
        run: |
          # Install from GitHub Releases (public repo — no token needed).
          gh release download {version} --repo compliantflow/compliantflow --pattern "compliantflow-*.whl"
          pip install compliantflow-*.whl

      - name: Download test results
        if: always()
        uses: actions/download-artifact@v4
        with:
          name: product-test-results
          path: test-results/

      - name: Run test-coverage gate
        run: |
          compliantflow {dhf_path_arg} ci test-coverage \\
            --junit-dir test-results

{('  evidence-bundle:\n'
 '    name: Evidence Bundle\n'
 '    runs-on: ubuntu-latest\n'
 '    needs: [test-coverage]\n'
 '    if: github.event_name == \'push\' && github.ref == \'refs/heads/main\' && !cancelled()\n'
 '    steps:\n'
 '      - uses: actions/checkout@v4\n'
 f'{checkout_dhf}{install_dhf}      - name: Install CompliantFlow\n'
 '        run: |\n'
 f'          gh release download {version} --repo compliantflow/compliantflow --pattern "compliantflow-*.whl"\n'
 '          pip install compliantflow-*.whl\n'
 '      - name: Download test evidence\n'
 '        uses: actions/download-artifact@v4\n'
 '        with:\n'
 '          path: test-results/\n'
 '\n'
 '      - name: Generate evidence bundle\n'
 '        run: |\n'
 f'          compliantflow {dhf_path_arg} ci evidence bundle \\\n'
 '            --out-dir dhf-artifacts \\\n'
 '            --junit-dir test-results\n'
 '\n'
 '      - name: Upload evidence bundle\n'
 '        uses: actions/upload-artifact@v4\n'
 '        with:\n'
 '          name: dhf-artifacts\n'
 '          path: dhf-artifacts/\n') if dhf_repo else ''}"""


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run_init() -> None:
    """Interactive onboarding: scaffold product repo, optionally fetch DHF template."""
    click.echo()
    click.secho("CompliantFlow Setup", bold=True)
    click.echo("━" * 45)
    click.echo()

    # ── GitHub repo names ──
    click.secho("GitHub", bold=True)
    owner = click.prompt("  Org or username")
    product_name = click.prompt("  Product repository name (no org prefix)")
    product_repo = f"{owner}/{product_name}"
    click.echo()

    # ── DHF ─────────────────────────────────────────────────
    click.secho("DHF Repository", bold=True)
    setup_dhf = click.confirm("  Set up a DHF repository? (fetches template from CompliantFlow-DHF)", default=True)
    dhf_repo: Optional[str] = None
    dhf_dir: Optional[Path] = None
    dhf_template_ref: str = DEFAULT_TEMPLATE_REF
    if setup_dhf:
        dhf_name = click.prompt("  DHF repository name", default=f"{product_name}-dhf")
        dhf_repo = f"{owner}/{dhf_name}"
        dhf_dir = Path(click.prompt("  Local directory for DHF files", default=f"./{dhf_name}"))
        dhf_template_ref = click.prompt(
            "  DHF template version (branch or tag)",
            default=DEFAULT_TEMPLATE_REF,
            show_default=True,
        )
    click.echo()

    # ── Local path for product repo ──────────────────────────
    click.secho("Local Directories", bold=True)
    product_dir = Path(click.prompt("  Product repo local directory", default=f"./{product_name}"))
    click.echo()

    # ── Project ─────────────────────────────────────────────
    click.secho("Project", bold=True)
    default_proj = product_name.replace("-", " ").replace("_", " ").title()
    project_name = click.prompt("  Project name (used in DHF documents)", default=default_proj)
    click.echo()

    # ── Summary ─────────────────────────────────────────────
    click.secho("Summary", bold=True)
    click.echo("━" * 45)
    if setup_dhf:
        click.echo(f"  • Fetch DHF template from CompliantFlow-DHF (ref: {dhf_template_ref})")
        click.echo(f"  • Write to: {dhf_dir}")
        click.echo(f"    Project: \"{project_name}\"")
    click.echo(f"  • Write CLAUDE.md to: {product_dir}/")
    click.echo(f"  • Write engineering-control.yml to: {product_dir / '.github' / 'workflows'}/")
    click.echo(f"  • Write cr-complete.yml to: {product_dir / '.github' / 'workflows'}/")
    click.echo()

    if not click.confirm("Proceed?", default=True):
        raise click.Abort()

    click.echo()

    # ── Execute ─────────────────────────────────────────────
    steps: list[str] = []
    if setup_dhf:
        steps.append(f"Fetch DHF template to {dhf_dir}")
    steps.append("Write CLAUDE.md to product repo")
    steps.append("Write engineering-control.yml")
    steps.append("Write CR completion workflow")
    total = len(steps)
    n = 0

    def _step(msg: str) -> None:
        nonlocal n
        n += 1
        click.echo(f"[{n}/{total}] {msg}...", nl=False)

    if setup_dhf:
        _step(f"Fetch DHF template to {dhf_dir}")
        _fetch_dhf_template(dhf_dir, dhf_template_ref)  # type: ignore[arg-type]
        _replace_placeholders(dhf_dir, project_name, product_repo)  # type: ignore[arg-type]
        click.secho(" ✓", fg="green")

    _step("Write CLAUDE.md to product repo")
    _write_claude_md(product_dir, project_name, dhf_repo)
    click.secho(" ✓", fg="green")

    _step("Write engineering-control.yml")
    _write_engineering_control_yml(product_dir, dhf_repo)
    click.secho(" ✓", fg="green")

    _step("Write CR completion workflow")
    _write_cr_complete_yml(product_dir, dhf_repo)
    click.secho(" ✓", fg="green")

    # ── Done ────────────────────────────────────────────────
    click.echo()
    click.echo("━" * 45)
    click.secho("Done. Next steps:", bold=True, fg="green")
    click.echo()
    n = 1
    if setup_dhf:
        click.secho(f"  {n}. Push DHF repo to GitHub:", bold=True)
        click.echo(f"       cd {dhf_dir}")
        click.echo(f"       git init && git remote add origin https://github.com/{dhf_repo}")
        click.echo(f"       git add -A && git commit -m \"feat: initialize DHF for {project_name}\"")
        click.echo(f"       git push -u origin main")
        n += 1
    click.secho(f"  {n}. Open engineering control PR:", bold=True)
    click.echo(f"       cd {product_dir}")
    click.echo(f"       git checkout -b compliantflow/setup")
    workflow_file = ".github/workflows/engineering-control.yml"
    click.echo(f"       git add CLAUDE.md {workflow_file} .github/workflows/cr-complete.yml")
    click.echo(f"       git commit -m \"feat: add CompliantFlow harness and CI workflows\"")
    click.echo(f"       git push -u origin compliantflow/setup")
    n += 1
    click.secho(f"  {n}. Add secrets to {product_repo} → Settings → Secrets:", bold=True)
    if setup_dhf:
        click.echo(f"       DHF_REPO_TOKEN — fine-grained PAT with contents:read on {dhf_repo}")
    else:
        click.echo(f"       (no secrets required for the baseline OSS path)")
    n += 1
    click.secho(f"  {n}. Fill in your documentation:", bold=True)
    click.echo(f"       See README.md and GETTING_STARTED.md for project guidance.")
    click.echo(f"       Treat the DHF-side CRS, architecture spec, and development plan as the canonical formal docs.")
