"""CompliantFlow CLI — read-only analysis and traceability for CI/CD pipelines.

Data management (item CRUD, lifecycle transitions, schema validation,
doc generation) is handled by the utils CLI (python -m utils).
"""

import json
import os
import sys
from pathlib import Path

import click


def _resolve_dhf(dhf_option: str | None) -> Path:
    """Resolve the DHF directory from CLI option, env var, or default."""
    if dhf_option:
        return Path(dhf_option)
    env = os.environ.get("COMPLIANTFLOW_DHF")
    if env:
        return Path(env)
    return Path(__file__).parent.parent / "DHF"


def _make_core(ctx: click.Context):
    """Instantiate CompliantFlowCore from CLI context.

    Single-project mode (default): uses ``ctx.obj["dhf"]`` path with a
    ``LocalDHFAdapter`` (requires the DHF system to be installed alongside
    this tool, e.g. by cloning compliantflow-dhf into the Python path).

    Multi-project mode: activated when ``--project slug:path`` flags are
    present.  Builds a ``MultiDHFAdapter`` keyed by slug and passes it to
    ``CompliantFlowCore`` unchanged.
    """
    try:
        from utils.local_adapter import LocalDHFAdapter
    except ImportError:
        raise click.ClickException(
            "LocalDHFAdapter not found. Add your DHF system (e.g. compliantflow-dhf) "
            "to the Python path before running the CLI."
        )
    from compliantflow.core import CompliantFlowCore

    projects: dict = ctx.obj.get("projects", {})
    if projects:
        from compliantflow.adapters.multi import MultiDHFAdapter
        adapters = {slug: LocalDHFAdapter(path, auto_commit=False)
                    for slug, path in projects.items()}
        return CompliantFlowCore(MultiDHFAdapter(adapters))

    dhf_path: Path = ctx.obj["dhf"]
    return CompliantFlowCore(LocalDHFAdapter(dhf_path, auto_commit=False))


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.option(
    "--dhf",
    default=None,
    metavar="PATH",
    help="Path to the DHF directory. Overrides COMPLIANTFLOW_DHF env var.",
)
@click.option(
    "--project",
    "projects",
    multiple=True,
    metavar="SLUG:PATH",
    help=(
        "Add a project as slug:path. Repeat for multiple projects. "
        "When provided, --dhf is ignored and a MultiDHFAdapter is used. "
        "Example: --project device-a:/repo/a/DHF --project device-b:/repo/b/DHF"
    ),
)
@click.pass_context
def main(ctx: click.Context, dhf: str | None, projects: tuple) -> None:
    """CompliantFlow CLI — analysis and traceability for CI/CD pipelines."""
    ctx.ensure_object(dict)
    if projects:
        parsed: dict = {}
        for entry in projects:
            if ":" not in entry:
                raise click.BadParameter(
                    f"--project must be in slug:path format, got: {entry!r}",
                    param_hint="--project",
                )
            slug, path = entry.split(":", 1)
            parsed[slug.strip()] = Path(path.strip())
        ctx.obj["projects"] = parsed
    ctx.obj["dhf"] = _resolve_dhf(dhf)


# ---------------------------------------------------------------------------
# review-pr
# ---------------------------------------------------------------------------

@main.command("review-pr")
@click.option("--diff", "diff_file", default=None, metavar="FILE",
              help="Path to a unified diff file. Use '-' to read from stdin.")
@click.option("--pr", "pr_number", default=None, metavar="NUMBER",
              help="GitHub PR number. Fetches diff via 'gh pr diff'.")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Path to governance directory. Defaults to ./governance.")
@click.option("--post-comment", is_flag=True, default=False,
              help="Post the checklist as a GitHub PR comment (requires --pr and gh CLI).")
@click.pass_context
def review_pr(ctx: click.Context, diff_file: str | None, pr_number: str | None,
              governance_dir: str | None, post_comment: bool) -> None:
    """Analyse a PR diff and produce a DHF compliance action checklist.

    Suggestion layer only — no pass/fail exit code. The CI gate remains
    the authoritative compliance enforcer.

    \b
    Example:
      git diff main...HEAD | python -m compliantflow --dhf path/to/DHF review-pr --diff -
      python -m compliantflow --dhf path/to/DHF review-pr --pr 42
      python -m compliantflow --dhf path/to/DHF review-pr --pr 42 --post-comment
    """
    import subprocess

    if diff_file is None and pr_number is None:
        raise click.UsageError("Provide either --diff <file> or --pr <number>.")

    # Read diff
    if pr_number:
        try:
            result = subprocess.run(
                ["gh", "pr", "diff", str(pr_number)],
                capture_output=True, text=True, check=True,
            )
            diff_text = result.stdout
        except subprocess.CalledProcessError as exc:
            raise click.ClickException(f"gh pr diff failed: {exc.stderr.strip()}")
        except FileNotFoundError:
            raise click.ClickException("'gh' CLI not found. Install the GitHub CLI to use --pr.")
    elif diff_file == "-":
        diff_text = sys.stdin.read()
    else:
        diff_text = Path(diff_file).read_text(encoding="utf-8")

    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    result = core.review_pr(diff_text, governance_dir=gov_dir)

    checklist = result["checklist"]
    changed = result["changed_items"]
    analyzed = result["chains_analyzed"]

    # Build full comment body
    header = (
        f"## CompliantFlow DHF Review\n\n"
        f"**Changed DHF items detected:** {', '.join(changed) if changed else 'none'}\n"
        f"**Chains analysed:** {', '.join(analyzed) if analyzed else 'none'}\n\n"
        f"### Required DHF Actions\n\n"
        f"{checklist}\n\n"
        f"---\n"
        f"_Generated by CompliantFlow · Suggestion layer — not a compliance gate_"
    )

    click.echo(header)

    if post_comment and pr_number:
        try:
            subprocess.run(
                ["gh", "pr", "comment", str(pr_number), "--body", header],
                check=True,
            )
            click.echo(f"✓ Comment posted to PR #{pr_number}", err=True)
        except subprocess.CalledProcessError as exc:
            raise click.ClickException(f"gh pr comment failed: {exc.stderr.strip()}")


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------

@main.command("context")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Path to governance directory. Defaults to ./governance.")
@click.option("--standard", default=None, metavar="ID",
              help="Filter compliance policies to this standard (e.g. IEC_62304).")
@click.option("--summary", is_flag=True, default=False,
              help="Emit policy IDs and headings only — omit check details.")
@click.option("--format", "fmt", default="json", show_default=True,
              type=click.Choice(["json", "yaml"], case_sensitive=False),
              help="Output format.")
@click.pass_context
def context(ctx: click.Context, governance_dir: str | None, standard: str | None,
            summary: bool, fmt: str) -> None:
    """Output DHF schema, lifecycle rules, and compliance policy summaries for AI agents.

    Provides the full item type schema (fields, allowed values, ID prefixes),
    global lifecycle states, and compliance policy summaries from governance
    YAML files in a machine-readable format.  Run this before generating or
    editing DHF content to avoid CI failures from invalid field values.

    \b
    Example:
      python -m compliantflow --dhf path/to/DHF context
      python -m compliantflow --dhf path/to/DHF context --standard IEC_62304 --summary
      python -m compliantflow --dhf path/to/DHF context --format yaml
    """
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    result = core.get_context(gov_dir, standard=standard, summary=summary)

    if fmt == "yaml":
        try:
            import yaml as _yaml
            click.echo(_yaml.dump(result, default_flow_style=False, allow_unicode=True))
        except ImportError:
            raise click.ClickException("PyYAML is required for --format yaml. Install it with: pip install pyyaml")
    else:
        click.echo(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@main.command("status")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Path to governance directory. Defaults to ./governance.")
@click.option("--live", is_flag=True, default=False,
              help="Run fresh compliance checks instead of reading from persisted run store.")
@click.option("--format", "fmt", default="text", show_default=True,
              type=click.Choice(["text", "json"], case_sensitive=False),
              help="Output format.")
@click.pass_context
def status(ctx: click.Context, governance_dir: str | None, live: bool, fmt: str) -> None:
    """Show at-a-glance compliance posture: scores, traceability, defects, release.

    Reads compliance scores from the persisted run store by default.
    Use --live to run fresh checks (invokes LLM for semantic policies).

    \b
    Example:
      python -m compliantflow --dhf path/to/DHF status
      python -m compliantflow --dhf path/to/DHF status --live --format json
    """
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    result = core.get_status(gov_dir, live=live)

    if fmt == "json":
        click.echo(json.dumps(result, default=str))
        return

    # Human-readable text output
    click.echo("\n── Compliance ──────────────────────────────────")
    compliance = result.get("compliance", [])
    if not compliance:
        click.echo("  No governance files found.")
    for entry in compliance:
        score = entry.get("score")
        score_str = f"{score:.0f}%" if score is not None else "n/a"
        passed = entry.get("passed_policies", "?")
        total = entry.get("total_policies", "?")
        source = entry.get("source", "")
        ts = str(entry.get("last_run_at", ""))[:16].replace("T", " ")
        status_icon = "✓" if score is not None and score == 100.0 else "✗"
        click.echo(f"  {status_icon} {entry['standard']}: {score_str} ({passed}/{total}) [{source}] {ts}")

    click.echo("\n── Traceability ─────────────────────────────────")
    trace = result.get("traceability", [])
    if not trace:
        click.echo("  No traceability data.")
    for t in trace:
        icon = "✓" if t["coverage_pct"] == 100.0 else "✗"
        click.echo(
            f"  {icon} {t['parent_type']}→{t['child_type']}: "
            f"{t['coverage_pct']}% ({t['covered']}/{t['total']})"
        )

    click.echo("\n── Open Defects ─────────────────────────────────")
    defs = result.get("open_defects", {})
    count = defs.get("count", 0)
    if count == 0:
        click.echo("  ✓ No open defects.")
    else:
        click.echo(f"  ✗ {count} open defect(s):")
        for d in defs.get("items", [])[:5]:
            click.echo(f"    - {d['id']} [{d['status']}] {d.get('title', '')}")
        if count > 5:
            click.echo(f"    … and {count - 5} more")

    click.echo("\n── Release ──────────────────────────────────────")
    rel = result.get("release")
    if rel is None:
        click.echo("  No REL item found.")
    else:
        icon = "✓" if rel.get("passed") else "✗"
        click.echo(f"  {icon} {rel['rel_id']}: {'ready' if rel.get('passed') else 'not ready'}")
        for c in rel.get("checks", []):
            ci = "✓" if c["passed"] else "✗"
            click.echo(f"    {ci} {c['name']}: {c['details']}")
    click.echo("")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@main.group()
def validate() -> None:
    """Commands for DHF validation."""


@validate.command("traceability")
@click.pass_context
def validate_traceability(ctx: click.Context) -> None:
    """Check that no items are orphaned (every item has at least one traceability link).

    Exits 1 if any orphaned items are found.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    result = core.validate()
    if not result.get("valid", True):
        for issue in result.get("issues", []):
            issue_type = issue.get("type", "issue")
            affected = issue.get("items", [])
            click.echo(
                f"ORPHAN [{issue_type}]: {len(affected)} item(s): "
                + ", ".join(affected[:5])
                + ("…" if len(affected) > 5 else ""),
                err=True,
            )
        sys.exit(1)
    item_count = len(core.get_all_items())
    click.echo(f"✓ All {item_count} items have traceability links.", err=True)


@validate.command("coverage")
@click.argument("pairs", nargs=-1, required=True, metavar="PARENT:CHILD...")
@click.pass_context
def validate_coverage(ctx: click.Context, pairs: tuple) -> None:
    """Check that every item at each level is covered by the next level.

    PAIRS are PARENT:CHILD type-code pairs, e.g.:

    \b
      python -m compliantflow validate coverage UC:CRS CRS:SYS SYS:SYSARCH

    Outputs a JSON report to stdout.
    Exits 1 if any item is uncovered.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)

    parsed = []
    for pair in pairs:
        if ":" not in pair:
            click.echo(f"ERROR: invalid pair '{pair}', expected PARENT:CHILD format.", err=True)
            sys.exit(2)
        parent, child = pair.split(":", 1)
        parsed.append((parent.strip(), child.strip()))

    report = core.check_coverage(parsed)
    click.echo(json.dumps(report, default=str))

    for r in report["results"]:
        if r["passed"]:
            click.echo(
                f"  ✓ {r['parent_type']}→{r['child_type']}: "
                f"{r['covered']}/{r['total']} covered",
                err=True,
            )
        else:
            click.echo(
                f"  ✗ {r['parent_type']}→{r['child_type']}: "
                f"{len(r['uncovered'])} uncovered: {r['uncovered']}",
                err=True,
            )

    if not report["passed"]:
        click.echo("✗ Coverage check failed.", err=True)
        sys.exit(1)
    click.echo("✓ All coverage checks passed.", err=True)


@validate.command("compliance")
@click.argument("group_id")
@click.option(
    "--governance-dir",
    default=None,
    metavar="PATH",
    help="Path to governance directory containing policy YAML files. Defaults to ./governance.",
)
@click.option(
    "--persist/--no-persist",
    default=False,
    help="Persist the compliance run to the DHF compliance-runs store.",
)
@click.pass_context
def validate_compliance(
    ctx: click.Context,
    group_id: str,
    governance_dir: str | None,
    persist: bool,
) -> None:
    """Check compliance against a governance policy group.

    GROUP_ID is the filename stem of a policy YAML file (e.g. IEC_62304).
    Outputs the full JSON report to stdout.
    Exits 1 if any policy fails.
    """
    dhf_path: Path = ctx.obj["dhf"]
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    report = core.check_compliance(group_id, governance_dir=gov_dir, persist=persist)
    if report is None:
        click.echo(f"ERROR: Policy group '{group_id}' not found.", err=True)
        sys.exit(1)
    failed = [r for r in report["results"] if not r["passed"]]
    for r in failed:
        click.echo(f"  ✗ [{r['policy_id']}] {r['policy_text']}: {r['details']}", err=True)
        rem = r.get("remediation")
        if rem:
            guidance = rem.get("guidance", "")
            items = rem.get("items", [])
            line = f"     → {guidance}"
            if items:
                preview = ", ".join(items[:5])
                if len(items) > 5:
                    preview += f" (+{len(items) - 5} more)"
                line += f" [{preview}]"
            click.echo(line, err=True)
    click.echo(json.dumps(report, default=str))
    if failed:
        click.echo(
            f"✗ {len(failed)}/{report['total_policies']} policies failed "
            f"(score: {report['score']:.0f}%).",
            err=True,
        )
        sys.exit(1)
    click.echo(
        f"✓ {report['passed_policies']}/{report['total_policies']} policies passed "
        f"(score: {report['score']:.0f}%).",
        err=True,
    )


@validate.command("release")
@click.argument("rel_id")
@click.pass_context
def validate_release(ctx: click.Context, rel_id: str) -> None:
    """Evaluate whether a REL item meets all release criteria.

    REL_ID is the identifier of the release (e.g. REL-002).

    Checks:
      1. REL item exists.
      2. All included CRs are completed.
      3. No open DEF items exist (draft/open/in_progress).
      4. All SYS requirements are verified.

    Outputs a JSON report to stdout.
    Exits 0 if all checks pass; exits 1 if any fail.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    report = core.validate_release(rel_id)
    click.echo(json.dumps(report, default=str))
    failed = [c for c in report["checks"] if not c["passed"]]
    if failed:
        for c in failed:
            click.echo(f"  ✗ [{c['name']}] {c['details']}", err=True)
        click.echo(
            f"✗ Release gate FAILED: {len(failed)}/{len(report['checks'])} check(s) did not pass.",
            err=True,
        )
        sys.exit(1)
    click.echo(
        f"✓ Release gate PASSED: all {len(report['checks'])} checks passed for {rel_id}.",
        err=True,
    )


@validate.command("draft")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--type", "item_type", default=None, metavar="TYPE",
              help="Item type code (e.g. SYS). Inferred from id prefix if omitted.")
@click.option("--format", "fmt", default="json", show_default=True,
              type=click.Choice(["json", "text"], case_sensitive=False),
              help="Output format.")
@click.pass_context
def validate_draft(ctx: click.Context, file: str, item_type: str | None, fmt: str) -> None:
    """Validate a draft DHF item YAML against the doc-type field schema.

    Checks required fields and allowed values without requiring a full CI run.
    Graph-dependent checks (traceability, verification) are out of scope.
    Exits 0 on pass, 1 on validation failure.

    \b
    Example:
      python -m compliantflow --dhf path/to/DHF validate draft my_item.yaml
      python -m compliantflow --dhf path/to/DHF validate draft my_item.yaml --type SYS
    """
    import yaml as _yaml

    with open(file, "r", encoding="utf-8") as f:
        try:
            item_data = _yaml.safe_load(f)
        except Exception as exc:
            raise click.ClickException(f"Failed to parse YAML: {exc}")

    if not isinstance(item_data, dict):
        raise click.ClickException("Item file must be a YAML mapping.")

    core = _make_core(ctx)
    result = core.validate_draft(item_data, type_name=item_type)

    if fmt == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        valid = result["valid"]
        icon = "✓" if valid else "✗"
        item_type_str = result.get("type") or "unknown"
        click.echo(f"{icon} {item_type_str}: {'valid' if valid else 'invalid'}")
        for w in result.get("warnings", []):
            click.echo(f"  ⚠  {w['field']}: {w['message']}")
        for e in result.get("errors", []):
            click.echo(f"  ✗  {e['field']}: {e['message']}")

    if not result["valid"]:
        sys.exit(1)


@validate.group("compliance-history")
def validate_compliance_history() -> None:
    """Compliance run history commands."""


@validate_compliance_history.command("list")
@click.argument("group_id")
@click.option("--since", default=None, metavar="DATE",
              help="Filter to runs at or after this ISO 8601 date (e.g. 2026-01-01).")
@click.pass_context
def validate_compliance_history_list(
    ctx: click.Context,
    group_id: str,
    since: str | None,
) -> None:
    """List persisted compliance runs for GROUP_ID.

    Outputs each run as a JSON object on stdout (NDJSON).
    """
    from utils.local_adapter import LocalDHFAdapter
    dhf_path: Path = ctx.obj["dhf"]
    adapter = LocalDHFAdapter(dhf_path, auto_commit=False)
    runs = adapter.get_compliance_runs(group_id, since_date=since)
    for run in runs:
        click.echo(json.dumps(run, default=str))
    click.echo(f"({len(runs)} run(s) for '{group_id}')", err=True)


# ---------------------------------------------------------------------------
# traceability group
# ---------------------------------------------------------------------------

@main.group()
def traceability() -> None:
    """Commands for traceability analysis."""


@traceability.command("matrix")
@click.argument("doc_types", nargs=-1, required=True, metavar="DOC_TYPE...")
@click.pass_context
def traceability_matrix(ctx: click.Context, doc_types: tuple) -> None:
    """Build a traceability matrix for an ordered list of doc types.

    Outputs one JSON object per row to stdout.

    \b
    Examples:
      python -m cli traceability matrix CRS SYS SRS
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    result = core.build_traceability_matrix(list(doc_types))
    click.echo(json.dumps({"columns": result["columns"]}, default=str), err=True)
    for row in result["rows"]:
        click.echo(json.dumps(row, default=str))
    total = len(result["rows"])
    complete = sum(1 for r in result["rows"] if r["is_complete"])
    orphans = sum(1 for r in result["rows"] if r["is_orphan"])
    click.echo(
        f"({total} row(s): {complete} complete, {orphans} orphan(s))", err=True
    )


@traceability.command("chain")
@click.argument("item_id")
@click.pass_context
def traceability_chain(ctx: click.Context, item_id: str) -> None:
    """Show the full connected traceability chain for a single item."""
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    result = core.get_item_chain(item_id)
    if result is None:
        click.echo(f"ERROR: Item '{item_id}' not found.", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))
    click.echo(f"({len(result['nodes'])} node(s) in chain)", err=True)


# ---------------------------------------------------------------------------
# report group
# ---------------------------------------------------------------------------

@main.group()
def report() -> None:
    """Commands for generating PDF evidence reports."""


@report.command("traceability")
@click.argument("doc_types", nargs=-1, required=True, metavar="DOC_TYPE...")
@click.option("--output", "-o", default="traceability_report.pdf", show_default=True,
              help="Output PDF file path.")
@click.pass_context
def report_traceability(ctx: click.Context, doc_types: tuple, output: str) -> None:
    """Generate a traceability matrix PDF.

    \b
    Example:
      python -m compliantflow report traceability UC CRS SYS SYSARCH \\
        --output traceability_report.pdf
    """
    from compliantflow.report_generator import generate_traceability_pdf
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    matrix = core.build_traceability_matrix(list(doc_types))

    # Enrich each row with verification_status from the items it contains
    columns: list[str] = matrix["columns"]
    for row in matrix["rows"]:
        statuses = []
        for col in columns:
            item_id = row.get(col)
            if item_id:
                item = core.get_item(item_id)
                vs = item.get("verification_status") if item else None
                if vs:
                    statuses.append(vs)
        # Summarise: any failure → failed; all verified → verified; else not_verified
        if "failed" in statuses:
            row["verification_status"] = "failed"
        elif statuses and all(s == "verified" for s in statuses):
            row["verification_status"] = "verified"
        elif statuses:
            row["verification_status"] = "not_verified"
        # else leave absent (no items with verification in this row)

    # Attach test results summary
    matrix["test_results"] = core.get_all_test_results()

    out = Path(output)
    generate_traceability_pdf(matrix, out)
    click.echo(f"✓ Traceability report written to {out} "
               f"({len(matrix['rows'])} rows)", err=True)


@report.command("compliance")
@click.argument("group_id")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Path to governance directory. Defaults to ./governance.")
@click.option("--output", "-o", default=None, show_default=False,
              help="Output file path. Defaults to compliance_report.pdf or compliance_report.json.")
@click.option("--format", "fmt", default="pdf", show_default=True,
              type=click.Choice(["pdf", "json"], case_sensitive=False),
              help="Output format: pdf (default) or json for programmatic consumption.")
@click.pass_context
def report_compliance(ctx: click.Context, group_id: str,
                      governance_dir: str | None, output: str | None, fmt: str) -> None:
    """Generate a compliance evidence report (PDF or JSON).

    \b
    Examples:
      python -m compliantflow report compliance IEC_62304 --governance-dir governance
      python -m compliantflow report compliance IEC_62304 --format json --output report.json
    """
    from compliantflow.report_generator import generate_compliance_pdf, generate_compliance_json
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    result = core.check_compliance(group_id, governance_dir=gov_dir)
    if result is None:
        click.echo(f"ERROR: Policy group '{group_id}' not found.", err=True)
        sys.exit(1)
    default_name = f"compliance_report.{'json' if fmt == 'json' else 'pdf'}"
    out = Path(output) if output else Path(default_name)
    if fmt == "json":
        generate_compliance_json(result, out)
    else:
        generate_compliance_pdf(result, out)
    failed = result["total_policies"] - result["passed_policies"]
    for r in result["results"]:
        if not r["passed"]:
            click.echo(f"  ✗ [{r['policy_id']}] {r['policy_text']}: {r['details']}", err=True)
    click.echo(json.dumps(result, default=str))
    if failed:
        click.echo(
            f"✗ {failed}/{result['total_policies']} policies failed "
            f"(score: {result['score']:.0f}%) — report: {out}",
            err=True,
        )
        sys.exit(1)
    click.echo(
        f"✓ {result['passed_policies']}/{result['total_policies']} policies passed "
        f"(score: {result['score']:.0f}%) — report: {out}",
        err=True,
    )


# ---------------------------------------------------------------------------
# cr group
# ---------------------------------------------------------------------------

@main.group()
def cr() -> None:
    """Commands for Change Request git-evidence management."""


@cr.command("check-status")
@click.argument("cr_id")
@click.pass_context
def cr_check_status(ctx: click.Context, cr_id: str) -> None:
    """Check that a Change Request exists and is in an authorized state.

    CR_ID is the identifier of the change request (e.g. CR-012).
    Outputs a JSON object to stdout.
    Exits 0 if the CR exists and is approved, implementing, or completed; exits 1 otherwise.

    Note: linked commits/PRs are evidence recorded AFTER the work is merged.
    This gate only verifies the CR is authorized — not that evidence exists yet.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    item = core.get_item(cr_id)
    if item is None:
        click.echo(json.dumps({"cr_id": cr_id, "found": False, "error": f"CR '{cr_id}' not found"}))
        click.echo(f"ERROR: CR '{cr_id}' not found.", err=True)
        sys.exit(1)

    status = item.get("status", "")
    valid_statuses = {"planned", "approved", "implementing", "completed"}
    valid = status in valid_statuses

    result = {
        "cr_id": cr_id,
        "found": True,
        "status": status,
        "valid": valid,
    }
    click.echo(json.dumps(result, default=str))

    if valid:
        click.echo(f"✓ CR '{cr_id}' is authorized (status: {status}).", err=True)
    else:
        click.echo(
            f"✗ CR '{cr_id}' is not authorized: status is '{status}' "
            f"(expected one of: {', '.join(sorted(valid_statuses))}).",
            err=True,
        )
        sys.exit(1)


@cr.command("generate-report")
@click.argument("cr_id")
@click.option("--since", default=None, metavar="DATE",
              help="Only include commits after this date (ISO 8601).")
@click.pass_context
def cr_generate_report(ctx: click.Context, cr_id: str, since: str | None) -> None:
    """Scan git log to generate a CR-PR evidence report.

    Outputs a JSON object to stdout with the CR details and associated commits
    extracted from git log messages mentioning CR_ID.

    The resulting JSON can be written to a file and consumed by the
    ``cr_git_evidence`` policy check via COMPLIANTFLOW_CR_REPORT_PATH.
    """
    import subprocess  # noqa: PLC0415
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    item = core.get_item(cr_id)

    cr_data: dict = {}
    if item:
        cr_data = {
            "cr_id": cr_id,
            "title": item.get("title", ""),
            "status": item.get("status", ""),
            "affected_items": item.get("affected_items") or [],
            "implementation_prs": item.get("implementation_prs") or [],
        }
    else:
        cr_data = {"cr_id": cr_id, "found": False}

    # Scan git log for commits mentioning this CR ID
    git_args = [
        "git", "-C", str(dhf_path.parent),
        "log", "--all", "--format=%H %s",
        f"--grep={cr_id}",
    ]
    if since:
        git_args += [f"--after={since}"]

    commits = []
    pr_numbers: list[str] = []
    try:
        import re  # noqa: PLC0415
        proc = subprocess.run(git_args, capture_output=True, text=True, timeout=30)
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            sha = parts[0]
            message = parts[1] if len(parts) > 1 else ""
            commits.append({"sha": sha, "message": message})
            # Extract PR numbers from GitHub squash-merge format: "Title (#123)"
            for match in re.finditer(r'\(#(\d+)\)', message):
                pr_num = match.group(1)
                if pr_num not in pr_numbers:
                    pr_numbers.append(pr_num)
    except Exception as exc:
        click.echo(f"WARNING: git log scan failed: {exc}", err=True)

    cr_data["commits"] = commits
    cr_data["implementation_prs"] = pr_numbers
    click.echo(json.dumps(cr_data, default=str))
    click.echo(
        f"({len(commits)} commit(s) referencing {cr_id} found in git log)", err=True
    )


# ---------------------------------------------------------------------------
# test group
# ---------------------------------------------------------------------------

@main.group()
def test() -> None:
    """Commands for test result integration."""


@test.command("import")
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "fmt", default="junit", show_default=True,
              type=click.Choice(["junit"], case_sensitive=False),
              help="Test result format.")
@click.option("--tester", default="", help="Name of the tester or CI agent.")
@click.option("--run-id", default="", help="CI run ID.")
@click.option("--run-url", default="", help="URL to the CI run.")
@click.option("--commit", default="", help="Git commit SHA.")
@click.pass_context
def test_import(
    ctx: click.Context,
    path: str,
    fmt: str,
    tester: str,
    run_id: str,
    run_url: str,
    commit: str,
) -> None:
    """Import test results from a JUnit XML file.

    PATH is the path to the test result file.
    Outputs a JSON summary to stdout.
    """
    from utils.local_adapter import LocalDHFAdapter
    dhf_path: Path = ctx.obj["dhf"]
    adapter = LocalDHFAdapter(dhf_path, auto_commit=False)
    result = adapter.import_results_from_file(
        xml_path=Path(path),
        tester=tester,
        run_id=run_id,
        run_url=run_url,
        commit_sha=commit,
    )
    # Re-shape to match the summary format used by core.import_test_results
    recorded = result.get("recorded", [])
    skipped = result.get("skipped", 0)
    items_updated = list({uid for r in recorded for uid in r.get("links", [])})
    failed_tcs = [r["tc_id"] for r in recorded if r.get("testing_status") == "FAIL"]
    summary = {
        "imported": len(recorded),
        "skipped": skipped,
        "items_updated": items_updated,
        "failed_tcs": failed_tcs,
    }
    click.echo(json.dumps(summary, default=str))
    click.echo(
        f"✓ Imported {summary['imported']} result(s), "
        f"skipped {summary['skipped']}, "
        f"updated {len(summary['items_updated'])} item(s).",
        err=True,
    )
    if summary["failed_tcs"]:
        click.echo(f"  ✗ Failing TCs: {summary['failed_tcs']}", err=True)


@test.command("status")
@click.argument("tc_id")
@click.pass_context
def test_status(ctx: click.Context, tc_id: str) -> None:
    """Show the latest test result for a TC.

    TC_ID is the test case identifier (e.g. TC-SYS-001-001).
    Outputs a JSON object to stdout.
    Exits 1 if the TC is not found.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    result = core.get_test_result(tc_id)
    if result is None:
        click.echo(json.dumps({"tc_id": tc_id, "found": False}))
        click.echo(f"ERROR: TC '{tc_id}' not found.", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))
    status = result.get("testing_status", "UNKNOWN")
    click.echo(f"  {tc_id}: {status}", err=True)


@test.command("list")
@click.option("--status", "status_filter", default=None,
              type=click.Choice(["PASS", "FAIL", "SKIP"], case_sensitive=False),
              help="Filter by testing status.")
@click.pass_context
def test_list(ctx: click.Context, status_filter: str | None) -> None:
    """List all imported test results.

    Outputs one JSON object per result to stdout (NDJSON).
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    sf = status_filter.upper() if status_filter else None
    results = core.get_all_test_results(status_filter=sf)
    for rec in results.values():
        click.echo(json.dumps(rec, default=str))
    click.echo(f"({len(results)} result(s))", err=True)


# ---------------------------------------------------------------------------
# migrate group
# ---------------------------------------------------------------------------

@main.group()
def migrate() -> None:
    """Migrate external repository formats into a CompliantFlow DHF."""


@migrate.command("rdm")
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--dry-run", is_flag=True, default=False,
    help="Parse and map items without writing any files.",
)
@click.option(
    "--report-output", default=None, metavar="FILE",
    help="Write a Markdown completeness report to FILE after migration.",
)
@click.pass_context
def migrate_rdm(ctx: click.Context, source_dir: Path, dry_run: bool,
                report_output: str | None) -> None:
    """Migrate an Innolitics RDM repository into this DHF.

    SOURCE_DIR is the root of the RDM repository to migrate.

    Discovers all YAML requirement files under SOURCE_DIR, maps them to
    CompliantFlow doc types, converts reST content to Markdown, writes items
    into DHF/items/, and prints a JSON migration report to stdout.

    After writing items, runs post-migration field schema validation and
    categorises results into clean / gaps / skipped.  Use --report-output to
    save a Markdown completeness report.

    Use --dry-run to preview the mapping without writing any files.

    \b
    Example:
      python -m compliantflow --dhf path/to/DHF migrate rdm /path/to/rdm-repo
      python -m compliantflow --dhf path/to/DHF migrate rdm /path/to/rdm-repo --report-output migration_report.md
    """
    from compliantflow.migrate.rdm import RDMMigrator, generate_migration_markdown

    dhf_path: Path = ctx.obj["dhf"]
    dhf_items_dir = dhf_path / "items"

    migrator = RDMMigrator(source_dir=source_dir)
    migration_report = migrator.migrate(dhf_items_dir=dhf_items_dir, dry_run=dry_run)

    n_created = len(migration_report["created"])
    n_skipped = len(migration_report["skipped"])
    n_review = len(migration_report["needs_review"])
    suffix = " (dry run)" if dry_run else ""

    # Post-migration validation (skipped in dry-run mode)
    if not dry_run:
        core = _make_core(ctx)
        completeness = core.validate_migration_report(migration_report)
        click.echo(json.dumps(completeness, indent=2, default=str))

        if report_output:
            md = generate_migration_markdown(completeness)
            Path(report_output).write_text(md, encoding="utf-8")
            click.echo(f"✓ Markdown report written to {report_output}", err=True)

        n_gaps = completeness["summary"]["gaps"]
        click.echo(
            f"\n✓ Migration complete{suffix}: "
            f"{n_created} created ({completeness['summary']['clean']} clean, "
            f"{n_gaps} gap(s)), {n_skipped} skipped",
            err=True,
        )
        if n_gaps > 0 or n_skipped > 0:
            click.echo(
                "⚠  Review required before migration is considered complete.",
                err=True,
            )
    else:
        click.echo(json.dumps(migration_report, indent=2, default=str))
        click.echo(
            f"\n✓ Migration complete{suffix}: "
            f"{n_created} created, {n_skipped} skipped, {n_review} need review",
            err=True,
        )
