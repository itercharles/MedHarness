"""medharness init — interactive onboarding command.

Sets up MedHarness infrastructure for a new project:
  1. Optionally scaffolds a DHF repo from local templates/
  2. Writes product repo files (CLAUDE.md, engineering-control.yml, cr-complete.yml)
  3. Prints git commands to push both repos and open a PR
"""

from __future__ import annotations

import shutil
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Optional

import click

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "dhfkit" / "templates"


# ---------------------------------------------------------------------------
# DHF scaffold — copies from local templates/ (no remote fetch)
# ---------------------------------------------------------------------------

def _scaffold_dhf(dhf_dir: Path) -> None:
    """Create a DHF project directory from the bundled template assets.

    Copies config, spec templates, plan templates, GitHub Actions workflows,
    and creates empty item directories for each configured doc type.
    """
    dhf_dir.mkdir(parents=True, exist_ok=True)

    def _cp(rel_src: str, rel_dst: str) -> None:
        src = _TEMPLATES_DIR / rel_src
        dst = dhf_dir / rel_dst
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

    # Config skeletons
    _cp("config", "DHF/config")

    # Spec templates (Jinja2 .j2 + CSS styles)
    _cp("specs", "DHF/documents/specs")

    # Plan templates
    _cp("plans", "DHF/documents/plans")

    # Starter sample items (one per doc type)
    _cp("items", "DHF/items")

    # GitHub Actions workflows for the generated DHF repo
    _cp("github/prompts", ".github/prompts")
    _cp("github/workflows/dhf", ".github/workflows")

    # Root README (the DHF starter readme from templates/)
    _cp("README.md", "README.md")

    # AI harness context for CI agents and interactive skills
    _cp("AI-harness", "AI-harness")

    # Create empty test-results dir with .gitkeep
    results_dir = dhf_dir / "DHF" / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / ".gitkeep").touch(exist_ok=True)


def _replace_placeholders(dhf_dir: Path, project_name: str, product_repo: Optional[str]) -> None:
    """Substitute placeholders in the scaffolded DHF content."""
    dhf_repo_name = (product_repo.split("/", 1)[1] + "-dhf"
                     if product_repo and "/" in product_repo else "your-product-dhf")
    github_org = (product_repo.split("/", 1)[0]
                  if product_repo and "/" in product_repo else "your-org")

    text_extensions = {".md", ".yaml", ".yml", ".j2", ".css", ".txt", ".gitkeep"}

    for path in dhf_dir.rglob("*"):
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
        text = text.replace("{{product_repo}}", product_repo or "your-org/your-product")
        text = text.replace("{{product_repo_name}}",
                            product_repo.split("/", 1)[1] if product_repo and "/" in product_repo else "your-product")
        text = text.replace("{{github_org}}", github_org)
        text = text.replace("{{dhf_repo_name}}", dhf_repo_name)
        text = text.replace("{{primary_test_tool}}", "pytest")
        text = text.replace("{{medharness_version}}", pkg_version("medharness"))
        text = text.replace("{{medharness_repo}}", "itercharles/MedHarness")
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
- DHF mutations go through `medharness dhf item` in the DHF repo
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


def _render_product_workflow(dhf_repo: Optional[str], template_filename: str) -> str:
    """Read a product workflow template and substitute placeholders."""
    template_path = _TEMPLATES_DIR / "github" / "workflows" / "product" / template_filename
    text = template_path.read_text(encoding="utf-8")
    if dhf_repo and "/" in dhf_repo:
        github_org = dhf_repo.split("/", 1)[0]
        dhf_repo_name = dhf_repo.split("/", 1)[1]
    else:
        github_org = "your-org"
        dhf_repo_name = "your-product-dhf"
    return text.replace("{{github_org}}", github_org).replace("{{dhf_repo_name}}", dhf_repo_name)


def _write_cr_complete_yml(product_dir: Path, dhf_repo: Optional[str]) -> Path:
    dest = product_dir / ".github" / "workflows" / "cr-complete.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_render_product_workflow(dhf_repo, "cr-complete.yml"))
    return dest


def _write_review_pr_yml(product_dir: Path, dhf_repo: Optional[str]) -> Path:
    dest = product_dir / ".github" / "workflows" / "review-pr.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_render_product_workflow(dhf_repo, "review-pr.yml"))
    return dest


def _write_skills(product_dir: Path, project_name: str, dhf_repo: Optional[str]) -> list[Path]:
    """Copy skill templates into the product repo's .claude/skills/ directory."""
    skills_src = _TEMPLATES_DIR / "product" / ".claude" / "skills"
    if not skills_src.exists():
        return []
    skills_dst = product_dir / ".claude" / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)
    written = []
    for skill_dir in skills_src.iterdir():
        if not skill_dir.is_dir():
            continue
        dst_skill = skills_dst / skill_dir.name
        shutil.copytree(skill_dir, dst_skill, dirs_exist_ok=True)
        skill_md = dst_skill / "SKILL.md"
        if skill_md.exists():
            text = skill_md.read_text()
            text = text.replace("{{project_name}}", project_name)
            text = text.replace("{{product_repo}}", dhf_repo or "your-org/your-product-dhf")
            skill_md.write_text(text)
        written.append(dst_skill)
    return written


# ---------------------------------------------------------------------------
# Engineering control workflow generation
# ---------------------------------------------------------------------------

def _cf_version() -> str:
    try:
        return f"v{pkg_version('medharness')}"
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

    evidence_block = (
        '  evidence-bundle:\n'
        '    name: Evidence Bundle\n'
        '    runs-on: ubuntu-latest\n'
        '    needs: [test-coverage]\n'
        f'    if: github.event_name == {chr(39)}push{chr(39)} && github.ref == {chr(39)}refs/heads/main{chr(39)} && !cancelled()\n'
        '    steps:\n'
        '      - uses: actions/checkout@v4\n'
        f'{checkout_dhf}{install_dhf}      - name: Install MedHarness\n'
        '        run: |\n'
        f'          gh release download {version} --repo {{github_org}}/{{dhf_repo_name}} --pattern "medharness-*.whl"\n'
        '          pip install medharness-*.whl\n'
        '      - name: Download test evidence\n'
        '        uses: actions/download-artifact@v4\n'
        '        with:\n'
        '          path: test-results/\n'
        '\n'
        '      - name: Generate evidence bundle\n'
        '        run: |\n'
        f'          medharness {dhf_path_arg} ci evidence bundle \\\n'
        '            --out-dir dhf-artifacts \\\n'
        '            --junit-dir test-results\n'
        '\n'
        '      - name: Upload evidence bundle\n'
        '        uses: actions/upload-artifact@v4\n'
        '        with:\n'
        '          name: dhf-artifacts\n'
        '          path: dhf-artifacts/\n'
    ) if dhf_repo else ''

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

{checkout_dhf}{install_dhf}      - name: Install MedHarness
        run: |
          # Install from GitHub Releases (public repo — no token needed).
          gh release download {version} --repo {{github_org}}/{{dhf_repo_name}} --pattern "medharness-*.whl"
          pip install medharness-*.whl

      - name: Download test results
        if: always()
        uses: actions/download-artifact@v4
        with:
          name: product-test-results
          path: test-results/

      - name: Run test-coverage gate
        run: |
          medharness {dhf_path_arg} ci test-coverage \\
            --junit-dir test-results

{evidence_block}"""


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run_init() -> None:
    """Interactive onboarding: scaffold product repo, optionally scaffold DHF repo."""
    click.echo()
    click.secho("MedHarness Setup", bold=True)
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
    setup_dhf = click.confirm("  Set up a DHF repository? (scaffolds from bundled templates)", default=True)
    dhf_repo: Optional[str] = None
    dhf_dir: Optional[Path] = None
    if setup_dhf:
        dhf_name = click.prompt("  DHF repository name", default=f"{product_name}-dhf")
        dhf_repo = f"{owner}/{dhf_name}"
        dhf_dir = Path(click.prompt("  Local directory for DHF files", default=f"./{dhf_name}"))
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
        click.echo(f"  • Scaffold DHF repo from bundled templates")
        click.echo(f"  • Write to: {dhf_dir}")
        click.echo(f"    Project: \"{project_name}\"")
    click.echo(f"  • Write CLAUDE.md to: {product_dir}/")
    click.echo(f"  • Write engineering-control.yml to: {product_dir / '.github' / 'workflows'}/")
    click.echo(f"  • Write cr-complete.yml to: {product_dir / '.github' / 'workflows'}/")
    click.echo(f"  • Write review-pr.yml to: {product_dir / '.github' / 'workflows'}/")
    click.echo()

    if not click.confirm("Proceed?", default=True):
        raise click.Abort()

    click.echo()

    # ── Execute ─────────────────────────────────────────────
    steps: list[str] = []
    if setup_dhf:
        steps.append(f"Scaffold DHF repo to {dhf_dir}")
    steps.append("Write CLAUDE.md to product repo")
    steps.append("Write engineering-control.yml")
    steps.append("Write CR completion workflow")
    steps.append("Write PR review workflow")
    steps.append("Write Claude Code skills")
    total = len(steps)
    n = 0

    def _step(msg: str) -> None:
        nonlocal n
        n += 1
        click.echo(f"[{n}/{total}] {msg}...", nl=False)

    if setup_dhf:
        _step(f"Scaffold DHF repo to {dhf_dir}")
        _scaffold_dhf(dhf_dir)  # type: ignore[arg-type]
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

    _step("Write PR review workflow")
    _write_review_pr_yml(product_dir, dhf_repo)
    click.secho(" ✓", fg="green")

    _step("Write Claude Code skills")
    _write_skills(product_dir, project_name, dhf_repo)
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
    click.echo(f"       git checkout -b medharness/setup")
    workflow_file = ".github/workflows/engineering-control.yml"
    click.echo(f"       git add CLAUDE.md {workflow_file} .github/workflows/cr-complete.yml .github/workflows/review-pr.yml")
    click.echo(f"       git commit -m \"feat: add MedHarness harness and CI workflows\"")
    click.echo(f"       git push -u origin medharness/setup")
    n += 1
    click.secho(f"  {n}. Add secrets to {product_repo} → Settings → Secrets:", bold=True)
    if setup_dhf:
        click.echo(f"       DHF_REPO_TOKEN — fine-grained PAT with contents:read on {dhf_repo}")
    else:
        click.echo(f"       (no secrets required for the baseline OSS path)")
    n += 1
    click.secho(f"  {n}. Fill in your project content:", bold=True)
    click.echo(f"       The scaffolded DHF contains starter sample items and templates.")
    click.echo(f"       Replace all sample content with your project's real requirements,")
    click.echo(f"       architecture, risks, and plans before using for a real product.")
