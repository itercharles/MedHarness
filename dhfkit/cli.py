"""DHF CLI — standalone data-layer operations (no medharness dependency)."""

import json
import os
import shutil
import sys
from pathlib import Path

import click
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


@item.command("transitions")
@click.argument("item_id")
@click.pass_context
def item_transitions(ctx: click.Context, item_id: str) -> None:
    """List available lifecycle transitions for an item. Outputs JSON."""
    adapter = _make_adapter(ctx.obj["dhf"])
    it = adapter.get_item(item_id)
    if it is None:
        click.echo(f"ERROR: Item '{item_id}' not found.", err=True)
        sys.exit(1)
    transitions = adapter.get_available_transitions(item_id)
    click.echo(json.dumps({
        "item_id": item_id,
        "current_status": it.get("status"),
        "transitions": transitions,
    }, default=str))


@item.command("transition")
@click.argument("item_id")
@click.argument("to_state")
@click.option("--by", "performed_by", default="cli", show_default=True, help="User performing the transition.")
@click.pass_context
def item_transition(ctx: click.Context, item_id: str, to_state: str, performed_by: str) -> None:
    """Execute a lifecycle state transition for an item."""
    adapter = _make_adapter(ctx.obj["dhf"])
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
    if result.get("orphans"):
        blocking.append(f"{len(result['orphans'])} orphan(s)")
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


@validate.command("traceability")
@click.option("--fail-on-uncovered", is_flag=True, default=False,
              help="Exit 1 if any items lack downstream coverage (default: warn only).")
@click.option("--report", "report_path", default=None, metavar="PATH",
              help="Write full traceability report as JSON to this file.")
@click.pass_context
def validate_traceability(ctx: click.Context, fail_on_uncovered: bool, report_path: str | None) -> None:
    """Check required traceability, orphan detection, and coverage.

    Exits 1 on required traceability failures or orphaned items.
    Exits 1 on uncovered items only when --fail-on-uncovered is set.
    """
    dhf_path: Path = ctx.obj["dhf"]
    adapter = _make_adapter(dhf_path)
    result = adapter.validate_traceability()

    # Report required traceability failures
    required = result.get("required", {})
    for f in required.get("failures", []):
        click.echo(f"  ✗ REQUIRED {f['id']}: {f['issue']}", err=True)

    # Report deprecation warnings (deduplicated)
    seen_warnings = set()
    for w in result.get("deprecation_warnings", []):
        if w not in seen_warnings:
            seen_warnings.add(w)
            click.echo(f"  ⚠ DEPRECATED {w}", err=True)

    # Report orphans (deprecated allowed_parents)
    for o in result["orphans"]:
        click.echo(f"  ✗ ORPHAN {o['id']}: {o['issue']}", err=True)

    # Report dangling links — always blocking, distinct from coverage gaps
    dangling = result.get("dangling", [])
    for d in dangling:
        click.echo(
            f"  ✗ DANGLING {d['source']}.{d['field']} → {d['target']}: target does not exist",
            err=True,
        )

    # Report coverage per matrix pair. Uncovered items are advisory unless
    # --fail-on-uncovered is set, so label them WARN rather than implying a
    # blocked build.
    gap_label = "✗" if fail_on_uncovered else "⚠"
    for c in result["coverage"]:
        status = "✓" if c["passed"] else gap_label
        click.echo(
            f"  {status} {c['parent_type']} → {c['child_type']}: "
            f"{c['covered']}/{c['total']} covered",
            err=True,
        )
        for uid in c["uncovered"]:
            click.echo(f"      ↳ uncovered: {uid}", err=True)

    click.echo(_traceability_summary(result, fail_on_uncovered), err=True)

    if report_path:
        import json as _json
        Path(report_path).write_text(_json.dumps(result, indent=2, default=str))
        click.echo(f"✓ Traceability report written to {report_path}", err=True)

    if not required.get("passed", True):
        sys.exit(1)
    if result["orphans"]:
        sys.exit(1)
    if dangling:
        sys.exit(1)
    if fail_on_uncovered and not result["passed"]:
        sys.exit(1)


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
    result = [{"code": dt.code, "name": dt.name, "prefix": dt.prefix} for dt in adapter._config.doc_types]
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


# ---------------------------------------------------------------------------
# test group
# ---------------------------------------------------------------------------

@main.group()
def test() -> None:
    """Commands for managing test results stored in the DHF."""


@test.command("list")
@click.option("--status", "status_filter", default=None, metavar="STATUS",
              help="Filter by testing_status (PASS, FAIL, SKIP).")
@click.pass_context
def test_list(ctx: click.Context, status_filter: str) -> None:
    """List all stored test results, one JSON object per line."""
    from dhfkit.result_store import ResultStore
    dhf_path: Path = ctx.obj["dhf"]
    store = ResultStore(dhf_path)
    records = store.get_all(status_filter)
    for record in records.values():
        click.echo(json.dumps(record, default=str))
    click.echo(f"({len(records)} record(s))", err=True)


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
        dhfkit --dhf path/to/DHF validate traceability
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
    click.echo(f"  dhfkit --dhf {dhf_path} validate traceability", err=True)


@main.command("report")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", show_default=True)
@click.option("--out", "out_path", default=None, type=click.Path(dir_okay=False, path_type=Path),
              help="Write report to this file instead of stdout.")
@click.pass_context
def report_cmd(ctx: click.Context, fmt: str, out_path: Path | None) -> None:
    """Print a human-readable traceability coverage report.

    Shows required-link failures, coverage gaps, and a per-matrix breakdown.
    Use --format json to get the raw validation dict for scripting.
    """
    from dhfkit.traceability import format_traceability_report
    adapter = _make_adapter(ctx.obj["dhf"])
    result = adapter.validate_traceability()
    if fmt == "json":
        output = json.dumps(result, indent=2)
    else:
        output = format_traceability_report(result)
    if out_path:
        out_path.write_text(output + "\n", encoding="utf-8")
        click.echo(f"Report written to {out_path}", err=True)
    else:
        click.echo(output)
    if not result.get("passed"):
        sys.exit(1)


@main.command("soup-sync")
@click.option("--manifest", "manifest_paths", multiple=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              metavar="PATH",
              help="Manifest file to parse (repeatable). When omitted, reads "
                   "DHF/config/soup-sources.yaml or auto-discovers manifests.")
@click.option("--from-command", "extra_commands", multiple=True, metavar="CMD",
              help="Shell command whose stdout is NDJSON {name,version,ecosystem} "
                   "(repeatable). Use to plug in syft, trivy, or custom scripts.")
@click.option("--write", is_flag=True, default=False,
              help="Create/update SOUP items in the DHF (dry-run by default)")
@click.option("--author", default="ci", show_default=True, metavar="NAME")
@click.option("--cr", "cr_id", default=None, metavar="CR_ID",
              help="CR to attribute writes to")
@click.pass_context
def soup_sync_cmd(
    ctx: click.Context,
    manifest_paths: tuple[Path, ...],
    extra_commands: tuple[str, ...],
    write: bool,
    author: str,
    cr_id: str | None,
) -> None:
    """Sync SOUP items in the DHF with package manifests.

    Without --manifest / --from-command, reads DHF/config/soup-sources.yaml
    (if present) or auto-discovers manifest files in the project root.

    Supported manifest formats: requirements.txt, uv.lock, poetry.lock,
    pyproject.toml, package.json, package-lock.json, go.mod, Cargo.lock, pom.xml.

    Compares found packages against existing SOUP items and reports new,
    version-drifted, and orphaned entries. Pass --write to apply changes.
    """
    from dhfkit.soup_sync import sync_soup_items
    dhf: Path = ctx.obj["dhf"]
    result = sync_soup_items(
        dhf, list(manifest_paths),
        write=write, author=author, cr_id=cr_id,
        extra_commands=list(extra_commands),
    )
    click.echo(json.dumps(result))
    create_count = len(result.get("to_create") or [])
    update_count = len(result.get("to_update") or [])
    orphan_count = len(result.get("orphans") or [])
    written = (
        f" ({len(result.get('items_created', []))} created, {len(result.get('items_updated', []))} updated)"
        if write else " (dry-run)"
    )
    click.echo(
        f"OK soup-sync{written}: +{create_count} new, ~{update_count} drift, "
        f"{orphan_count} orphan(s), {result.get('matched_count', 0)} matched.",
        err=True,
    )
    if result.get("outcome") == "completed_with_errors":
        for err in result.get("errors") or []:
            click.echo(f"  FAIL: {err}", err=True)
        sys.exit(1)


@main.command("release-baseline")
@click.option("--version", "version", required=True, metavar="VERSION",
              help="Release version string (e.g. 1.0.0)")
@click.option("--manifest", "manifest_paths", multiple=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              metavar="PATH", help="requirements.txt or package.json for BOM (repeatable)")
@click.option("--cr", "cr_ids", multiple=True, metavar="CR_ID",
              help="CR to include (repeatable; auto-collected if omitted)")
@click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path),
              default=Path("."), show_default=True,
              help="Directory to write release-baseline.json and software-bom.json")
@click.option("--write", is_flag=True, default=False,
              help="Create a REL item in the DHF (dry-run by default)")
@click.option("--author", default="ci", show_default=True, metavar="NAME")
@click.pass_context
def release_baseline_cmd(
    ctx: click.Context, version: str, manifest_paths: tuple[Path, ...],
    cr_ids: tuple[str, ...], out_dir: Path, write: bool, author: str,
) -> None:
    """Build an IEC 62304 §9 release baseline.

    Verifies all included CRs are in `completed` state, collects a
    software BOM from DHF SOUP items and manifest packages, and writes
    release-baseline.json and software-bom.json to --out-dir.
    Pass --write to also create a REL item in the DHF.
    CRs are auto-collected (completed, not yet in any REL) when --cr is omitted.
    """
    from dhfkit.release_baseline import build_release_baseline
    dhf: Path = ctx.obj["dhf"]
    result = build_release_baseline(
        dhf, version, list(manifest_paths), list(cr_ids), out_dir,
        write=write, author=author,
    )
    click.echo(json.dumps(result))
    if result.get("outcome") == "completed_with_errors":
        for err in result.get("errors") or []:
            click.echo(f"  FAIL: {err}", err=True)
        sys.exit(1)
    rel_note = f" → {result['rel_uid']}" if result.get("rel_uid") else ""
    click.echo(
        f"OK release-baseline {version}{rel_note}: "
        f"{len(result.get('cr_ids', []))} CR(s), "
        f"{result.get('soup_count', 0)} SOUP item(s), "
        f"{len(result.get('artifacts', []))} artifact(s) written.",
        err=True,
    )


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
