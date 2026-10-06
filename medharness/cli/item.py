"""`item` — read and write DHF items."""

from __future__ import annotations

import json

import click

from dhfkit.store import open_store


def _json_object(data: str) -> dict:
    """`--data` parsed, or exit 1: a JSON array or scalar is not a set of fields."""
    try:
        value = json.loads(data)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"--data is not valid JSON: {e}") from e
    if not isinstance(value, dict):
        raise click.ClickException("--data must be a JSON object, e.g. '{\"title\": \"...\"}'.")
    return value


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in _strings(v)]
    return []


def _has_every_term(item: dict, terms: list[str]) -> bool:
    text = "\n".join(_strings(item)).casefold()
    return all(term in text for term in terms)


def register(main):
    @main.group("item")
    def item() -> None:
        """Read and write DHF items: list, get, create, update, transition."""

    @item.command("get")
    @click.argument("item_id")
    @click.pass_context
    def item_get(ctx: click.Context, item_id: str) -> None:
        """Get a single DHF item by ID. Outputs JSON."""
        adapter = open_store(ctx.obj["dhf"])
        result = adapter.get_item(item_id)
        if result is None:
            raise click.ClickException(f"Item '{item_id}' not found.")
        click.echo(json.dumps(result, default=str))


    @item.command("list")
    @click.option("--type", "doc_type", default=None, metavar="CODE", help="Filter by doc type code (e.g. SYS).")
    @click.option("--match", "match", default=None, metavar="TEXT",
                  help="Keep items where every word of TEXT occurs, case-insensitively, in any text field.")
    @click.option("--linked-to", "linked_to", default=None, metavar="ID",
                  help="Keep items that link to ID or that ID links to.")
    @click.option("--brief", is_flag=True, help="Print only id, type, title and links.")
    @click.pass_context
    def item_list(ctx: click.Context, doc_type: str | None, match: str | None,
                  linked_to: str | None, brief: bool) -> None:
        """List DHF items. Outputs one JSON object per line."""
        terms = match.casefold().split() if match is not None else None
        if terms == []:
            raise click.ClickException("--match needs at least one word.")
        adapter = open_store(ctx.obj["dhf"])
        items = adapter.list_items(doc_type)
        if linked_to is not None:
            anchor = adapter.get_item(linked_to)
            if anchor is None:
                raise click.ClickException(f"Item '{linked_to}' not found.")
            reached = set(anchor.get("all_linked_uids") or [])
            items = [it for it in items
                     if it["id"] in reached or linked_to in (it.get("all_linked_uids") or [])]
        if terms:
            items = [it for it in items if _has_every_term(it, terms)]
        for it in items:
            if brief:
                it = {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
                      "links": it.get("all_linked_uids") or []}
            click.echo(json.dumps(it, default=str))
        click.echo(f"({len(items)} item(s))", err=True)


    @item.command("create")
    @click.option("--type", "doc_type", required=True, metavar="CODE", help="Doc type code (e.g. SYS, SRS).")
    @click.option("--data", required=True, metavar="JSON", help="Item fields as JSON object.")
    @click.pass_context
    def item_create(ctx: click.Context, doc_type: str, data: str) -> None:
        """Create a new DHF item. Outputs the created item as JSON."""
        item_data = _json_object(data)
        item_data["type"] = doc_type
        adapter = open_store(ctx.obj["dhf"])
        from dhfkit.exceptions import ValidationError
        try:
            result = adapter.create_item(item_data)
        except (ValidationError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        click.echo(json.dumps(result, default=str))
        click.echo(f"✓ Created {result['id']}.", err=True)


    @item.command("update")
    @click.argument("item_id")
    @click.option("--data", required=True, metavar="JSON", help="Fields to update as JSON (merged into existing).")
    @click.pass_context
    def item_update(ctx: click.Context, item_id: str, data: str) -> None:
        """Update fields of an existing DHF item."""
        update_data = _json_object(data)
        adapter = open_store(ctx.obj["dhf"])
        from dhfkit.exceptions import RefusedWrite
        try:
            result = adapter.update_item(item_id, update_data)
        except RefusedWrite as e:
            raise click.ClickException(str(e)) from e
        if result is None:
            raise click.ClickException(f"Item '{item_id}' not found.")
        click.echo(json.dumps(result, default=str))
        click.echo(f"✓ Updated {item_id}.", err=True)


    @item.command("transition")
    @click.argument("item_id")
    @click.argument("to_state", required=False)
    @click.pass_context
    def item_transition(ctx: click.Context, item_id: str, to_state: str | None) -> None:
        """Move an item to TO_STATE, or list where it can go when TO_STATE is omitted."""
        adapter = open_store(ctx.obj["dhf"])
        if to_state is None:
            it = adapter.get_item(item_id)
            if it is None:
                raise click.ClickException(f"Item '{item_id}' not found.")
            click.echo(json.dumps({
                "item_id": item_id,
                "current_status": it.get("status"),
                "transitions": adapter.get_available_transitions(item_id),
            }, default=str))
            return
        try:
            result = adapter.execute_transition(item_id, to_state)
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        click.echo(json.dumps(result, default=str))
        click.echo(f"✓ {item_id}: {result.get('status')}.", err=True)
