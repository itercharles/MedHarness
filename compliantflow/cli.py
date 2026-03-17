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


def _make_core(dhf_path: Path):
    """Instantiate CompliantFlowCore with a LocalDHFAdapter."""
    from utils.local_adapter import LocalDHFAdapter
    from compliantflow.core import CompliantFlowCore
    adapter = LocalDHFAdapter(dhf_path, auto_commit=False)
    return CompliantFlowCore(adapter)


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
@click.pass_context
def main(ctx: click.Context, dhf: str | None) -> None:
    """CompliantFlow CLI — analysis and traceability for CI/CD pipelines."""
    ctx.ensure_object(dict)
    ctx.obj["dhf"] = _resolve_dhf(dhf)


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
    core = _make_core(dhf_path)
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
    core = _make_core(dhf_path)

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
@click.pass_context
def validate_compliance(ctx: click.Context, group_id: str, governance_dir: str | None) -> None:
    """Check compliance against a governance policy group.

    GROUP_ID is the filename stem of a policy YAML file (e.g. IEC_62304).
    Outputs the full JSON report to stdout.
    Exits 1 if any policy fails.
    """
    dhf_path: Path = ctx.obj["dhf"]
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(dhf_path)
    report = core.check_compliance(group_id, governance_dir=gov_dir)
    if report is None:
        click.echo(f"ERROR: Policy group '{group_id}' not found.", err=True)
        sys.exit(1)
    failed = [r for r in report["results"] if not r["passed"]]
    for r in failed:
        click.echo(f"  ✗ [{r['policy_id']}] {r['policy_text']}: {r['details']}", err=True)
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
    core = _make_core(dhf_path)
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
    core = _make_core(dhf_path)
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
    core = _make_core(dhf_path)
    matrix = core.build_traceability_matrix(list(doc_types))
    out = Path(output)
    generate_traceability_pdf(matrix, out)
    click.echo(f"✓ Traceability report written to {out} "
               f"({len(matrix['rows'])} rows)", err=True)


@report.command("compliance")
@click.argument("group_id")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Path to governance directory. Defaults to ./governance.")
@click.option("--output", "-o", default="compliance_report.pdf", show_default=True,
              help="Output PDF file path.")
@click.pass_context
def report_compliance(ctx: click.Context, group_id: str,
                      governance_dir: str | None, output: str) -> None:
    """Generate a compliance evidence PDF with pass/fail and rationale per policy.

    \b
    Example:
      python -m compliantflow report compliance IEC_62304 \\
        --governance-dir governance --output compliance_report.pdf
    """
    from compliantflow.report_generator import generate_compliance_pdf
    dhf_path: Path = ctx.obj["dhf"]
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(dhf_path)
    result = core.check_compliance(group_id, governance_dir=gov_dir)
    if result is None:
        click.echo(f"ERROR: Policy group '{group_id}' not found.", err=True)
        sys.exit(1)
    out = Path(output)
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
