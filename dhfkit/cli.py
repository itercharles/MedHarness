"""DHF CLI — standalone data-layer operations (no medharness dependency)."""

import json
import os
import shutil
import sys
from pathlib import Path

import click

from dhfkit.cli_errors import DHFAwareGroup
import yaml


def _resolve_dhf(dhf_option: str | None) -> Path:
    """Resolve the DHF directory from CLI option, env var, or default."""
    if dhf_option:
        return Path(dhf_option)
    env = os.environ.get("COMPLIANTFLOW_DHF")
    if env:
        return Path(env)
    raise click.UsageError("--dhf or COMPLIANTFLOW_DHF must be set")


def _make_adapter(dhf_path: Path):
    """Instantiate LocalDHFAdapter."""
    from dhfkit.local_adapter import LocalDHFAdapter
    return LocalDHFAdapter(dhf_path, auto_commit=False)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group(cls=DHFAwareGroup)
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
    from dhfkit.exceptions import ValidationError
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






@item.command("transition")
@click.argument("item_id")
@click.argument("to_state", required=False)
@click.option("--by", "performed_by", default="cli", show_default=True, help="User performing the transition.")
@click.pass_context
def item_transition(ctx: click.Context, item_id: str, to_state: str | None, performed_by: str) -> None:
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
        result = adapter.execute_transition(item_id, to_state, performed_by=performed_by)
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
        click.echo(f"SCHEMA ERROR: {e}", err=True)
        sys.exit(1)
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

@main.group()
def doc() -> None:
    """Commands for document generation."""












# ---------------------------------------------------------------------------
# test group
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
@click.option("--format", "fmt", type=click.Choice(["html", "pdf"]), default="html",
              show_default=True,
              help="HTML needs no native libraries and works on a base install; "
                   "PDF requires medharness[docs] plus cairo/pango.")
@click.option("--out-dir", "out_dir", default=None,
              type=click.Path(file_okay=False, path_type=Path),
              help="Destination directory (default: DHF/documents/exports).")
@click.pass_context
def doc_export(ctx: click.Context, doc_type: str, fmt: str, out_dir: Path | None) -> None:
    """Regenerate spec and export it.

    DOC_TYPE is a configured code (e.g. SYS) or ALL.
    """
    adapter = _make_adapter(ctx.obj["dhf"])
    codes = adapter.get_available_doc_types() if doc_type.upper() == "ALL" else [doc_type]
    key = f"{fmt}_path"
    for code in codes:
        try:
            result = (adapter.export_html(code, out_dir) if fmt == "html"
                      else adapter.export_pdf(code, out_dir))
            click.echo(json.dumps(result))
            click.echo(f"✓ {code} → {result[key]}", err=True)
        except Exception as e:
            click.echo(f"✗ {code}: {e}", err=True)
            if len(codes) == 1:
                raise SystemExit(1)


@main.command("init")
@click.option("--project-name", default="My Project", show_default=True,
              help="Human-readable project name written into global.yaml.")
@click.pass_context
def init_cmd(ctx: click.Context, project_name: str) -> None:
    """Bootstrap a minimal standalone DHF.

    Creates the DHF directory with a minimal config (global.yaml + core
    doc types), empty item directories, and a documents/specs/ folder so
    item and document commands work immediately.

    \b
    Example:
        dhfkit --dhf path/to/DHF init --project-name "My Device"
        dhfkit --dhf path/to/DHF item create SYS --data '{"title": "..."}'
        dhfkit --dhf path/to/DHF validate schema
    """
    dhf_path: Path = ctx.obj["dhf"]
    _templates = Path(__file__).parent / "templates"

    if dhf_path.exists() and any(dhf_path.iterdir()):
        raise click.ClickException(f"{dhf_path} already exists and is not empty.")

    # config/global.yaml — minimal standalone version (no lifecycle states, no AI harness)
    config_dir = dhf_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    dhf_name = dhf_path.name  # used in output paths so doc generation resolves correctly
    (config_dir / "global.yaml").write_text(
        yaml.dump({"project_name": project_name}, default_flow_style=False, allow_unicode=True)
        + "\n"
        "required_traceability:\n"
        "- source_type: SRS\n"
        "  direction: upstream\n"
        "  field: derives_from\n"
        "  target_type: SYS\n"
        "  min_count: 1\n"
        "- source_type: RCM\n"
        "  direction: upstream\n"
        "  field: mitigates\n"
        "  target_type: RISK\n"
        "  min_count: 1\n"
        "- source_type: RCM\n"
        "  direction: upstream\n"
        "  field: implements\n"
        "  target_type: SYS\n"
        "  min_count: 1\n"
        "\n"
        "traceability_matrices:\n"
        "- name: Requirements Chain\n"
        "  description: System to software requirements\n"
        "  path:\n"
        "  - SYS\n"
        "  - SRS\n"
        "- name: Risk to Control Measures\n"
        "  description: Risks and their controls\n"
        "  path:\n"
        "  - RISK\n"
        "  - RCM\n"
        "\n"
        f"document_specifications:\n"
        f"  SYS:\n"
        f"    source: requirements_specification.md.j2\n"
        f"    output: {dhf_name}/documents/specs/system_requirement_specification.md\n"
        f"    doc_type_name: System Requirement\n"
        f"  SRS:\n"
        f"    source: requirements_specification.md.j2\n"
        f"    output: {dhf_name}/documents/specs/software_requirement_specification.md\n"
        f"    doc_type_name: Software Requirement\n"
        f"  RISK:\n"
        f"    source: risk_specification.md.j2\n"
        f"    output: {dhf_name}/documents/specs/risk_analysis_specification.md\n"
        f"    doc_type_name: Risk Analysis\n"
        f"  RCM:\n"
        f"    source: rcm_specification.md.j2\n"
        f"    output: {dhf_name}/documents/specs/risk_control_measures_specification.md\n"
        f"    doc_type_name: Risk Control Measures\n",
        encoding="utf-8",
    )

    # config/doc_types/ — copy core four from bundled templates
    doc_types_dir = config_dir / "doc_types"
    doc_types_dir.mkdir(exist_ok=True)
    for code in ("sys", "srs", "risk", "rcm"):
        src = _templates / "config" / "doc_types" / f"{code}.yaml"
        shutil.copy2(src, doc_types_dir / f"{code}.yaml")

    # empty item directories
    for directory in ("02_sys", "03_srs", "10_risk", "11_rcm"):
        (dhf_path / "items" / directory).mkdir(parents=True, exist_ok=True)

    # documents/specs/ — copy the four core Jinja2 templates so doc generate works
    specs_dir = dhf_path / "documents" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    for tmpl in ("requirements_specification.md.j2", "risk_specification.md.j2", "rcm_specification.md.j2"):
        shutil.copy2(_templates / "specs" / tmpl, specs_dir / tmpl)

    click.echo(json.dumps({"created": str(dhf_path), "project_name": project_name}))
    click.echo(f"DHF initialised at {dhf_path}", err=True)
    click.echo("Next steps:", err=True)
    click.echo(f"  dhfkit --dhf {dhf_path} item create SYS --data '{{\"title\": \"My first requirement\"}}'", err=True)
    click.echo(f"  medharness --dhf {dhf_path} verify dhf", err=True)
