"""CompliantFlow CLI — analysis and traceability operations for CI/CD pipelines.

Data CRUD (item create/update/delete, validate schema, doc generate/export)
is handled by the dhf CLI (python -m dhf).
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
    return Path(__file__).parent.parent.parent / "DHF"


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


@validate.command("compliance")
@click.argument("group_id")
@click.pass_context
def validate_compliance(ctx: click.Context, group_id: str) -> None:
    """Check compliance against a governance policy group.

    GROUP_ID is the filename stem under governance/ at the repo root (e.g. IEC_62304).
    Outputs the full JSON report to stdout.
    Exits 1 if any policy fails.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    report = core.check_compliance(group_id)
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
# item group (lifecycle only — CRUD is in dhf CLI)
# ---------------------------------------------------------------------------

@main.group()
def item() -> None:
    """Commands for item lifecycle transitions."""


@item.command("transitions")
@click.argument("item_id")
@click.pass_context
def item_transitions(ctx: click.Context, item_id: str) -> None:
    """List available lifecycle transitions for an item. Outputs JSON."""
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    it = core.get_item(item_id)
    if it is None:
        click.echo(f"ERROR: Item '{item_id}' not found.", err=True)
        sys.exit(1)
    transitions = core.get_available_transitions(it)
    click.echo(json.dumps({"item_id": item_id, "current_status": it.get("status"), "transitions": transitions}, default=str))


@item.command("transition")
@click.argument("item_id")
@click.argument("to_state")
@click.option("--by", "performed_by", default="cli", show_default=True, help="User performing the transition.")
@click.pass_context
def item_transition(ctx: click.Context, item_id: str, to_state: str, performed_by: str) -> None:
    """Execute a lifecycle state transition for an item."""
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    try:
        result = core.execute_transition(item_id, to_state, performed_by=performed_by)
    except ValueError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))
    click.echo(f"✓ {item_id}: {result.get('status')}.", err=True)


# ---------------------------------------------------------------------------
# cr group
# ---------------------------------------------------------------------------

@main.group()
def cr() -> None:
    """Commands for Change Request management."""


@cr.command("check-status")
@click.argument("cr_id")
@click.pass_context
def cr_check_status(ctx: click.Context, cr_id: str) -> None:
    """Check that a CR is in a non-stable state.

    Exits 0 if the CR is open (non-stable) and safe to modify.
    Exits 1 if the CR is stable (approved/closed) or does not exist.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    cr_item = core.get_item(cr_id)
    if cr_item is None:
        click.echo(f"ERROR: CR '{cr_id}' not found.", err=True)
        sys.exit(1)
    if core.is_cr_stable(cr_item):
        status = cr_item.get("status", "unknown")
        click.echo(
            f"ERROR: CR '{cr_id}' is in stable status '{status}'. "
            "Cannot modify items for a closed CR.",
            err=True,
        )
        sys.exit(1)
    status = cr_item.get("status", "unknown")
    click.echo(f"✓ CR '{cr_id}' is open (status: {status}).", err=True)


@cr.command("update")
@click.argument("cr_id")
@click.option("--item", "items", multiple=True, metavar="ITEM_ID", help="Affected item ID (repeat for multiple).")
@click.pass_context
def cr_update(
    ctx: click.Context,
    cr_id: str,
    items: tuple,
) -> None:
    """Add affected items to a Change Request.

    PR linkage is captured implicitly by Git conventions (PR title starts with
    CR-NNN, enforced by CI). PR metadata is not stored in CR YAML — see SYSARCH-011.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)

    cr_item = core.get_item(cr_id)
    if cr_item is None:
        click.echo(f"ERROR: CR '{cr_id}' not found.", err=True)
        sys.exit(1)
    if core.is_cr_stable(cr_item):
        click.echo(f"ERROR: CR '{cr_id}' is in a stable state. Cannot update.", err=True)
        sys.exit(1)

    added = []
    for item_id in items:
        success = core.add_item_to_cr(cr_id, item_id)
        if success:
            added.append(item_id)
            click.echo(f"  + Added item: {item_id}", err=True)
        else:
            click.echo(f"  ~ Skipped item: {item_id} (already present or error)", err=True)

    click.echo(
        f"✓ CR '{cr_id}' updated: {len(added)} item(s) added.",
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
# test group
# ---------------------------------------------------------------------------

@main.group()
def test() -> None:
    """Commands for external test result integration."""


@test.command("import")
@click.argument("file")
@click.option("--format", "fmt", default="junit", show_default=True,
              type=click.Choice(["junit"]), help="Input format.")
@click.option("--tester", required=True, help="Name of tester / CI system.")
@click.option("--run-id", default="", help="CI run identifier.")
@click.option("--run-url", default="", help="URL to CI run for traceability.")
@click.option("--commit", "commit_sha", default="", metavar="SHA",
              help="Git commit SHA that was tested.")
@click.pass_context
def test_import(
    ctx: click.Context,
    file: str,
    fmt: str,
    tester: str,
    run_id: str,
    run_url: str,
    commit_sha: str,
) -> None:
    """Import test execution results from a JUnit XML file."""
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)

    summary = core.import_test_results_from_file(
        Path(file),
        tester=tester,
        run_id=run_id,
        run_url=run_url,
        commit_sha=commit_sha,
    )
    click.echo(json.dumps(summary, default=str))
    click.echo(
        f"✓ Imported {summary['imported']} result(s), "
        f"skipped {summary['skipped']}, "
        f"updated {len(summary['items_updated'])} item(s).",
        err=True,
    )
    if summary["failed_tcs"]:
        click.echo(
            f"✗ {len(summary['failed_tcs'])} TC(s) FAILED: "
            + ", ".join(summary["failed_tcs"][:10])
            + ("…" if len(summary["failed_tcs"]) > 10 else ""),
            err=True,
        )
        sys.exit(1)


@test.command("pull")
@click.option("--run-id", default="", help="GitHub Actions run ID (default: latest for HEAD).")
@click.option("--commit", "commit_sha", default="", metavar="SHA",
              help="Find latest completed run for this commit SHA.")
@click.pass_context
def test_pull(ctx: click.Context, run_id: str, commit_sha: str) -> None:
    """Fetch test results from GitHub Actions artifacts.

    Requires GITHUB_TOKEN to be set in the environment.
    Results are cached locally (DHF/test-results/results.yaml, git-ignored).
    Verification status is computed in-memory — requirement YAML files are not modified.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    try:
        summary = core.pull_test_results(run_id=run_id, commit_sha=commit_sha)
    except ValueError as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)

    click.echo(json.dumps(summary, default=str))
    click.echo(
        f"✓ Pulled {summary['imported']} result(s), "
        f"skipped {summary['skipped']} — "
        f"run {summary['run_id']}",
        err=True,
    )
    if summary["failed_tcs"]:
        click.echo(
            f"✗ {len(summary['failed_tcs'])} TC(s) FAILED: "
            + ", ".join(summary["failed_tcs"][:10])
            + ("…" if len(summary["failed_tcs"]) > 10 else ""),
            err=True,
        )
        sys.exit(1)


@test.command("status")
@click.argument("tc_id")
@click.pass_context
def test_status(ctx: click.Context, tc_id: str) -> None:
    """Show the stored record for a single test case. Outputs JSON."""
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    record = core.get_test_result(tc_id)
    if record is None:
        click.echo(f"ERROR: No record found for '{tc_id}'.", err=True)
        sys.exit(1)
    click.echo(json.dumps(record, default=str))


@test.command("list")
@click.option("--status", "status_filter", default=None, metavar="STATUS",
              help="Filter by testing_status (PASS, FAIL, SKIP).")
@click.pass_context
def test_list(ctx: click.Context, status_filter: str) -> None:
    """List all stored test results, one JSON object per line."""
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    records = core.get_all_test_results(status_filter)
    for tc_id, record in records.items():
        click.echo(json.dumps(record, default=str))
    click.echo(f"({len(records)} record(s))", err=True)
