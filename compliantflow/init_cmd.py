"""compliantflow init — interactive onboarding command.

Sets up the full CompliantFlow infrastructure for a new project:
  1. Writes the DHF template to a local directory for review
  2. Writes product repo workflows to the product repo directory for review
  3. Prints git commands to push both repos and open a PR
"""

from __future__ import annotations

import shutil
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Optional

import click

TEMPLATE_DIR = Path(__file__).parent / "data" / "dhf-template"
PRODUCT_TEMPLATE_DIR = Path(__file__).parent / "data" / "product-template"
HARNESS_DIR = Path(__file__).parent.parent / "AI-harness"

# Map standard IDs to governance filenames (all present in template)
GOVERNANCE_FILES = {
    "IEC_62304": "IEC_62304.yaml",
    "ISO_14971": "ISO_14971.yaml",
    "IEC_82304_1": "IEC_82304_1.yaml",
    "ISO_13485": "ISO_13485.yaml",
}

STANDARD_LABELS = {
    "IEC_62304": "IEC 62304  — Medical device software lifecycle",
    "ISO_14971": "ISO 14971  — Risk management",
    "IEC_82304_1": "IEC 82304-1 — Health software",
    "ISO_13485": "ISO 13485  — Quality management system",
}


# ---------------------------------------------------------------------------
# Local file writers
# ---------------------------------------------------------------------------

def _replace_placeholders_in_tree(root: Path, replacements: dict[str, str]) -> None:
    """Replace placeholder strings in text files under root, skipping binary assets."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)
        path.write_text(text)


def _init_dhf_template(
    dhf_dir: Path,
    project_name: str,
    standards: list[str],
    product_repo: Optional[str] = None,
) -> None:
    """Populate dhf_dir with the DHF template. No git operations — caller reviews and pushes."""
    dhf_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        TEMPLATE_DIR,
        dhf_dir,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )

    _replace_placeholders_in_tree(
        dhf_dir,
        {
            "{{project_name}}": project_name,
            "{{product_repo}}": product_repo or "your-org/your-product",
            "{{product_repo_name}}": (
                product_repo.split("/", 1)[1] if product_repo and "/" in product_repo else "your-product"
            ),
        },
    )

    # Set project_name in global.yaml
    global_yaml = dhf_dir / "DHF" / "config" / "global.yaml"
    content = global_yaml.read_text()
    content = content.replace(
        'project_name: "My Medical Device Software"',
        f'project_name: "{project_name}"',
    )
    global_yaml.write_text(content)

    # Remove governance files for unselected standards
    gov_dir = dhf_dir / "governance"
    for std_id, filename in GOVERNANCE_FILES.items():
        if std_id not in standards:
            f = gov_dir / filename
            if f.exists():
                f.unlink()
    standard_dir = gov_dir / "Standard"
    if standard_dir.exists():
        shutil.rmtree(standard_dir)

    # Write DHF repo CI workflows
    gh_workflows = dhf_dir / ".github" / "workflows"
    gh_workflows.mkdir(parents=True, exist_ok=True)
    _write_dhf_ci_workflow(gh_workflows / "ci.yml")
    _write_dhf_cr_transition_workflow(gh_workflows / "cr-transition.yml")


def _init_product_template(
    product_dir: Path,
    project_name: str,
    dhf_repo: Optional[str],
    standards: list[str],
) -> None:
    """Write AI-harness and docs/ scaffolding to product_dir. No git operations — caller reviews and pushes."""
    dhf_repo_value = dhf_repo or "your-org/your-product-dhf"
    standards_value = ", ".join(STANDARD_LABELS.get(s, s) for s in standards)
    replacements = {
        "{{project_name}}": project_name,
        "{{dhf_repo}}": dhf_repo_value,
        "{{standards}}": standards_value,
    }

    ai_harness_src = HARNESS_DIR
    ai_harness_dst = product_dir / "AI-harness"
    shutil.copytree(ai_harness_src, ai_harness_dst, dirs_exist_ok=True)
    _replace_placeholders_in_tree(ai_harness_dst, replacements)

    docs_src = PRODUCT_TEMPLATE_DIR / "docs"
    docs_dst = product_dir / "docs"
    shutil.copytree(docs_src, docs_dst, dirs_exist_ok=True)
    _replace_placeholders_in_tree(docs_dst, replacements)


def _write_compliance_yml(
    product_dir: Path,
    dhf_repo: Optional[str],
    standards: list[str],
    llm_provider: Optional[str],
) -> Path:
    """Write compliance.yml into product_dir. Returns the file path."""
    dest = product_dir / ".github" / "workflows" / "compliance.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_generate_compliance_yaml(dhf_repo, standards, llm_provider))
    return dest


def _write_cr_complete_yml(product_dir: Path, dhf_repo: Optional[str]) -> Path:
    """Write the CR completion workflow into the product repo."""
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

      - name: Install DHF workflow dependencies
        if: steps.cr.outputs.skip != 'true'
        run: |
          python -m pip install --upgrade pip
          pip install -r dhf/requirements.txt
          pip install -e dhf/ 2>/dev/null || true

      - name: Complete CR in DHF
        if: steps.cr.outputs.skip != 'true'
        run: |
          cd dhf
          git config user.name "GitHub Actions [bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          cd ..
          compliantflow cr workflow complete \\
            --dhf-repo dhf \\
            --cr "${{{{ steps.cr.outputs.cr_id }}}}" \\
            --by "github-actions[bot]" \\
            --push
""")
    return dest


def _write_dhf_ci_workflow(path: Path) -> None:
    path.write_text("""\
name: DHF CI

on:
  push:
    branches: [ main ]
  pull_request:
    types: [opened, synchronize]

jobs:
  utils-tests:
    name: DHF Utils Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install pytest click jinja2 markdown pydantic PyYAML gitpython
      - name: Run DHF utils tests
        run: |
          export PYTHONPATH="${PYTHONPATH}:${PWD}:${PWD}/DHF"
          pytest DHF/utils/tests/ -v

  schema-validation:
    name: Schema Validation
    runs-on: ubuntu-latest
    needs: utils-tests
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install click jinja2 markdown pydantic PyYAML gitpython
      - name: Validate DHF schema
        run: |
          export PYTHONPATH="${PYTHONPATH}:${PWD}:${PWD}/DHF"
          python -m dhf_util validate schema
""")


def _write_dhf_cr_transition_workflow(path: Path) -> None:
    path.write_text("""\
name: CR Lifecycle Transition

on:
  workflow_dispatch:
    inputs:
      cr_ids:
        description: "Space-separated CR IDs to transition (e.g. 'CR-001 CR-002')"
        required: true
        type: string
      to_state:
        description: "Target lifecycle state"
        required: true
        type: choice
        options:
          - new
          - analyzing
          - developing
          - completed
          - rejected
      triggered_by:
        description: "Who triggered this transition"
        required: false
        default: "Manual"
        type: string

jobs:
  transition:
    name: Transition CR(s) to ${{ inputs.to_state }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install click jinja2 markdown pydantic PyYAML gitpython
      - name: Transition CR(s)
        env:
          CR_IDS: ${{ inputs.cr_ids }}
          TO_STATE: ${{ inputs.to_state }}
          TRIGGERED_BY: ${{ inputs.triggered_by }}
        run: |
          export PYTHONPATH="${PYTHONPATH}:${PWD}:${PWD}/DHF"
          for CR_ID in $CR_IDS; do
            python -m dhf_util item transition "$CR_ID" "$TO_STATE" --by "$TRIGGERED_BY"
          done
      - name: Commit status changes
        run: |
          git config user.name "GitHub Actions [bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add DHF/items/
          if ! git diff --staged --quiet; then
            git commit -m "chore: transition ${{ inputs.cr_ids }} to ${{ inputs.to_state }} [skip ci]"
            git push
          fi
""")


# ---------------------------------------------------------------------------
# Compliance workflow generation
# ---------------------------------------------------------------------------

def _cf_version() -> str:
    try:
        return f"v{pkg_version('compliantflow')}"
    except Exception:
        return "latest"


def _generate_compliance_yaml(
    dhf_repo: Optional[str],
    standards: list[str],
    llm_provider: Optional[str],
) -> str:
    """Render the compliance.yml workflow content for the product repo."""
    version = _cf_version()

    checkout_dhf = ""
    pythonpath = ""
    dhf_flag = "--dhf DHF"

    if dhf_repo:
        checkout_dhf = f"""\
      - name: Check out DHF
        uses: actions/checkout@v4
        with:
          repository: {dhf_repo}
          path: dhf
          token: ${{{{ secrets.DHF_REPO_TOKEN }}}}

"""
        pythonpath = '          export PYTHONPATH="${PYTHONPATH}:${PWD}/dhf/DHF"\n'
        dhf_flag = "--dhf dhf/DHF"

    compliance_checks = "\n".join(
        f"          compliantflow {dhf_flag} validate compliance {std} \\\n"
        f"            --governance-dir {'dhf/' if dhf_repo else ''}governance"
        for std in standards
    )

    llm_env = ""
    if llm_provider == "gemini":
        llm_env = "          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}\n"
    elif llm_provider == "ollama":
        llm_env = "          COMPLIANTFLOW_OLLAMA_URL: ${{ secrets.COMPLIANTFLOW_OLLAMA_URL }}\n"

    env_block = f"        env:\n{llm_env}" if llm_env else ""

    return f"""\
name: Compliance Gate

on: [push, pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

{checkout_dhf}      - name: Install CompliantFlow
        env:
          GH_TOKEN: ${{{{ secrets.COMPLIANTFLOW_TOKEN }}}}
        run: |
          gh release download {version} --repo itercharles/CompliantFlow --pattern "compliantflow-*.zip" --output compliantflow.zip
          unzip compliantflow.zip -d cf
          pip install cf/*/compliantflow-*.whl

      - name: Compliance gate
{env_block}        run: |
{pythonpath}          compliantflow {dhf_flag} validate traceability
{compliance_checks}
          compliantflow {dhf_flag} validate coverage UC:CRS CRS:SYS SYS:SRS
"""


# ---------------------------------------------------------------------------
# Main interactive entrypoint
# ---------------------------------------------------------------------------

def run_init() -> None:
    """Interactive onboarding: set up the full CompliantFlow infrastructure."""
    click.echo()
    click.secho("CompliantFlow Setup", bold=True)
    click.echo("━" * 45)
    click.echo()

    # ── GitHub repo names (for compliance.yml content only) ──
    click.secho("GitHub", bold=True)
    owner = click.prompt("  Org or username")
    product_name = click.prompt("  Product repository name (no org prefix)")
    product_repo = f"{owner}/{product_name}"
    click.echo()

    # ── DHF ─────────────────────────────────────────────────
    click.secho("DHF Repository", bold=True)
    setup_dhf = click.confirm("  Set up a DHF repository?", default=True)
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

    # ── Standards ───────────────────────────────────────────
    click.secho("Compliance Standards", bold=True)
    selected_standards: list[str] = []
    for std_id, label in STANDARD_LABELS.items():
        default_on = std_id in ("IEC_62304", "ISO_14971")
        if click.confirm(f"  {label}?", default=default_on):
            selected_standards.append(std_id)
    if not selected_standards:
        raise click.ClickException("At least one standard must be selected.")
    click.echo()

    # ── LLM ─────────────────────────────────────────────────
    click.secho("AI Compliance Checks (optional)", bold=True)
    llm_provider: Optional[str] = None
    if click.confirm("  Enable AI-assisted PR review and semantic compliance checks?", default=True):
        provider = click.prompt(
            "  LLM provider",
            type=click.Choice(["gemini", "ollama", "skip"]),
            default="gemini",
        )
        if provider == "gemini":
            llm_provider = "gemini"
        elif provider == "ollama":
            llm_provider = "ollama"
    click.echo()

    # ── Summary ─────────────────────────────────────────────
    click.secho("Summary", bold=True)
    click.echo("━" * 45)
    if setup_dhf:
        click.echo(f"  • Write DHF template to: {dhf_dir}")
        click.echo(f"    Project: \"{project_name}\"  Standards: {', '.join(selected_standards)}")
    click.echo(f"  • Write AI-harness to: {product_dir}/")
    click.echo(f"  • Write compliance.yml to: {product_dir / '.github' / 'workflows'}/")
    click.echo(f"  • Write cr-complete.yml to: {product_dir / '.github' / 'workflows'}/")
    click.echo()

    if not click.confirm("Proceed?", default=True):
        raise click.Abort()

    click.echo()

    # ── Execute ─────────────────────────────────────────────
    steps: list[str] = []
    if setup_dhf:
        steps.append(f"Write DHF template to {dhf_dir}")
    steps.append("Write AI-harness to product repo")
    steps.append("Write compliance.yml")
    steps.append("Write CR completion workflow")
    total = len(steps)
    n = 0

    def _step(msg: str) -> None:
        nonlocal n
        n += 1
        click.echo(f"[{n}/{total}] {msg}...", nl=False)

    if setup_dhf:
        _step(f"Write DHF template to {dhf_dir}")
        _init_dhf_template(
            dhf_dir,
            project_name,
            selected_standards,
            product_repo=product_repo,
        )  # type: ignore[arg-type]
        click.secho(" ✓", fg="green")

    _step("Write AI-harness to product repo")
    _init_product_template(product_dir, project_name, dhf_repo, selected_standards)
    click.secho(" ✓", fg="green")

    _step("Write compliance.yml")
    _write_compliance_yml(product_dir, dhf_repo, selected_standards, llm_provider)
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
    click.secho(f"  {n}. Open compliance PR:", bold=True)
    click.echo(f"       cd {product_dir}")
    click.echo(f"       git checkout -b compliantflow/setup")
    click.echo(f"       git add AI-harness/ .github/workflows/compliance.yml .github/workflows/cr-complete.yml")
    click.echo(f"       git commit -m \"feat: add CompliantFlow workflows and AI harness\"")
    click.echo(f"       git push -u origin compliantflow/setup")
    n += 1
    click.secho(f"  {n}. Add secrets to {product_repo} → Settings → Secrets:", bold=True)
    click.echo(f"       COMPLIANTFLOW_TOKEN  — from your account representative")
    if setup_dhf:
        click.echo(f"       DHF_REPO_TOKEN       — fine-grained PAT with contents:read on {dhf_repo}")
    if llm_provider == "gemini":
        click.echo(f"       GEMINI_API_KEY       — your Gemini API key")
    elif llm_provider == "ollama":
        click.echo(f"       COMPLIANTFLOW_OLLAMA_URL — your Ollama base URL")
    n += 1
    click.secho(f"  {n}. Fill in your strategy documents:", bold=True)
    click.echo(f"       {product_dir}/docs/product_strategy.md   — mission, objectives, target customer")
    click.echo(f"       {product_dir}/docs/product_roadmap.md    — milestone grouping and exit criteria")
    click.echo(f"       {product_dir}/docs/technical_strategy.md — architectural principles and guardrails")
    click.echo(f"       {product_dir}/docs/testing_strategy.md   — test layers and DHF traceability conventions")
    click.echo(f"       These are used by the AI agent for direction checks on every task.")
