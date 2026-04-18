"""compliantflow init — interactive onboarding command.

Sets up the full CompliantFlow infrastructure for a new project:
  1. Creates a private DHF repository from the built-in template (optional)
  2. Opens a pull request in the product repo adding the compliance CI gate
  3. Configures LLM secrets for AI-assisted checks (optional)
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
import tempfile
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Optional

import click

TEMPLATE_DIR = Path(__file__).parent / "data" / "dhf-template"

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
# gh CLI helpers
# ---------------------------------------------------------------------------

def _gh(*args: str, input: Optional[str] = None, check: bool = True) -> str:
    """Run a gh CLI command and return stdout. Raises ClickException on failure."""
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            input=input,
            check=check,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        raise click.ClickException(
            "'gh' CLI not found. Install the GitHub CLI (https://cli.github.com) and authenticate with 'gh auth login'."
        )
    except subprocess.CalledProcessError as exc:
        msg = exc.stderr.strip() or exc.stdout.strip()
        raise click.ClickException(f"gh command failed: {msg}")


def _detect_gh_owner() -> Optional[str]:
    try:
        return _gh("api", "user", "--jq", ".login", check=True)
    except click.ClickException:
        return None


def _repo_exists(repo: str) -> bool:
    try:
        _gh("api", f"repos/{repo}", check=True)
        return True
    except click.ClickException:
        return False


# ---------------------------------------------------------------------------
# DHF repo setup
# ---------------------------------------------------------------------------

def _create_dhf_repo(dhf_repo: str, project_name: str) -> None:
    _gh(
        "repo", "create", dhf_repo,
        "--private",
        "--description", f"Design History File for {project_name}",
    )


def _init_dhf_template(dhf_repo: str, project_name: str, standards: list[str]) -> None:
    """Clone the new empty repo, populate with DHF template, and push."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = Path(tmp) / "repo"

        # Clone (empty repo — no --depth needed)
        subprocess.run(
            ["gh", "repo", "clone", dhf_repo, str(repo_dir)],
            check=True, capture_output=True,
        )

        # Copy template contents (excludes .github — added separately below)
        shutil.copytree(
            TEMPLATE_DIR,
            repo_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )

        # Set project_name in global.yaml
        global_yaml = repo_dir / "DHF" / "config" / "global.yaml"
        content = global_yaml.read_text()
        content = content.replace(
            'project_name: "My Medical Device Software"',
            f'project_name: "{project_name}"',
        )
        global_yaml.write_text(content)

        # Remove governance files for unselected standards
        gov_dir = repo_dir / "governance"
        for std_id, filename in GOVERNANCE_FILES.items():
            if std_id not in standards:
                f = gov_dir / filename
                if f.exists():
                    f.unlink()
        # Remove the 'Standard' directory placeholder if present
        standard_dir = gov_dir / "Standard"
        if standard_dir.exists():
            shutil.rmtree(standard_dir)

        # Write DHF repo CI workflows
        gh_workflows = repo_dir / ".github" / "workflows"
        gh_workflows.mkdir(parents=True, exist_ok=True)
        _write_dhf_ci_workflow(gh_workflows / "ci.yml")
        _write_dhf_cr_transition_workflow(gh_workflows / "cr-transition.yml")

        # git commit and push
        subprocess.run(["git", "config", "user.email", "compliantflow-init@noreply"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "CompliantFlow Init"], cwd=repo_dir, check=True)
        subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"feat: initialize DHF for {project_name}"],
            cwd=repo_dir, check=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True)


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
        run: pip install click jinja2 markdown pydantic PyYAML
      - name: Validate DHF schema
        run: |
          export PYTHONPATH="${PYTHONPATH}:${PWD}:${PWD}/DHF"
          python -m utils validate schema
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
          - closed
          - planned
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
            python -m utils item transition "$CR_ID" "$TO_STATE" --by "$TRIGGERED_BY"
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
          gh release download {version} --repo itercharles/CompliantFlow \\
            --pattern "compliantflow-*.zip" \\
            --output compliantflow.zip
          unzip compliantflow.zip -d cf
          pip install cf/*/build/compliantflow-*.whl

      - name: Compliance gate
{env_block}        run: |
{pythonpath}          compliantflow {dhf_flag} validate traceability
{compliance_checks}
          compliantflow {dhf_flag} validate coverage UC:CRS CRS:SYS SYS:SRS
"""


# ---------------------------------------------------------------------------
# Product repo PR
# ---------------------------------------------------------------------------

def _open_compliance_pr_v2(
    product_repo: str,
    dhf_repo: Optional[str],
    standards: list[str],
    llm_provider: Optional[str],
) -> str:
    """Create branch, add compliance.yml, open PR. Returns PR URL."""
    workflow_content = _generate_compliance_yaml(dhf_repo, standards, llm_provider)
    encoded = base64.b64encode(workflow_content.encode()).decode()

    # Get default branch and its latest SHA
    default_branch = _gh("api", f"repos/{product_repo}", "--jq", ".default_branch")
    branch_sha = _gh(
        "api", f"repos/{product_repo}/git/ref/heads/{default_branch}",
        "--jq", ".object.sha",
    )

    branch_name = "compliantflow/setup"

    # Create branch (ignore if already exists)
    try:
        _gh(
            "api", f"repos/{product_repo}/git/refs",
            "--method", "POST",
            "--field", f"ref=refs/heads/{branch_name}",
            "--field", f"sha={branch_sha}",
        )
    except click.ClickException:
        pass

    # Create or update file
    file_path = ".github/workflows/compliance.yml"
    payload: dict = {
        "message": "feat(compliantflow): add compliance gate workflow",
        "content": encoded,
        "branch": branch_name,
    }
    try:
        existing_sha = _gh(
            "api", f"repos/{product_repo}/contents/{file_path}?ref={branch_name}",
            "--jq", ".sha",
        )
        payload["sha"] = existing_sha
    except click.ClickException:
        pass

    _gh(
        "api", f"repos/{product_repo}/contents/{file_path}",
        "--method", "PUT",
        "--input", "-",
        input=json.dumps(payload),
    )

    # Open PR
    pr_body = (
        "## CompliantFlow Compliance Gate\n\n"
        "This PR adds the compliance CI gate.\n\n"
        "**Required secrets after merging:**\n"
        "- `COMPLIANTFLOW_TOKEN` — from your account representative\n"
    )
    if dhf_repo:
        pr_body += f"- `DHF_REPO_TOKEN` — fine-grained PAT with `contents: read` on `{dhf_repo}`\n"
    if llm_provider == "gemini":
        pr_body += "- `GEMINI_API_KEY` — already configured via this setup\n"
    elif llm_provider == "ollama":
        pr_body += "- `COMPLIANTFLOW_OLLAMA_URL` — already configured via this setup\n"

    try:
        raw = _gh(
            "api", f"repos/{product_repo}/pulls",
            "--method", "POST",
            "--input", "-",
            input=json.dumps({
                "title": "feat: add CompliantFlow compliance gate",
                "head": branch_name,
                "base": default_branch,
                "body": pr_body,
            }),
        )
        return json.loads(raw).get("html_url", f"https://github.com/{product_repo}/pulls")
    except click.ClickException:
        return f"https://github.com/{product_repo}/pulls"


# ---------------------------------------------------------------------------
# Secret management
# ---------------------------------------------------------------------------

def _set_secret(repo: str, name: str, value: str) -> None:
    _gh("secret", "set", name, "--repo", repo, "--body", value)


# ---------------------------------------------------------------------------
# Main interactive entrypoint
# ---------------------------------------------------------------------------

def run_init() -> None:
    """Interactive onboarding: set up the full CompliantFlow infrastructure."""
    click.echo()
    click.secho("CompliantFlow Setup", bold=True)
    click.echo("━" * 45)
    click.echo()

    # ── GitHub ──────────────────────────────────────────────
    click.secho("GitHub", bold=True)
    default_owner = _detect_gh_owner()
    owner = click.prompt("  Org or username", default=default_owner or "")
    product_name = click.prompt("  Product repository name (no org prefix)")
    product_repo = f"{owner}/{product_name}"
    click.echo()

    # ── Project ─────────────────────────────────────────────
    click.secho("Project", bold=True)
    default_proj = product_name.replace("-", " ").replace("_", " ").title()
    project_name = click.prompt("  Project name (used in DHF documents)", default=default_proj)
    click.echo()

    # ── DHF ─────────────────────────────────────────────────
    click.secho("DHF Repository", bold=True)
    setup_dhf = click.confirm("  Create and initialise a DHF repository?", default=True)
    dhf_repo: Optional[str] = None
    if setup_dhf:
        dhf_name = click.prompt("  DHF repository name", default=f"{product_name}-dhf")
        dhf_repo = f"{owner}/{dhf_name}"
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
    enable_llm = click.confirm(
        "  Enable AI-assisted PR review and semantic compliance checks?", default=True
    )
    llm_provider: Optional[str] = None
    llm_key: Optional[str] = None
    llm_url: Optional[str] = None
    if enable_llm:
        provider = click.prompt(
            "  LLM provider",
            type=click.Choice(["gemini", "ollama", "skip"]),
            default="gemini",
        )
        if provider == "gemini":
            llm_provider = "gemini"
            llm_key = click.prompt("  Gemini API key", hide_input=True)
        elif provider == "ollama":
            llm_provider = "ollama"
            llm_url = click.prompt("  Ollama base URL", default="http://localhost:11434")
    click.echo()

    # ── Summary ─────────────────────────────────────────────
    click.secho("Summary", bold=True)
    click.echo("━" * 45)
    if setup_dhf:
        click.echo(f"  • Create private DHF repo: {dhf_repo}")
        click.echo(f"  • Initialise DHF: \"{project_name}\"")
        click.echo(f"    Standards: {', '.join(selected_standards)}")
    click.echo(f"  • Open compliance PR in: {product_repo}")
    if llm_provider == "gemini":
        click.echo(f"  • Set GEMINI_API_KEY in {product_repo}")
    elif llm_provider == "ollama":
        click.echo(f"  • Set COMPLIANTFLOW_OLLAMA_URL in {product_repo}")
    click.echo()

    if not click.confirm("Proceed?", default=True):
        raise click.Abort()

    click.echo()

    # ── Execute ─────────────────────────────────────────────
    steps: list[str] = []
    if setup_dhf:
        steps += ["Create DHF repository", "Initialise DHF template"]
    steps.append(f"Open compliance PR in {product_repo}")
    if llm_key or llm_url:
        steps.append("Configure repository secrets")

    total = len(steps)
    n = 0

    def _step(msg: str) -> None:
        nonlocal n
        n += 1
        click.echo(f"[{n}/{total}] {msg}...", nl=False)

    if setup_dhf:
        _step(f"Create DHF repository {dhf_repo}")
        _create_dhf_repo(dhf_repo, project_name)  # type: ignore[arg-type]
        click.secho(" ✓", fg="green")

        _step("Initialise DHF template")
        _init_dhf_template(dhf_repo, project_name, selected_standards)  # type: ignore[arg-type]
        click.secho(" ✓", fg="green")

    _step(f"Open compliance PR in {product_repo}")
    pr_url = _open_compliance_pr_v2(product_repo, dhf_repo, selected_standards, llm_provider)
    click.secho(f" ✓", fg="green")

    if llm_key or llm_url:
        _step("Configure repository secrets")
        if llm_key:
            _set_secret(product_repo, "GEMINI_API_KEY", llm_key)
        if llm_url:
            _set_secret(product_repo, "COMPLIANTFLOW_OLLAMA_URL", llm_url)
        click.secho(" ✓", fg="green")

    # ── Done ────────────────────────────────────────────────
    click.echo()
    click.echo("━" * 45)
    click.secho("Setup complete!", bold=True, fg="green")
    click.echo()
    click.secho("Next steps:", bold=True)
    n = 1
    click.echo(f"  {n}. Add COMPLIANTFLOW_TOKEN to {product_repo} secrets")
    click.echo("     (provided by your account representative)")
    n += 1
    if setup_dhf:
        click.echo(f"  {n}. Create a fine-grained PAT with 'Contents: Read' access to {dhf_repo}")
        click.echo(f"     and add it as DHF_REPO_TOKEN to {product_repo} secrets")
        n += 1
    click.echo(f"  {n}. Review and merge the compliance PR:")
    click.echo(f"     {pr_url}")
    n += 1
    if setup_dhf:
        click.echo(f"  {n}. Open your DHF in Claude Code:")
        click.echo(f"     gh repo clone {dhf_repo} && cd {dhf_repo.split('/')[-1]} && claude")
