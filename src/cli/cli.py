"""CompliantFlow CLI — headless access to DHF operations for CI/CD pipelines."""

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
    # Default: DHF/ next to the src/ that contains this package
    return Path(__file__).parent.parent.parent / "DHF"


def _make_core(dhf_path: Path):
    """Instantiate CompliantFlowCore; adds src/ to sys.path if needed."""
    src_dir = Path(__file__).parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from compliantflow.core import CompliantFlowCore
    return CompliantFlowCore(dhf_path, auto_commit=False)


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
    """CompliantFlow CLI — DHF operations for CI/CD pipelines."""
    ctx.ensure_object(dict)
    ctx.obj["dhf"] = _resolve_dhf(dhf)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@main.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate all DHF items against the project schema.

    Checks:
      1. Schema validation — every YAML conforms to its doc-type definition.
      2. Graph validation — reports isolated items (no traceability links).

    Exits with code 1 if schema errors are found.
    """
    dhf_path: Path = ctx.obj["dhf"]
    click.echo(f"Validating DHF at: {dhf_path}", err=True)

    # Schema validation happens during loading; catch hard errors here.
    from traceability.exceptions import ValidationError as CFValidationError
    try:
        core = _make_core(dhf_path)
    except CFValidationError as e:
        click.echo(f"SCHEMA ERROR: {e}", err=True)
        click.echo("✗ Schema validation failed.", err=True)
        sys.exit(1)

    items = core.get_all_items()
    item_count = len(items)

    # Graph-level validation (orphans, isolated nodes) — informational only.
    graph_result = core.validate()
    if not graph_result.get("valid", True):
        for issue in graph_result.get("issues", []):
            issue_type = issue.get("type", "issue")
            affected = issue.get("items", [])
            click.echo(
                f"WARNING: {len(affected)} isolated item(s) [{issue_type}]: "
                + ", ".join(affected[:5])
                + ("…" if len(affected) > 5 else ""),
                err=True,
            )

    click.echo(f"✓ All {item_count} items passed schema validation.", err=True)


# ---------------------------------------------------------------------------
# item group
# ---------------------------------------------------------------------------

@main.group()
def item() -> None:
    """Commands for querying DHF items."""


@item.command("list")
@click.option("--type", "doc_type", default=None, metavar="CODE", help="Filter by doc type code (e.g. SYS, SRS).")
@click.option("--status", default=None, metavar="STATUS", help="Filter by status (e.g. approved, draft).")
@click.option("--search", default="", metavar="TEXT", help="Search text filter.")
@click.pass_context
def item_list(ctx: click.Context, doc_type: str | None, status: str | None, search: str) -> None:
    """List DHF items. Outputs one JSON object per line."""
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    status_filter = [status] if status else None
    if doc_type:
        items = core.get_items_filtered(doc_type, status_filter, search)
    else:
        # No type filter — return all items with optional status/search filter
        items = core.get_all_items()
        if status_filter:
            items = [i for i in items if i.get("status") in status_filter]
        if search:
            s = search.lower()
            items = [i for i in items if s in i["id"].lower() or s in i.get("title", "").lower()]
    for it in items:
        click.echo(json.dumps(it, default=str))
    click.echo(f"({len(items)} item(s))", err=True)


@item.command("get")
@click.argument("item_id")
@click.pass_context
def item_get(ctx: click.Context, item_id: str) -> None:
    """Get a single DHF item by ID. Outputs JSON."""
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    result = core.get_item(item_id)
    if result is None:
        click.echo(f"ERROR: Item '{item_id}' not found.", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))


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
@click.option("--pr-number", default=None, type=int, metavar="N", help="Pull request number.")
@click.option("--pr-url", default=None, metavar="URL", help="Pull request URL.")
@click.option("--pr-title", default=None, metavar="TITLE", help="Pull request title.")
@click.pass_context
def cr_update(
    ctx: click.Context,
    cr_id: str,
    items: tuple,
    pr_number: int | None,
    pr_url: str | None,
    pr_title: str | None,
) -> None:
    """Add affected items and/or PR metadata to a Change Request."""
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)

    cr_item = core.get_item(cr_id)
    if cr_item is None:
        click.echo(f"ERROR: CR '{cr_id}' not found.", err=True)
        sys.exit(1)
    if core.is_cr_stable(cr_item):
        click.echo(f"ERROR: CR '{cr_id}' is in a stable state. Cannot update.", err=True)
        sys.exit(1)

    # Add affected items
    added = []
    for item_id in items:
        success = core.add_item_to_cr(cr_id, item_id)
        if success:
            added.append(item_id)
            click.echo(f"  + Added item: {item_id}", err=True)
        else:
            click.echo(f"  ~ Skipped item: {item_id} (already present or error)", err=True)

    # Add PR info if provided
    if pr_number is not None:
        cr_item = core.get_item(cr_id)  # reload after item updates
        prs = list(cr_item.get("implementation_prs") or [])
        if not any(p.get("pr_number") == pr_number for p in prs):
            prs.append({
                "pr_number": pr_number,
                "pr_url": pr_url or "",
                "title": pr_title or "",
            })
            cr_item["implementation_prs"] = prs
            core.update_item(cr_id, cr_item)
            click.echo(f"  + Tracked PR #{pr_number}", err=True)
        else:
            click.echo(f"  ~ PR #{pr_number} already tracked", err=True)

    click.echo(
        f"✓ CR '{cr_id}' updated: {len(added)} item(s) added"
        + (f", PR #{pr_number} tracked" if pr_number else "")
        + ".",
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

    DOC_TYPE arguments must be ordered along the traceability chain
    (e.g. CRS SYS SRS).  Orphaned items are included with null slots.

    Outputs one JSON object per row to stdout.

    \b
    Examples:
      python -m cli traceability matrix CRS SYS SRS
      python -m cli traceability matrix RISK RCM SYS TC-SYS
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
    """Show the full connected traceability chain for a single item.

    Traverses all upstream and downstream links transitively and outputs
    a JSON object with 'root' and 'nodes'.  Each node lists only its
    direct neighbours; the complete reachable set is the nodes dict.

    \b
    Examples:
      python -m cli traceability chain SYS-001
      python -m cli traceability chain CRS-003
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(dhf_path)
    result = core.get_item_chain(item_id)
    if result is None:
        click.echo(f"ERROR: Item '{item_id}' not found.", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))
    click.echo(f"({len(result['nodes'])} node(s) in chain)", err=True)
