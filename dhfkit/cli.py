"""DHF CLI — standalone data-layer operations (no medharness dependency)."""

import json
import sys
from pathlib import Path

import click

from dhfkit.cli_errors import DHFAwareGroup
import yaml


def _make_adapter(dhf_path: Path):
    """Instantiate LocalDHFAdapter."""
    from dhfkit.local_adapter import LocalDHFAdapter
    return LocalDHFAdapter(dhf_path)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group(cls=DHFAwareGroup)
@click.option(
    "--dhf",
    default="DHF",
    show_default=True,
    metavar="PATH",
    help="Path to the DHF directory. Goes before the command.",
)
@click.pass_context
def main(ctx: click.Context, dhf: str) -> None:
    """DHF CLI — data-layer operations for the Design History File."""
    ctx.ensure_object(dict)
    ctx.obj["dhf"] = Path(dhf)


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
    adapter = _make_adapter(ctx.obj["dhf"])
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
    adapter = _make_adapter(ctx.obj["dhf"])
    result = adapter.update_item(item_id, update_data)
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
    adapter = _make_adapter(ctx.obj["dhf"])
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
    from dhfkit.exceptions import ValidationError
    try:
        adapter = _make_adapter(dhf_path)
        result = adapter.validate_schema()
    except ValidationError as e:
        click.echo(json.dumps({"valid": False, "item_count": 0, "errors": [str(e)]}))
        click.echo(f"SCHEMA ERROR: {e}", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))
    if not result['valid']:
        for err in result.get('errors', []):
            click.echo(f"  ✗ {err}", err=True)
        sys.exit(1)
    click.echo(f"✓ All {result.get('item_count', 0)} items passed schema validation.", err=True)


def _traceability_summary(result: dict, fail_on_uncovered: bool) -> str:
    """Summarise a traceability result by what actually blocks the exit code.

    check_traceability() reports uncovered items as a failure, but the CLI only
    exits non-zero for them under --fail-on-uncovered. Reporting those as "FAIL"
    regardless would tell CI readers a green build had blocked.
    """
    blocking, advisory = [], []

    required_failures = result.get("required", {}).get("failures", [])
    if required_failures:
        blocking.append(f"{len(required_failures)} required failure(s)")
    if result.get("dangling"):
        blocking.append(f"{len(result['dangling'])} dangling link(s)")

    uncovered = sum(len(c.get("uncovered", [])) for c in result.get("coverage", []))
    if uncovered:
        (blocking if fail_on_uncovered else advisory).append(f"{uncovered} uncovered item(s)")

    if blocking:
        note = f" ({', '.join(advisory)} advisory)" if advisory else ""
        return f"FAIL — {', '.join(blocking)}{note}"
    if advisory:
        return (
            f"PASS — {', '.join(advisory)} not blocking; "
            "re-run with --fail-on-uncovered to enforce coverage."
        )
    return "All checks passed."


# ---------------------------------------------------------------------------
# config group
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# doc group
# ---------------------------------------------------------------------------

@main.command("sbom")
@click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path),
              help="Where to write the SBOM (default: <dhf>/sbom.cdx.json).")
@click.option("--stdout", "to_stdout", is_flag=True,
              help="Write the document to stdout instead of a file.")
@click.pass_context
def sbom_cmd(ctx: click.Context, output_path: Path | None, to_stdout: bool) -> None:
    """Generate a CycloneDX SBOM from the DHF's SOUP items.

    The SOUP register already holds what an SBOM needs, recorded there because
    IEC 62304 §8.1.2 asks for it. This serialises it into the format FDA
    cybersecurity guidance and the EU Cyber Resilience Act expect.

    A component whose ecosystem has no package-URL type is included without a
    `purl` rather than given a guessed one — a wrong purl resolves against a
    real registry, so an absent one is safer.

    Regenerating an unchanged SBOM leaves the file alone, including its
    timestamp, so a regeneration is not a diff.
    """
    from importlib.metadata import version as pkg_version

    from dhfkit.local_adapter import LocalDHFAdapter
    from dhfkit.sbom import build_sbom, purl_gap, write_sbom

    dhf: Path = ctx.obj["dhf"]
    adapter = LocalDHFAdapter(dhf)
    soup_items = [
        i for i in adapter.list_items()
        if str(i.get("id", "")).startswith("SOUP-")
    ]
    try:
        tool_version = pkg_version("dhfkit")
    except Exception:
        tool_version = "unknown"

    document = build_sbom(
        soup_items,
        project_name=adapter._config.project_name or dhf.resolve().parent.name,
        tool_version=tool_version,
    )

    if to_stdout:
        click.echo(json.dumps(document, indent=2))
        return

    target = output_path or (dhf / "sbom.cdx.json")
    written, changed = write_sbom(document, target)
    click.echo(json.dumps({
        "path": str(written),
        "components": len(document["components"]),
        "without_purl": sum(1 for c in document["components"] if "purl" not in c),
        "changed": changed,
    }))
    n = len(document["components"])
    click.echo(
        f"{'Wrote' if changed else 'Unchanged'} {written} — {n} component(s).",
        err=True,
    )
    # Name the cause per component. A bare count says there is a problem without
    # saying which of the two it is, and they need different fixes.
    for component in document["components"]:
        if "purl" in component:
            continue
        props = {p["name"]: p["value"] for p in component.get("properties", [])}
        reason = purl_gap(
            component["name"], component["version"], props.get("dhfkit:ecosystem", "")
        )
        click.echo(
            f"WARN [sbom] {component['bom-ref']}: no purl — {reason}", err=True
        )


@main.command("doc")
@click.argument("doc_type")
@click.option("--format", "fmt", type=click.Choice(["md", "html", "pdf"]), default="md",
              show_default=True,
              help="md renders the specification from the items. html and pdf render "
                   "it and export it; pdf needs medharness[docs] plus cairo/pango.")
@click.option("--out-dir", "out_dir", default=None,
              type=click.Path(file_okay=False, path_type=Path),
              help="Where html and pdf go (default: DHF/documents/exports).")
@click.pass_context
def doc_cmd(ctx: click.Context, doc_type: str, fmt: str, out_dir: Path | None) -> None:
    """Render a specification from the items.

    DOC_TYPE is a configured code (e.g. SRS) or ALL, one JSON object per type:
    {doc_type, md_path, version}, plus html_path or pdf_path.
    """
    adapter = _make_adapter(ctx.obj["dhf"])
    codes = adapter.get_available_doc_types() if doc_type.upper() == "ALL" else [doc_type]
    for code in codes:
        try:
            if fmt == "md":
                generated = adapter.generate_doc(code)
                result = {"doc_type": generated["doc_type"], "md_path": generated["output_path"],
                          "version": generated["version"]}
            else:
                result = (adapter.export_html(code, out_dir) if fmt == "html"
                          else adapter.export_pdf(code, out_dir))
            click.echo(json.dumps(result))
            click.echo(f"✓ {code} → {result.get(f'{fmt}_path')}", err=True)
        except Exception as e:
            click.echo(f"✗ {code}: {e}", err=True)
            if len(codes) == 1:
                raise SystemExit(1)


@main.command("init")
@click.option("--project-name", default="My Project", show_default=True,
              help="Human-readable project name written into global.yaml.")
@click.pass_context
def init_cmd(ctx: click.Context, project_name: str) -> None:
    """A bare DHF: its config and an empty items directory.

    The doc types, lifecycle, traceability rules and templates come from the
    package's defaults; `global.yaml` holds only what this DHF changes.

    \b
    Example:
        dhfkit --dhf path/to/DHF init --project-name "My Device"
        dhfkit --dhf path/to/DHF item create --type SYS --data '{"title": "..."}'
        dhfkit --dhf path/to/DHF validate schema
    """
    dhf_path: Path = ctx.obj["dhf"]
    if dhf_path.exists() and any(dhf_path.iterdir()):
        raise click.ClickException(f"{dhf_path} already exists and is not empty.")

    config_dir = dhf_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "global.yaml").write_text(
        "# Anything not set here comes from the defaults shipped with dhfkit.\n"
        + yaml.dump({"project_name": project_name}, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    # One directory per item type, so it is plain where a new item goes.
    from dhfkit.models.config import ProjectConfig

    for doc_type in ProjectConfig.load(config_dir).doc_types:
        (dhf_path / "items" / (doc_type.directory or doc_type.code.lower())).mkdir(
            parents=True, exist_ok=True)

    click.echo(json.dumps({"created": str(dhf_path), "project_name": project_name}))
    click.echo(f"DHF initialised at {dhf_path}", err=True)
    click.echo("Next steps:", err=True)
    click.echo(f"  dhfkit --dhf {dhf_path} item create --type SYS --data '{{\"title\": \"My first requirement\"}}'", err=True)
    click.echo(f"  medharness --dhf {dhf_path} verify dhf", err=True)
