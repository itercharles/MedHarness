"""DHF CLI — standalone data-layer operations (no compliantflow dependency)."""

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


def _make_adapter(dhf_path: Path):
    """Instantiate LocalDHFAdapter."""
    src_dir = Path(__file__).parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from compliantflow.adapters.local import LocalDHFAdapter
    return LocalDHFAdapter(dhf_path, auto_commit=False)


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
    """DHF CLI — data-layer operations for the Design History File."""
    ctx.ensure_object(dict)
    ctx.obj["dhf"] = _resolve_dhf(dhf)


# ---------------------------------------------------------------------------
# item group
# ---------------------------------------------------------------------------

@main.group()
def item() -> None:
    """Commands for managing DHF items (CRUD)."""


@item.command("get")
@click.argument("item_id")
@click.pass_context
def item_get(ctx: click.Context, item_id: str) -> None:
    """Get a single DHF item by ID. Outputs JSON."""
    adapter = _make_adapter(ctx.obj["dhf"])
    result = adapter.get_item(item_id)
    if result is None:
        click.echo(f"ERROR: Item '{item_id}' not found.", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))


@item.command("list")
@click.option("--type", "doc_type", default=None, metavar="CODE", help="Filter by doc type code (e.g. SYS).")
@click.pass_context
def item_list(ctx: click.Context, doc_type: str | None) -> None:
    """List DHF items. Outputs one JSON object per line."""
    adapter = _make_adapter(ctx.obj["dhf"])
    items = adapter.list_items(doc_type)
    for it in items:
        click.echo(json.dumps(it, default=str))
    click.echo(f"({len(items)} item(s))", err=True)


@item.command("create")
@click.option("--type", "doc_type", required=True, metavar="CODE", help="Doc type code (e.g. SYS, SRS).")
@click.option("--data", required=True, metavar="JSON", help="Item fields as JSON object.")
@click.option("--author", default="cli", show_default=True, help="Author name for git commit.")
@click.option("--cr", "cr_id", default=None, metavar="CR_ID", help="Change Request ID.")
@click.pass_context
def item_create(ctx: click.Context, doc_type: str, data: str, author: str, cr_id: str | None) -> None:
    """Create a new DHF item. Outputs the created item as JSON."""
    import json as _json
    try:
        item_data = _json.loads(data)
    except _json.JSONDecodeError as e:
        click.echo(f"ERROR: --data is not valid JSON: {e}", err=True)
        sys.exit(1)
    item_data["type"] = doc_type
    adapter = _make_adapter(ctx.obj["dhf"])
    from utils.exceptions import ValidationError
    try:
        result = adapter.create_item(item_data, author=author, cr_id=cr_id)
    except (ValidationError, ValueError) as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))
    click.echo(f"✓ Created {result['id']}.", err=True)


@item.command("update")
@click.argument("item_id")
@click.option("--data", required=True, metavar="JSON", help="Fields to update as JSON (merged into existing).")
@click.option("--author", default="cli", show_default=True, help="Author name for git commit.")
@click.option("--cr", "cr_id", default=None, metavar="CR_ID", help="Change Request ID.")
@click.pass_context
def item_update(ctx: click.Context, item_id: str, data: str, author: str, cr_id: str | None) -> None:
    """Update fields of an existing DHF item."""
    import json as _json
    try:
        update_data = _json.loads(data)
    except _json.JSONDecodeError as e:
        click.echo(f"ERROR: --data is not valid JSON: {e}", err=True)
        sys.exit(1)
    adapter = _make_adapter(ctx.obj["dhf"])
    result = adapter.update_item(item_id, update_data, author=author, cr_id=cr_id)
    if result is None:
        click.echo(f"ERROR: Item '{item_id}' not found.", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))
    click.echo(f"✓ Updated {item_id}.", err=True)


@item.command("delete")
@click.argument("item_id")
@click.option("--author", default="cli", show_default=True, help="Author name for git commit.")
@click.pass_context
def item_delete(ctx: click.Context, item_id: str, author: str) -> None:
    """Delete a DHF item. Exits 1 if item not found."""
    adapter = _make_adapter(ctx.obj["dhf"])
    success = adapter.delete_item(item_id, author=author)
    if not success:
        click.echo(f"ERROR: Item '{item_id}' not found or could not be deleted.", err=True)
        sys.exit(1)
    click.echo(json.dumps({"deleted": item_id}))
    click.echo(f"✓ Deleted {item_id}.", err=True)


# ---------------------------------------------------------------------------
# validate group
# ---------------------------------------------------------------------------

@main.group()
def validate() -> None:
    """Commands for DHF data validation."""


@validate.command("schema")
@click.pass_context
def validate_schema(ctx: click.Context) -> None:
    """Validate all DHF items against their doc-type schema.

    Exits 1 if any YAML contains unknown or invalid fields.
    """
    dhf_path: Path = ctx.obj["dhf"]
    click.echo(f"Validating schema at: {dhf_path}", err=True)
    from utils.exceptions import ValidationError
    try:
        adapter = _make_adapter(dhf_path)
        result = adapter.validate_schema()
    except ValidationError as e:
        click.echo(f"SCHEMA ERROR: {e}", err=True)
        sys.exit(1)
    if not result['valid']:
        for err in result.get('errors', []):
            click.echo(f"  ✗ {err}", err=True)
        sys.exit(1)
    click.echo(f"✓ All {result.get('item_count', 0)} items passed schema validation.", err=True)


# ---------------------------------------------------------------------------
# config group
# ---------------------------------------------------------------------------

@main.group()
def config() -> None:
    """Commands for inspecting DHF configuration."""


@config.command("doc-types")
@click.pass_context
def config_doc_types(ctx: click.Context) -> None:
    """List all configured doc types. Outputs JSON."""
    adapter = _make_adapter(ctx.obj["dhf"])
    cfg = adapter.get_project_config()
    result = [{"code": dt.code, "name": dt.name, "prefix": dt.prefix} for dt in cfg.doc_types]
    click.echo(json.dumps(result, default=str))


# ---------------------------------------------------------------------------
# doc group
# ---------------------------------------------------------------------------

@main.group()
def doc() -> None:
    """Commands for document generation."""


@doc.command("list")
@click.pass_context
def doc_list(ctx: click.Context) -> None:
    """List available document type codes."""
    adapter = _make_adapter(ctx.obj["dhf"])
    click.echo(json.dumps({"doc_types": adapter.get_available_doc_types()}))


@doc.command("generate")
@click.argument("doc_type")
@click.pass_context
def doc_generate(ctx: click.Context, doc_type: str) -> None:
    """Generate specification document(s).

    DOC_TYPE is a configured code (e.g. SYS, SYSARCH) or ALL.
    """
    adapter = _make_adapter(ctx.obj["dhf"])
    codes = adapter.get_available_doc_types() if doc_type.upper() == "ALL" else [doc_type]
    for code in codes:
        try:
            result = adapter.generate_doc(code)
            click.echo(json.dumps(result))
            click.echo(f"✓ {code} → {result['output_path']}", err=True)
        except Exception as e:
            click.echo(f"✗ {code}: {e}", err=True)
            if len(codes) == 1:
                raise SystemExit(1)


@doc.command("export")
@click.argument("doc_type")
@click.pass_context
def doc_export(ctx: click.Context, doc_type: str) -> None:
    """Regenerate spec and export to PDF.

    DOC_TYPE is a configured code (e.g. SYS) or ALL.
    """
    adapter = _make_adapter(ctx.obj["dhf"])
    codes = adapter.get_available_doc_types() if doc_type.upper() == "ALL" else [doc_type]
    for code in codes:
        try:
            result = adapter.export_pdf(code)
            click.echo(json.dumps(result))
            click.echo(f"✓ {code} → {result['pdf_path']}", err=True)
        except Exception as e:
            click.echo(f"✗ {code}: {e}", err=True)
            if len(codes) == 1:
                raise SystemExit(1)
