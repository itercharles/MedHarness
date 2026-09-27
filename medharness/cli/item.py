"""`item` — read and write DHF items."""

from __future__ import annotations

import json
import sys

import click

from dhfkit.local_adapter import LocalDHFAdapter


def register(main):
    @main.group("item")
    def item() -> None:
        """Read and write DHF items: list, get, create, update, transition."""

    @item.command("get")
    @click.argument("item_id")
    @click.pass_context
    def item_get(ctx: click.Context, item_id: str) -> None:
        """Get a single DHF item by ID. Outputs JSON."""
        adapter = LocalDHFAdapter(ctx.obj["dhf"])
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
        adapter = LocalDHFAdapter(ctx.obj["dhf"])
        items = adapter.list_items(doc_type)
        for it in items:
            click.echo(json.dumps(it, default=str))
        click.echo(f"({len(items)} item(s))", err=True)


    @item.command("create")
    @click.option("--type", "doc_type", required=True, metavar="CODE", help="Doc type code (e.g. SYS, SRS).")
    @click.option("--data", required=True, metavar="JSON", help="Item fields as JSON object.")
    @click.pass_context
    def item_create(ctx: click.Context, doc_type: str, data: str) -> None:
        """Create a new DHF item. Outputs the created item as JSON."""
        import json as _json
        try:
            item_data = _json.loads(data)
        except _json.JSONDecodeError as e:
            click.echo(f"ERROR: --data is not valid JSON: {e}", err=True)
            sys.exit(1)
        item_data["type"] = doc_type
        adapter = LocalDHFAdapter(ctx.obj["dhf"])
        from dhfkit.exceptions import ValidationError
        try:
            result = adapter.create_item(item_data)
        except (ValidationError, ValueError) as e:
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)
        click.echo(json.dumps(result, default=str))
        click.echo(f"✓ Created {result['id']}.", err=True)


    @item.command("update")
    @click.argument("item_id")
    @click.option("--data", required=True, metavar="JSON", help="Fields to update as JSON (merged into existing).")
    @click.pass_context
    def item_update(ctx: click.Context, item_id: str, data: str) -> None:
        """Update fields of an existing DHF item."""
        import json as _json
        try:
            update_data = _json.loads(data)
        except _json.JSONDecodeError as e:
            click.echo(f"ERROR: --data is not valid JSON: {e}", err=True)
            sys.exit(1)
        adapter = LocalDHFAdapter(ctx.obj["dhf"])
        from dhfkit.exceptions import RefusedWrite
        try:
            result = adapter.update_item(item_id, update_data)
        except RefusedWrite as e:
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)
        if result is None:
            click.echo(f"ERROR: Item '{item_id}' not found.", err=True)
            sys.exit(1)
        click.echo(json.dumps(result, default=str))
        click.echo(f"✓ Updated {item_id}.", err=True)


    @item.command("transition")
    @click.argument("item_id")
    @click.argument("to_state", required=False)
    @click.pass_context
    def item_transition(ctx: click.Context, item_id: str, to_state: str | None) -> None:
        """Move an item to TO_STATE, or list where it can go when TO_STATE is omitted."""
        adapter = LocalDHFAdapter(ctx.obj["dhf"])
        if to_state is None:
            it = adapter.get_item(item_id)
            if it is None:
                click.echo(f"ERROR: Item '{item_id}' not found.", err=True)
                sys.exit(1)
            click.echo(json.dumps({
                "item_id": item_id,
                "current_status": it.get("status"),
                "transitions": adapter.get_available_transitions(item_id),
            }, default=str))
            return
        try:
            result = adapter.execute_transition(item_id, to_state)
        except ValueError as e:
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)
        click.echo(json.dumps(result, default=str))
        click.echo(f"✓ {item_id}: {result.get('status')}.", err=True)
