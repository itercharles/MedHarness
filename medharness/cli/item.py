"""`item` — read and write DHF items."""

from __future__ import annotations

import json
from pathlib import Path

import click

from dhfkit.store import open_store


def _json_object(data: str) -> dict:
    """`--data` parsed, or exit 1: a JSON array or scalar is not a set of fields.

    `@FILE` reads the JSON from a file and `-` from standard input; JSON that is an object never starts with either.
    """
    if data == "-":
        data = click.get_text_stream("stdin").read()
    elif data.startswith("@"):
        try:
            data = Path(data[1:]).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise click.ClickException(f"--data: cannot read {data[1:]}: {getattr(e, 'strerror', None) or e}") from e
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
        """List DHF items in ID order. Outputs one JSON object per line."""
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
    @click.option("--data", required=True, metavar="JSON", help="Item fields as a JSON object, or @FILE / - to read it from a file / standard input.")
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
    @click.option("--data", required=True, metavar="JSON", help="Fields to update as a JSON object (merged into existing), or @FILE / - to read it from a file / standard input.")
    @click.pass_context
    def item_update(ctx: click.Context, item_id: str, data: str) -> None:
        """Update fields of an existing DHF item."""
        update_data = _json_object(data)
        adapter = open_store(ctx.obj["dhf"])
        from dhfkit.exceptions import ValidationError
        try:
            result = adapter.update_item(item_id, update_data)
        except (ValidationError, ValueError) as e:
            raise click.ClickException(f"{item_id} not updated: {e}" if not str(e).startswith(item_id) else str(e)) from e
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


    @item.command("approve")
    @click.option("--key", "key_path", required=True, metavar="PATH",
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="The private key to sign with. Never ssh-agent: name the key.")
    @click.option("--release", "release", default=None, metavar="VERSION",
                  help="Sign the documents of this release that the key's roles own (and the release itself, "
                       "for the release role). Needs the manifest `build release --write` made.")
    @click.option("--approvers", "approvers_list", is_flag=True, default=False,
                  help="Instead, approve the current approvers list (DHF/config/approvers.yaml).")
    @click.option("--statement", default="I have reviewed the changes to these documents and approve them for release.",
                  show_default=True, help="What the signer states; it is signed with the approval.")
    @click.option("--yes", is_flag=True, default=False, help="Do not ask for confirmation.")
    @click.pass_context
    def item_approve(ctx: click.Context, key_path: Path, release: str | None, approvers_list: bool,
                     statement: str, yes: bool) -> None:
        """Sign a release's documents, or the approvers list.

        With --release, shows the changes to each document the key's roles own (from the release's
        `changes.md`), asks, then writes one record into the approval log
        (`DHF/approvals/release-VERSION/<ULID>.yaml`) and signs it with the key, so one touch signs
        everything the signer owns. Documents this signer already signed at the same content are
        skipped; with none left it records nothing and says so. Outputs the record and its path as
        JSON. Needs `DHF/config/approvers.yaml`.
        """
        from dhfkit.exceptions import DHFDataError  # noqa: PLC0415
        from medharness.services import approve  # noqa: PLC0415
        from medharness.services.approval import ApprovalError  # noqa: PLC0415

        if (release is None) == (not approvers_list):
            raise click.UsageError("pass exactly one of --release VERSION and --approvers.")
        dhf_path: Path = ctx.obj["dhf"]
        try:
            plan = (approve.prepare_release(dhf_path, key_path, release) if release is not None
                    else approve.prepare_approvers(dhf_path, key_path))
            if plan is None:
                raise click.ClickException("Approvals are not configured: add DHF/config/approvers.yaml first.")
            if not plan.documents:
                click.echo(json.dumps({"summary": f"Nothing to sign for {plan.approver.name} in release {release}."}))
                click.echo("Nothing to sign: no document needs a signature this key's roles may give.", err=True)
                return
            click.echo(f"{plan.approver.name} signs, as {', '.join(plan.roles)}:", err=True)
            for doc in plan.documents:
                click.echo(f"  {doc['id']}", err=True)
                for line in approve.describe(dhf_path, plan, doc["id"]).splitlines():
                    click.echo(f"    {line}", err=True)
            if not yes:
                click.confirm("Sign?", abort=True, err=True)
            created = approve.sign(dhf_path, key_path, plan, statement)
        except (ApprovalError, DHFDataError) as e:
            raise click.ClickException(str(e)) from e
        click.echo(json.dumps(created, default=str))
        click.echo(f"✓ Created {created['id']}, signed with {key_path.name}. Commit it to the release branch.", err=True)
