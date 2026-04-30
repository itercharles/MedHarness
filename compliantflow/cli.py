"""CompliantFlow CLI — analysis, traceability, and DHF automation facade.

Local DHF providers may still be implemented by a DHF repository's utils layer;
product repositories should call this CLI facade rather than depending on DHF
storage paths or provider-specific commands.
"""

import json
import os
import shutil
import subprocess
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


def _make_core(ctx: click.Context):
    """Instantiate CompliantFlowCore from CLI context.

    Single-project mode (default): uses ``ctx.obj["dhf"]`` path with a
    ``LocalDHFAdapter`` (requires the DHF system to be installed alongside
    this tool, e.g. by cloning compliantflow-dhf into the Python path).

    Multi-project mode: activated when ``--project slug:path`` flags are
    present.  Builds a ``MultiDHFAdapter`` keyed by slug and passes it to
    ``CompliantFlowCore`` unchanged.
    """
    try:
        from dhf_util.local_adapter import LocalDHFAdapter
    except ImportError:
        raise click.ClickException(
            "LocalDHFAdapter not found. Add your DHF system (e.g. compliantflow-dhf) "
            "to the Python path before running the CLI."
        )
    from compliantflow.core import CompliantFlowCore

    projects: dict = ctx.obj.get("projects", {})
    if projects:
        from compliantflow.adapters.multi import MultiDHFAdapter
        adapters = {slug: LocalDHFAdapter(path, auto_commit=False)
                    for slug, path in projects.items()}
        return CompliantFlowCore(MultiDHFAdapter(adapters))

    dhf_path: Path = ctx.obj["dhf"]
    return CompliantFlowCore(LocalDHFAdapter(dhf_path, auto_commit=False))


def _make_adapter(ctx: click.Context):
    """Instantiate the configured DHF adapter for facade operations."""
    if ctx.obj.get("projects"):
        raise click.ClickException("DHF facade commands do not support --project multi-repo mode.")
    try:
        from dhf_util.local_adapter import LocalDHFAdapter
    except ImportError:
        raise click.ClickException(
            "LocalDHFAdapter not found. Add your DHF system to PYTHONPATH before running the CLI."
        )
    return LocalDHFAdapter(ctx.obj["dhf"], auto_commit=False)


def _parse_json_object(data: str) -> dict:
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"expected JSON object: {exc}") from exc
    if not isinstance(parsed, dict):
        raise click.BadParameter("expected JSON object")
    return parsed


def _get_document_with_legacy_fallback(adapter, dhf_path: Path, doc_id: str) -> str | None:
    content = adapter.get_document(doc_id)
    if content is not None:
        return content
    legacy_path = dhf_path.parent / "docs" / "cr-specs" / f"{doc_id}.md"
    if legacy_path.is_file():
        return legacy_path.read_text(encoding="utf-8")
    return None


DEFAULT_ACCEPTANCE_COVERAGE_PAIRS = ("UC:CRS", "CRS:SYS", "SYS:SRS", "SRS:SWDD")
DEFAULT_TRACEABILITY_DOC_TYPES = ("UC", "CRS", "SYS", "SRS", "SWDD")


def _parse_coverage_pairs(pairs: tuple[str, ...]) -> list[tuple[str, str]]:
    parsed = []
    for pair in pairs:
        if ":" not in pair:
            raise click.BadParameter(
                f"invalid pair '{pair}', expected PARENT:CHILD format.",
                param_hint="--coverage-pair",
            )
        parent, child = pair.split(":", 1)
        parsed.append((parent.strip(), child.strip()))
    return parsed


def _collect_junit_paths(junit_files: tuple[Path, ...] = (),
                         junit_dirs: tuple[Path, ...] = ()) -> list[Path]:
    """Collect JUnit XML files from explicit files and directories."""
    collected: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        resolved = str(path.resolve())
        if resolved in seen:
            return
        seen.add(resolved)
        collected.append(path)

    for junit_file in junit_files:
        if not junit_file.exists():
            raise click.ClickException(f"JUnit file '{junit_file}' not found.")
        if not junit_file.is_file():
            raise click.ClickException(f"JUnit path '{junit_file}' is not a file.")
        _add(junit_file)

    for junit_dir in junit_dirs:
        if not junit_dir.exists():
            continue
        if not junit_dir.is_dir():
            raise click.ClickException(f"JUnit path '{junit_dir}' is not a directory.")
        for xml_path in sorted(junit_dir.rglob("*.xml")):
            if xml_path.is_file():
                _add(xml_path)

    return collected


def _run_acceptance_gate(core, junit_paths: list[Path], coverage_pairs: tuple[str, ...]) -> dict:
    """Execute the CI acceptance gate using the provided JUnit evidence."""
    if junit_paths:
        core.inject_junit_results(junit_paths)

    traceability = core.validate()
    adapter_result = core._adapter.validate_traceability()
    required = adapter_result.get("required", {})
    pairs = coverage_pairs or DEFAULT_ACCEPTANCE_COVERAGE_PAIRS
    coverage = core.check_coverage(_parse_coverage_pairs(pairs))
    passed = (
        traceability.get("valid", True)
        and coverage.get("passed", True)
        and required.get("passed", True)
    )
    return {
        "passed": passed,
        "traceability": traceability,
        "required": required,
        "coverage": coverage,
        "junit_files": [str(path) for path in junit_paths],
    }


def _print_acceptance_gate_result(result: dict) -> None:
    click.echo(json.dumps(result, default=str))

    traceability = result.get("traceability", {})
    coverage = result.get("coverage", {})
    required = result.get("required", {})

    if not required.get("passed", True):
        for f in required.get("failures", []):
            click.echo(
                f"FAIL [required] {f['id']}: {f['issue']}",
                err=True,
            )
    if not traceability.get("valid", True):
        for issue in traceability.get("issues", []):
            affected = issue.get("items", [])
            click.echo(
                f"ORPHAN [{issue.get('type', 'issue')}]: {len(affected)} item(s): "
                + ", ".join(affected[:5])
                + ("..." if len(affected) > 5 else ""),
                err=True,
            )
    for row in coverage.get("results", []):
        symbol = "OK" if row.get("passed") else "FAIL"
        click.echo(
            f"{symbol} {row['parent_type']}->{row['child_type']}: "
            f"{row['covered']}/{row['total']} covered",
            err=True,
        )
    if not result.get("passed", False):
        click.echo("FAIL DHF acceptance gate failed.", err=True)
        sys.exit(1)
    click.echo("OK DHF acceptance gate passed.", err=True)


def _summarize_import_result(result: dict) -> dict:
    recorded = result.get("recorded", [])
    skipped = result.get("skipped", 0)
    items_updated = sorted({uid for r in recorded for uid in r.get("links", [])})
    failed_tcs = [r["tc_id"] for r in recorded if r.get("testing_status") == "FAIL"]
    return {
        "imported": len(recorded),
        "skipped": skipped,
        "items_updated": items_updated,
        "failed_tcs": failed_tcs,
    }


def _import_results_file(adapter, path: Path, tester: str, run_id: str,
                         run_url: str, commit: str) -> dict:
    if not hasattr(adapter, "import_results_from_file"):
        raise click.ClickException("Configured DHF adapter does not support test result import.")
    result = adapter.import_results_from_file(
        xml_path=path,
        tester=tester,
        run_id=run_id,
        run_url=run_url,
        commit_sha=commit,
    )
    summary = _summarize_import_result(result)
    summary["path"] = str(path)
    return summary


def _run_command(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(args, cwd=cwd, text=True, check=False)
    if check and proc.returncode != 0:
        raise click.ClickException(f"command failed ({proc.returncode}): {' '.join(args)}")
    return proc


def _run_git(repo_root: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout).strip()
        raise click.ClickException(message or f"git {' '.join(args)} failed")
    return proc.stdout


def _git_has_changes(repo_root: Path) -> bool:
    return bool(_run_git(repo_root, ["status", "--porcelain"]).strip())


def _run_pytest_junit(test_paths: tuple[str, ...], junit_dir: Path) -> list[Path]:
    junit_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for raw_path in test_paths:
        path = Path(raw_path)
        name = path.name or path.as_posix().replace("/", "-")
        xml_path = junit_dir / f"{name.replace('/', '-')}.xml"
        _run_command(["pytest", raw_path, "-v", f"--junitxml={xml_path}"])
        generated.append(xml_path)
    return generated


def _run_compliance_checks(core, governance_dir: Path, standards: tuple[str, ...]) -> list[dict]:
    reports = []
    for standard in standards:
        report = core.check_compliance(standard, governance_dir=governance_dir, persist=False)
        if report is None:
            raise click.ClickException(f"Policy group '{standard}' not found.")
        failed = report["total_policies"] - report["passed_policies"]
        reports.append({
            "standard": standard,
            "score": report["score"],
            "passed_policies": report["passed_policies"],
            "total_policies": report["total_policies"],
            "failed_policies": failed,
        })
    return reports


def _summarize_junit_file(path: Path) -> dict:
    from dhf_util.junit_parser import parse_junit_xml

    results = parse_junit_xml(path)
    recorded = [
        {
            "tc_id": r.id,
            "testing_status": r.testing_status,
            "links": r.links or [],
        }
        for r in results
        if r.testing_status != "SKIP"
    ]
    skipped = sum(1 for r in results if r.testing_status == "SKIP")
    return {
        "path": str(path),
        "imported": len(recorded),
        "skipped": skipped,
        "items_updated": sorted({uid for r in recorded for uid in r["links"]}),
        "failed_tcs": [r["tc_id"] for r in recorded if r["testing_status"] == "FAIL"],
    }


def _build_traceability_report_payload(core, doc_types: tuple[str, ...],
                                       junit_paths: tuple[str, ...] = ()) -> dict:
    if junit_paths:
        core.inject_junit_results([Path(p) for p in junit_paths])

    matrix = core.build_traceability_matrix(list(doc_types))

    columns: list[str] = matrix["columns"]
    for row in matrix["rows"]:
        level_statuses: dict[str, str] = {}
        for col in columns:
            item_id = row.get(col)
            if not item_id:
                continue
            prefix = item_id.split("-")[0] + "-"
            cfg = core.config.get_type_by_prefix(prefix) if core.config else None
            if not cfg or not cfg.has_verification:
                continue
            item = core.get_item(item_id)
            vs = item.get("verification_status") if item else None
            if vs:
                level_statuses[col] = vs
        row["level_statuses"] = level_statuses
        for col in reversed(columns):
            if col in level_statuses:
                row["verification_status"] = level_statuses[col]
                break

    coverage: dict[str, list[dict]] = {}
    seen_ids: set[str] = set()
    for col in columns:
        for row in matrix["rows"]:
            item_id = row.get(col)
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            prefix = item_id.split("-")[0] + "-"
            cfg = core.config.get_type_by_prefix(prefix) if core.config else None
            if not cfg or not cfg.has_verification:
                continue
            item = core.get_item(item_id)
            if not item:
                continue
            test_cases = item.get("test_cases") or []
            coverage.setdefault(item_id.split("-")[0], []).append({
                "id": item_id,
                "title": item.get("title", ""),
                "status": item.get("verification_status", "not_verified"),
                "tests": test_cases,
            })

    for level in coverage:
        coverage[level].sort(key=lambda x: x["id"])

    matrix["coverage"] = coverage
    matrix["test_results"] = core.get_all_test_results()
    return matrix


def _write_traceability_report(core, doc_types: tuple[str, ...], output: Path,
                               junit_paths: tuple[str, ...] = ()) -> dict:
    from compliantflow.report_generator import generate_traceability_pdf

    matrix = _build_traceability_report_payload(core, doc_types, junit_paths)
    output.parent.mkdir(parents=True, exist_ok=True)
    generate_traceability_pdf(matrix, output)
    return {"path": str(output), "rows": len(matrix["rows"])}


def _available_doc_types(adapter) -> list[str]:
    if hasattr(adapter, "get_available_doc_types"):
        return sorted(adapter.get_available_doc_types())
    doc_specs = getattr(adapter, "_doc_specs", None)
    if isinstance(doc_specs, dict):
        return sorted(doc_specs.keys())
    raise click.ClickException("Configured DHF adapter does not expose available document types.")


def _generate_specification_artifacts(adapter, out_dir: Path,
                                      doc_types: tuple[str, ...]) -> list[dict]:
    if not hasattr(adapter, "export_pdf"):
        raise click.ClickException("Configured DHF adapter does not support PDF export.")
    spec_dir = out_dir / "specifications"
    spec_dir.mkdir(parents=True, exist_ok=True)
    generated = []
    for doc_type in doc_types:
        result = adapter.export_pdf(doc_type)
        pdf_path = Path(result["pdf_path"])
        destination = spec_dir / pdf_path.name
        if pdf_path.resolve() != destination.resolve():
            shutil.copy2(pdf_path, destination)
        generated.append({
            "doc_type": doc_type,
            "path": str(destination),
            "source": str(pdf_path),
            "version": result.get("version"),
        })
    return generated


def _run_artifact_generation(
    adapter,
    core,
    dhf_path: Path,
    out_dir: Path,
    doc_types: tuple[str, ...],
    traceability_types: tuple[str, ...],
    junit_paths: list[Path],
    skip_plans: bool,
) -> dict:
    selected_doc_types = doc_types or tuple(_available_doc_types(adapter))
    selected_traceability = traceability_types or DEFAULT_TRACEABILITY_DOC_TYPES

    out_dir.mkdir(parents=True, exist_ok=True)
    specifications = _generate_specification_artifacts(adapter, out_dir, selected_doc_types)
    plans = [] if skip_plans else _generate_plan_artifacts(dhf_path, out_dir)
    traceability = _write_traceability_report(
        core,
        selected_traceability,
        out_dir / "traceability" / "Requirements_Traceability_Report.pdf",
        [str(path) for path in junit_paths],
    )
    return {
        "out_dir": str(out_dir),
        "specifications": specifications,
        "plans": plans,
        "traceability": traceability,
        "junit_files": [str(path) for path in junit_paths],
    }


def _resolve_dhf_repo_paths(ctx: click.Context, dhf_repo: Path | None) -> tuple[Path, Path]:
    """Resolve a DHF repository root and DHF root directory for workflow commands."""
    if dhf_repo is not None:
        repo_root = dhf_repo.resolve()
        dhf_root = repo_root / "DHF"
        if repo_root.name == "DHF":
            dhf_root = repo_root
            repo_root = repo_root.parent
        return repo_root, dhf_root

    dhf_root = Path(ctx.obj["dhf"]).resolve()
    return dhf_root.parent, dhf_root


def _github_env(token: str | None = None) -> dict[str, str]:
    """Return a subprocess env with GitHub token variables populated when available."""
    env = os.environ.copy()
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token
    return env


def _load_issue_comments(
    comments_path: Path | None,
    *,
    source_repo: str | None,
    issue_number: int | None,
    source_token: str | None,
) -> list[dict]:
    if comments_path is not None:
        try:
            comments = json.loads(comments_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"invalid comments JSON at {comments_path}") from exc
        if not isinstance(comments, list):
            raise click.ClickException(f"expected a JSON array in {comments_path}")
        return comments
    if not source_repo or issue_number is None:
        return []

    command = [
        "gh",
        "api",
        f"repos/{source_repo}/issues/{issue_number}/comments?per_page=100",
    ]
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=_github_env(source_token),
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout).strip()
        raise click.ClickException(message or f"failed to fetch comments for issue {issue_number}")
    try:
        comments = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise click.ClickException("gh api returned invalid JSON for issue comments") from exc
    if not isinstance(comments, list):
        raise click.ClickException("gh api returned unexpected issue comments payload")
    return comments


def _make_adapter_for_dhf_root(dhf_root: Path):
    try:
        from dhf_util.local_adapter import LocalDHFAdapter
    except ImportError:
        raise click.ClickException(
            "LocalDHFAdapter not found. Add your DHF system to PYTHONPATH before running the CLI."
        )
    return LocalDHFAdapter(dhf_root, auto_commit=False)


def _generate_plan_artifacts(dhf_path: Path, out_dir: Path) -> list[dict]:
    plans_dir = dhf_path / "documents" / "plans"
    if not plans_dir.is_dir():
        return []
    try:
        import markdown as _markdown
        from weasyprint import HTML
    except ImportError as exc:
        raise click.ClickException(
            "markdown and weasyprint are required to generate plan PDF artifacts."
        ) from exc

    css_candidates = [
        dhf_path / "documents" / "specifications" / "templates" / "styles" / "default.css",
        dhf_path / "documents" / "specs" / "styles" / "default.css",
    ]
    css = ""
    for css_path in css_candidates:
        if css_path.exists():
            css = f"<style>{css_path.read_text(encoding='utf-8')}</style>"
            break

    output_dir = out_dir / "plans"
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []
    for plan in sorted(plans_dir.glob("*.md")):
        html = _markdown.markdown(
            plan.read_text(encoding="utf-8"),
            extensions=["tables", "fenced_code", "toc"],
        )
        output = output_dir / f"{plan.stem}.pdf"
        HTML(
            string=f"<!doctype html><html><head>{css}</head><body>{html}</body></html>",
            base_url=str(plan.parent),
        ).write_pdf(str(output))
        generated.append({"source": str(plan), "path": str(output)})
    return generated


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="compliantflow")
@click.option(
    "--dhf",
    default=None,
    metavar="PATH",
    help="Path to the DHF directory. Overrides COMPLIANTFLOW_DHF env var.",
)
@click.option(
    "--project",
    "projects",
    multiple=True,
    metavar="SLUG:PATH",
    help=(
        "Add a project as slug:path. Repeat for multiple projects. "
        "When provided, --dhf is ignored and a MultiDHFAdapter is used. "
        "Example: --project device-a:/repo/a/DHF --project device-b:/repo/b/DHF"
    ),
)
@click.pass_context
def main(ctx: click.Context, dhf: str | None, projects: tuple) -> None:
    """CompliantFlow CLI — analysis and traceability for CI/CD pipelines."""
    ctx.ensure_object(dict)
    if projects:
        parsed: dict = {}
        for entry in projects:
            if ":" not in entry:
                raise click.BadParameter(
                    f"--project must be in slug:path format, got: {entry!r}",
                    param_hint="--project",
                )
            slug, path = entry.split(":", 1)
            parsed[slug.strip()] = Path(path.strip())
        ctx.obj["projects"] = parsed
    ctx.obj["dhf"] = _resolve_dhf(dhf)


# ---------------------------------------------------------------------------
# DHF facade
# ---------------------------------------------------------------------------

@main.group("dhf")
def dhf() -> None:
    """DHF automation facade commands."""


@dhf.group("item")
def dhf_item() -> None:
    """Read and mutate DHF items through the configured adapter."""


@dhf_item.command("list")
@click.option("--type", "doc_type", default=None, metavar="CODE",
              help="Filter by document type code, e.g. CR or SRS.")
@click.pass_context
def dhf_item_list(ctx: click.Context, doc_type: str | None) -> None:
    adapter = _make_adapter(ctx)
    for item in adapter.list_items(doc_type):
        click.echo(json.dumps(item, default=str))


@dhf_item.command("get")
@click.argument("item_id")
@click.pass_context
def dhf_item_get(ctx: click.Context, item_id: str) -> None:
    adapter = _make_adapter(ctx)
    item = adapter.get_item(item_id)
    if item is None:
        raise click.ClickException(f"Item '{item_id}' not found.")
    click.echo(json.dumps(item, default=str))


@dhf_item.command("create")
@click.option("--type", "doc_type", required=True, metavar="CODE",
              help="Document type code, e.g. CR or SRS.")
@click.option("--data", required=True, metavar="JSON",
              help="Item fields as a JSON object.")
@click.option("--author", default="compliantflow", show_default=True)
@click.option("--cr", "cr_id", default=None, metavar="CR_ID")
@click.pass_context
def dhf_item_create(
    ctx: click.Context,
    doc_type: str,
    data: str,
    author: str,
    cr_id: str | None,
) -> None:
    adapter = _make_adapter(ctx)
    payload = _parse_json_object(data)
    payload["type"] = doc_type
    try:
        result = adapter.create_item(payload, author=author, cr_id=cr_id)
    except TypeError:
        result = adapter.create_item(payload, author=author)
    click.echo(json.dumps(result, default=str))


@dhf_item.command("update")
@click.argument("item_id")
@click.option("--data", required=True, metavar="JSON",
              help="Fields to merge into the existing item.")
@click.option("--author", default="compliantflow", show_default=True)
@click.option("--cr", "cr_id", default=None, metavar="CR_ID")
@click.pass_context
def dhf_item_update(
    ctx: click.Context,
    item_id: str,
    data: str,
    author: str,
    cr_id: str | None,
) -> None:
    adapter = _make_adapter(ctx)
    payload = _parse_json_object(data)
    try:
        result = adapter.update_item(item_id, payload, author=author, cr_id=cr_id)
    except TypeError:
        result = adapter.update_item(item_id, payload, author=author)
    if result is None:
        raise click.ClickException(f"Item '{item_id}' not found.")
    click.echo(json.dumps(result, default=str))


@dhf_item.command("delete")
@click.argument("item_id")
@click.option("--author", default="compliantflow", show_default=True)
@click.pass_context
def dhf_item_delete(ctx: click.Context, item_id: str, author: str) -> None:
    adapter = _make_adapter(ctx)
    if not adapter.delete_item(item_id, author=author):
        raise click.ClickException(f"Item '{item_id}' not found or could not be deleted.")
    click.echo(json.dumps({"deleted": item_id}))


@dhf_item.command("transition")
@click.argument("item_id")
@click.argument("to_state")
@click.option("--by", "performed_by", default="compliantflow", show_default=True)
@click.pass_context
def dhf_item_transition(
    ctx: click.Context,
    item_id: str,
    to_state: str,
    performed_by: str,
) -> None:
    adapter = _make_adapter(ctx)
    result = adapter.execute_transition(item_id, to_state, performed_by=performed_by)
    click.echo(json.dumps(result, default=str))


@dhf.group("context")
def dhf_context() -> None:
    """Generate implementation context packages for product automation."""


@dhf_context.command("implementation")
@click.option("--cr", "cr_id", required=True, metavar="CR_ID")
@click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path), required=True)
@click.pass_context
def dhf_context_implementation(ctx: click.Context, cr_id: str, out_dir: Path) -> None:
    """Write the approved implementation context for a CR to OUT_DIR."""
    adapter = _make_adapter(ctx)
    dhf_path: Path = ctx.obj["dhf"]
    cr = adapter.get_item(cr_id)
    if cr is None:
        raise click.ClickException(f"CR '{cr_id}' not found.")
    spec = _get_document_with_legacy_fallback(adapter, dhf_path, f"{cr_id}-Spec") or ""

    out_dir.mkdir(parents=True, exist_ok=True)
    cr_path = out_dir / f"{cr_id}.json"
    spec_path = out_dir / f"{cr_id}-Spec.md"
    context_path = out_dir / "implementation-context.json"
    cr_path.write_text(json.dumps(cr, indent=2, default=str) + "\n", encoding="utf-8")
    spec_path.write_text(spec, encoding="utf-8")
    context_path.write_text(
        json.dumps(
            {
                "cr": str(cr_path),
                "implementation_spec": str(spec_path),
                "dhf_references": [cr_id, f"{cr_id}-Spec"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    click.echo(json.dumps({"cr": str(cr_path), "implementation_spec": str(spec_path), "context": str(context_path)}))


# ---------------------------------------------------------------------------
# CI facade
# ---------------------------------------------------------------------------

@main.group("ci")
def ci() -> None:
    """CI-facing facade commands for DHF gates, evidence, and artifacts."""


@ci.group("gate")
def ci_gate() -> None:
    """Acceptance gate commands."""


@ci.group("run")
def ci_run() -> None:
    """High-level CI orchestration commands for product repositories."""


@ci_gate.command("acceptance")
@click.option("--junit", "junit_paths", multiple=True, type=click.Path(exists=True, dir_okay=False),
              help="JUnit XML file(s) to include as in-memory verification evidence.")
@click.option("--coverage-pair", "coverage_pairs", multiple=True, metavar="PARENT:CHILD",
              help="Coverage pair to check. Repeat for multiple pairs.")
@click.pass_context
def ci_gate_acceptance(ctx: click.Context, junit_paths: tuple,
                       coverage_pairs: tuple) -> None:
    """Run the DHF acceptance gate for CI pipelines."""
    core = _make_core(ctx)
    result = _run_acceptance_gate(core, [Path(p) for p in junit_paths], coverage_pairs)
    _print_acceptance_gate_result(result)


@ci_run.command("acceptance")
@click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="JUnit XML file(s) to include in the acceptance gate.")
@click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path),
              help="Directory containing JUnit XML evidence. All *.xml files are included recursively.")
@click.option("--coverage-pair", "coverage_pairs", multiple=True, metavar="PARENT:CHILD",
              help="Coverage pair to check. Repeat for multiple pairs.")
@click.pass_context
def ci_run_acceptance(ctx: click.Context, junit_files: tuple[Path, ...],
                      junit_dirs: tuple[Path, ...], coverage_pairs: tuple) -> None:
    """Run the high-level CI acceptance gate for product workflows."""
    core = _make_core(ctx)
    junit_paths = _collect_junit_paths(junit_files, junit_dirs)
    result = _run_acceptance_gate(core, junit_paths, coverage_pairs)
    _print_acceptance_gate_result(result)


@ci.group("evidence")
def ci_evidence() -> None:
    """CI evidence ingestion commands."""


@ci_evidence.command("import")
@click.argument("paths", nargs=-1, required=True,
                type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--format", "fmt", default="junit", show_default=True,
              type=click.Choice(["junit"], case_sensitive=False),
              help="Test result format.")
@click.option("--tester", default="", help="Name of the tester or CI agent.")
@click.option("--run-id", default="", help="CI run ID.")
@click.option("--run-url", default="", help="URL to the CI run.")
@click.option("--commit", default="", help="Git commit SHA.")
@click.pass_context
def ci_evidence_import(ctx: click.Context, paths: tuple[Path, ...], fmt: str,
                       tester: str, run_id: str, run_url: str, commit: str) -> None:
    """Import one or more test evidence files into the DHF."""
    adapter = _make_adapter(ctx)
    files = [
        _import_results_file(adapter, path, tester, run_id, run_url, commit)
        for path in paths
    ]
    summary = {
        "format": fmt,
        "files": files,
        "imported": sum(f["imported"] for f in files),
        "skipped": sum(f["skipped"] for f in files),
        "items_updated": sorted({uid for f in files for uid in f["items_updated"]}),
        "failed_tcs": [tc for f in files for tc in f["failed_tcs"]],
    }
    click.echo(json.dumps(summary, default=str))
    click.echo(
        f"OK Imported {summary['imported']} result(s), skipped {summary['skipped']}, "
        f"updated {len(summary['items_updated'])} item(s).",
        err=True,
    )
    if summary["failed_tcs"]:
        click.echo(f"FAIL Failing TCs: {summary['failed_tcs']}", err=True)


@ci_evidence.command("record")
@click.option("--test-path", "test_paths", multiple=True, default=("tests/sys", "tests/crs"),
              help="Pytest path to run. Repeat for multiple paths.")
@click.option("--junit-dir", type=click.Path(file_okay=False, path_type=Path), default=Path("test-results"),
              show_default=True, help="Directory for generated JUnit XML files.")
@click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path), default=Path("evidence"),
              show_default=True, help="Directory for generated evidence summary artifacts.")
@click.option("--governance-dir", type=click.Path(file_okay=False, path_type=Path), required=True,
              help="Governance directory containing policy YAML files.")
@click.option("--standard", "standards", multiple=True, default=("IEC_62304", "IEC_82304_1"),
              help="Compliance standard to evaluate. Repeat for multiple standards.")
@click.option("--tester", default="GitHub Actions", show_default=True,
              help="Tester recorded in the evidence summary.")
@click.option("--run-id", default="", help="CI run ID.")
@click.option("--run-url", default="", help="CI run URL.")
@click.option("--commit", "commit_sha", default="", help="Git commit SHA.")
@click.option("--continue-on-compliance-failure", is_flag=True, default=False,
              help="Generate evidence artifacts and exit 0 even if a compliance check fails.")
@click.pass_context
def ci_evidence_record(
    ctx: click.Context,
    test_paths: tuple[str, ...],
    junit_dir: Path,
    out_dir: Path,
    governance_dir: Path,
    standards: tuple[str, ...],
    tester: str,
    run_id: str,
    run_url: str,
    commit_sha: str,
    continue_on_compliance_failure: bool,
) -> None:
    """Run tests and write CI evidence summaries without mutating the DHF."""
    core = _make_core(ctx)

    junit_paths = _run_pytest_junit(test_paths, junit_dir)
    files = [_summarize_junit_file(path) for path in junit_paths]

    compliance = _run_compliance_checks(core, governance_dir, standards)
    failed_standards = [item["standard"] for item in compliance if item["failed_policies"]]

    summary = {
        "dhf_root": str(ctx.obj["dhf"]),
        "tester": tester,
        "run_id": run_id,
        "run_url": run_url,
        "commit_sha": commit_sha,
        "test_paths": list(test_paths),
        "junit_files": [str(path) for path in junit_paths],
        "imported": sum(f["imported"] for f in files),
        "skipped": sum(f["skipped"] for f in files),
        "items_updated": sorted({uid for f in files for uid in f["items_updated"]}),
        "failed_tcs": [tc for f in files for tc in f["failed_tcs"]],
        "compliance": compliance,
        "failed_standards": failed_standards,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "evidence-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    click.echo(json.dumps(summary, default=str))
    click.echo(f"OK Evidence summary written to {summary_path}.", err=True)

    if failed_standards and not continue_on_compliance_failure:
        raise click.ClickException(f"Compliance failed for: {', '.join(failed_standards)}")



@ci_evidence.command("bundle")
@click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path), required=True,
              help="Output directory for evidence artifacts.")
@click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="JUnit XML file(s) to include.")
@click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path),
              help="Directory containing JUnit XML files (*.xml discovered recursively).")
@click.option("--coverage-pair", "coverage_pairs", multiple=True, metavar="PARENT:CHILD",
              help="Coverage pair to check. Repeat for multiple pairs.")
@click.option("--traceability-type", "traceability_types", multiple=True, metavar="CODE",
              help="Traceability matrix type. Defaults to UC CRS SYS SRS SWDD.")
@click.option("--compliance-standard", "compliance_standards", multiple=True, metavar="CODE",
              help="Compliance standard to check. Repeat for multiple standards (e.g. IEC_62304).")
@click.option("--governance-dir", type=click.Path(file_okay=False, path_type=Path),
              help="Governance directory for compliance checks.")
@click.option("--run-id", "run_id", default="", help="CI run identifier.")
@click.option("--run-url", "run_url", default="", help="CI run URL for traceability.")
@click.option("--commit", "commit_sha", default="", help="Git commit SHA.")
@click.option("--continue-on-gate-failure", is_flag=True, default=False,
              help="Continue generating artifacts even if the acceptance gate fails. "
                   "Use only for debugging; do not set as a CI default.")
@click.pass_context
def ci_evidence_bundle(
    ctx: click.Context,
    out_dir: Path,
    junit_files: tuple[Path, ...],
    junit_dirs: tuple[Path, ...],
    coverage_pairs: tuple[str, ...],
    traceability_types: tuple[str, ...],
    compliance_standards: tuple[str, ...],
    governance_dir: Path | None,
    run_id: str,
    run_url: str,
    commit_sha: str,
    continue_on_gate_failure: bool,
) -> None:
    """Produce a read-only CI evidence bundle: gate result, DHF PDF artifacts, and manifest.

    Does NOT write to the DHF. Does NOT call ci evidence import. Does NOT persist
    compliance runs. The bundle is a self-contained audit package that WebTPS or
    any other product repository can upload as a CI artifact.

    The bundle contains:
    - acceptance gate result (pass/fail, traceability, coverage)
    - DHF specification PDFs and traceability report
    - plan PDFs
    - evidence-summary.json
    - evidence-manifest.json (with SHA256 checksums)
    """
    import hashlib
    from datetime import datetime, timezone

    adapter = _make_adapter(ctx)
    core = _make_core(ctx)
    dhf_path: Path = ctx.obj["dhf"]

    # ── Collect JUnit evidence ──
    junit_paths = _collect_junit_paths(junit_files, junit_dirs)

    # ── Acceptance gate ──
    gate_result = _run_acceptance_gate(core, junit_paths, coverage_pairs)
    gate_passed = gate_result.get("passed", False)

    # ── DHF artifacts ──
    out_dir.mkdir(parents=True, exist_ok=True)
    doc_types = traceability_types if traceability_types else ()
    artifacts_result = _run_artifact_generation(
        adapter,
        core,
        dhf_path,
        out_dir,
        doc_types,
        traceability_types,
        junit_paths,
        skip_plans=False,
    )

    # ── Evidence summary ──
    junit_summaries = [_summarize_junit_file(p) for p in junit_paths]
    summary = {
        "dhf_root": str(dhf_path),
        "run_id": run_id,
        "run_url": run_url,
        "commit_sha": commit_sha,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_passed": gate_passed,
        "gate": gate_result,
        "artifacts": artifacts_result,
        "junit_sources": [
            {"path": s["path"], "imported": s["imported"], "skipped": s["skipped"],
             "failed_tcs": s["failed_tcs"]}
            for s in junit_summaries
        ],
    }
    summary_path = out_dir / "evidence-summary.json"
    summary_str = json.dumps(summary, indent=2, default=str)
    summary_path.write_text(summary_str + "\n", encoding="utf-8")

    # ── Compliance reports ──
    compliance_dir = out_dir / "compliance"
    compliance_dir.mkdir(parents=True, exist_ok=True)
    if compliance_standards and governance_dir:
        for standard in compliance_standards:
            output_pdf = compliance_dir / f"{standard}_Compliance_Report.pdf"
            try:
                core.report_compliance(standard, str(governance_dir), str(output_pdf))
            except Exception:
                click.echo(f"WARN: Compliance report for {standard} could not be generated.", err=True)

    # ── Manifest ──
    manifest_files: list[dict] = []
    for candidate in sorted(out_dir.rglob("*")):
        if not candidate.is_file() or candidate.name.startswith("."):
            continue
        sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
        manifest_files.append({
            "path": str(candidate.relative_to(out_dir)),
            "size": candidate.stat().st_size,
            "sha256": sha,
        })

    manifest = {
        "run_id": run_id,
        "run_url": run_url,
        "commit_sha": commit_sha,
        "dhf_root": str(dhf_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_passed": gate_passed,
        "acceptance_result": "PASS" if gate_passed else "FAIL",
        "files": manifest_files,
    }
    manifest_path = out_dir / "evidence-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")

    # ── Reporting ──
    click.echo(json.dumps(manifest, default=str))
    click.echo(f"OK Bundle written to {out_dir} (gate {'PASS' if gate_passed else 'FAIL'}).", err=True)

    if not gate_passed and not continue_on_gate_failure:
        raise click.ClickException("DHF acceptance gate failed.")


@ci.group("artifacts")
def ci_artifacts() -> None:
    """CI artifact generation commands."""


@ci_artifacts.command("generate")
@click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path), required=True)
@click.option("--doc-type", "doc_types", multiple=True, metavar="CODE",
              help="Specification document type to export. Defaults to all configured types.")
@click.option("--traceability-type", "traceability_types", multiple=True, metavar="CODE",
              help="Traceability matrix type. Defaults to UC CRS SYS SRS SWDD.")
@click.option("--junit", "junit_paths", multiple=True, type=click.Path(exists=True, dir_okay=False),
              help="JUnit XML file(s) to include in the traceability report.")
@click.option("--skip-plans", is_flag=True, default=False,
              help="Skip plan PDF generation.")
@click.pass_context
def ci_artifacts_generate(ctx: click.Context, out_dir: Path, doc_types: tuple,
                          traceability_types: tuple, junit_paths: tuple,
                          skip_plans: bool) -> None:
    """Generate CI-ready DHF PDF artifacts."""
    adapter = _make_adapter(ctx)
    core = _make_core(ctx)
    dhf_path: Path = ctx.obj["dhf"]
    result = _run_artifact_generation(
        adapter,
        core,
        dhf_path,
        out_dir,
        doc_types,
        traceability_types,
        [Path(p) for p in junit_paths],
        skip_plans,
    )
    click.echo(json.dumps(result, default=str))
    click.echo(
        f"OK Generated {len(result['specifications'])} specification(s), "
        f"{len(result['plans'])} plan(s), "
        f"traceability report at {result['traceability']['path']}.",
        err=True,
    )


@ci_run.command("artifacts")
@click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path), required=True)
@click.option("--doc-type", "doc_types", multiple=True, metavar="CODE",
              help="Specification document type to export. Defaults to all configured types.")
@click.option("--traceability-type", "traceability_types", multiple=True, metavar="CODE",
              help="Traceability matrix type. Defaults to UC CRS SYS SRS SWDD.")
@click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="JUnit XML file(s) to include in the artifact traceability report.")
@click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path),
              help="Directory containing JUnit XML evidence. All *.xml files are included recursively.")
@click.option("--skip-plans", is_flag=True, default=False,
              help="Skip plan PDF generation.")
@click.pass_context
def ci_run_artifacts(ctx: click.Context, out_dir: Path, doc_types: tuple,
                     traceability_types: tuple, junit_files: tuple[Path, ...],
                     junit_dirs: tuple[Path, ...], skip_plans: bool) -> None:
    """Generate CI-ready DHF artifacts for product workflows."""
    adapter = _make_adapter(ctx)
    core = _make_core(ctx)
    dhf_path: Path = ctx.obj["dhf"]
    junit_paths = _collect_junit_paths(junit_files, junit_dirs)
    result = _run_artifact_generation(
        adapter,
        core,
        dhf_path,
        out_dir,
        doc_types,
        traceability_types,
        junit_paths,
        skip_plans,
    )
    click.echo(json.dumps(result, default=str))
    click.echo(
        f"OK Generated {len(result['specifications'])} specification(s), "
        f"{len(result['plans'])} plan(s), "
        f"traceability report at {result['traceability']['path']}.",
        err=True,
    )


# ---------------------------------------------------------------------------
# ci dhf-validate — single-command DHF validation gate
# ---------------------------------------------------------------------------

@ci.command("dhf-validate")
@click.option("--dhf", "dhf_path", type=click.Path(file_okay=False, path_type=Path), required=True,
              help="Path to DHF directory.")
@click.option("--governance-dir", type=click.Path(file_okay=False, path_type=Path), default=Path("governance"),
              help="Path to governance directory.")
@click.option("--run-schema/--no-run-schema", default=True, show_default=True,
              help="Run schema validation.")
@click.option("--run-traceability/--no-run-traceability", default=True, show_default=True,
              help="Run traceability validation.")
@click.option("--run-compliance/--no-run-compliance", default=False, show_default=True,
              help="Run compliance validation.")
@click.option("--coverage-pair", "coverage_pairs", multiple=True, metavar="PARENT:CHILD",
              help="Coverage pair to check. Repeat for multiple pairs.")
@click.option("--compliance-standard", "compliance_standards", multiple=True, metavar="CODE",
              help="Compliance standard to check. Repeat for multiple.")
@click.option("--fail-on-uncovered", is_flag=True, default=False,
              help="Exit 1 on uncovered traceability items.")
@click.pass_context
def ci_dhf_validate(
    ctx: click.Context,
    dhf_path: Path,
    governance_dir: Path,
    run_schema: bool,
    run_traceability: bool,
    run_compliance: bool,
    coverage_pairs: tuple[str, ...],
    compliance_standards: tuple[str, ...],
    fail_on_uncovered: bool,
) -> None:
    """Single-command DHF validation gate for CI pipelines.

    Replaces reusable-workflow YAML with an explicit Python command.
    Each validation phase is independently toggleable.
    Coverage pairs and compliance standards are passed as CLI flags.
    """
    from dhf_util.local_adapter import LocalDHFAdapter
    from compliantflow.core import CompliantFlowCore

    adapter = LocalDHFAdapter(dhf_path)
    core = CompliantFlowCore(adapter)

    failed = False

    # ── Schema ──
    if run_schema:
        result = adapter.validate_schema()
        if not result.get("valid", True):
            failed = True
            click.echo("FAIL [schema]: validation errors found", err=True)
            for err in result.get("errors", []):
                click.echo(f"  ✗ {err}", err=True)
        else:
            click.echo(f"PASS [schema]: {result.get('item_count', 0)} items valid", err=True)

    # ── Traceability ──
    if run_traceability:
        trace_result = adapter.validate_traceability()
        required = trace_result.get("required", {})
        if not required.get("passed", True):
            failed = True
            for f in required.get("failures", []):
                click.echo(f"FAIL [required] {f['id']}: {f['issue']}", err=True)
        for c in trace_result.get("coverage", []):
            status = "PASS" if c["passed"] else "FAIL"
            if not c["passed"]:
                failed = fail_on_uncovered
            click.echo(
                f"{status} [coverage] {c['parent_type']}→{c['child_type']}: "
                f"{c['covered']}/{c['total']} covered",
                err=True,
            )
        click.echo(trace_result.get("summary", ""), err=True)

    # ── Coverage gate ──
    if coverage_pairs:
        pairs = [(p.split(":")[0], p.split(":")[1]) for p in coverage_pairs]
        cov_result = core.check_coverage(pairs)
        for row in cov_result.get("results", []):
            status = "PASS" if row.get("passed") else "FAIL"
            if not row.get("passed"):
                failed = True
            click.echo(
                f"{status} [gate] {row['parent_type']}→{row['child_type']}: "
                f"{row['covered']}/{row['total']} covered",
                err=True,
            )

    # ── Compliance ──
    if run_compliance and compliance_standards:
        for standard in compliance_standards:
            try:
                gov = governance_dir.resolve() if governance_dir else Path("governance")
                report = core.check_compliance(standard, str(gov))
                if report is None:
                    failed = True
                    click.echo(f"FAIL [compliance] {standard}: policy group not found", err=True)
                    continue
                score = report.get("score", 0)
                passed_pol = report.get("passed_policies", 0)
                total_pol = report.get("total_policies", 0)
                if score == 100.0:
                    click.echo(f"PASS [compliance] {standard}: {passed_pol}/{total_pol} ({score}%)", err=True)
                else:
                    failed = True
                    click.echo(f"FAIL [compliance] {standard}: {passed_pol}/{total_pol} ({score}%)", err=True)
            except Exception as e:
                failed = True
                click.echo(f"FAIL [compliance] {standard}: {e}", err=True)

    if failed:
        raise click.ClickException("DHF validation failed.")


# ---------------------------------------------------------------------------
# ci test-coverage — product-side requirement→test coverage gate
# ---------------------------------------------------------------------------

@ci.command("test-coverage")
@click.option("--dhf", "dhf_path", type=click.Path(file_okay=False, path_type=Path), required=True,
              help="Path to DHF directory.")
@click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path),
              help="Directory containing JUnit XML evidence. Repeat for multiple dirs.")
@click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="JUnit XML file(s) to include.")
@click.option("--requirement-type", "req_types", multiple=True, metavar="CODE",
              help="Requirement type to check (e.g. SRS, SYS, CRS). Repeat for multiple.")
@click.pass_context
def ci_test_coverage(
    ctx: click.Context,
    dhf_path: Path,
    junit_dirs: tuple[Path, ...],
    junit_files: tuple[Path, ...],
    req_types: tuple[str, ...],
) -> None:
    """Check that every requirement has test coverage from JUnit evidence.

    Scans JUnit XML files for @links tags, then verifies each requirement
    of the given types has at least one linked test.  Exits 1 on coverage
    gaps.

    This is a product-side gate: it answers "do tests cover requirements?"
    It does NOT check the DHF design chain (UC→CRS→SYS etc.) — that is
    the responsibility of ``ci dhf-validate`` in the DHF repository.
    """
    from dhf_util.local_adapter import LocalDHFAdapter
    from dhf_util.junit_parser import parse_junit_xml
    from dhf_util.models.config import ProjectConfig

    # ── Collect JUnit evidence ──
    junit_paths = _collect_junit_paths(junit_files, junit_dirs)
    if not junit_paths:
        click.echo("WARN: No JUnit files found — skipping test-coverage check.", err=True)
        return

    # ── Parse test evidence into requirement-coverage map ──
    covered_reqs: set[str] = set()
    for jp in junit_paths:
        for result in parse_junit_xml(jp):
            if result.testing_status == "PASS" and result.links:
                covered_reqs.update(result.links)

    # ── Load DHF items ──
    adapter = LocalDHFAdapter(dhf_path)
    all_items = adapter.list_items()
    by_id = {it["id"]: it for it in all_items}

    # ── Check coverage per requirement type ──
    failed = False
    default_types = req_types if req_types else ("SRS", "SYS", "CRS")
    for rt in default_types:
        config = adapter._config
        dt = config.get_doc_type(rt)
        if not dt:
            click.echo(f"WARN: Unknown requirement type '{rt}' — skipped.", err=True)
            continue
        prefix = dt.prefix
        req_items = [it for it in all_items if it["id"].startswith(prefix)]
        if not req_items:
            continue
        covered = 0
        uncovered = []
        for ri in req_items:
            if ri["id"] in covered_reqs:
                covered += 1
            else:
                uncovered.append(ri["id"])
        total = len(req_items)
        if covered < total:
            failed = True
            click.echo(f"FAIL [test-coverage] {rt}: {covered}/{total} covered", err=True)
            for uid in uncovered:
                click.echo(f"      ↳ uncovered: {uid}", err=True)
        else:
            click.echo(f"PASS [test-coverage] {rt}: {covered}/{total} covered", err=True)

    if failed:
        raise click.ClickException("Test coverage gaps found.")


# ---------------------------------------------------------------------------
# ci release — release artifact consumption and assembly
# ---------------------------------------------------------------------------

@ci.group("release")
def ci_release() -> None:
    """Release artifact consumption and assembly commands."""


@ci_release.command("consume-artifact")
@click.option("--repo", required=True, metavar="OWNER/REPO",
              help="GitHub repository containing the CI pipeline.")
@click.option("--commit-sha", required=True,
              help="Git commit SHA to find the matching CI run.")
@click.option("--workflow", "workflow_name", default="ci-pipeline.yml",
              help="Workflow file name that produces the artifact.")
@click.option("--artifact-name", default="dhf-release-artifacts", show_default=True,
              help="Name of the artifact to download.")
@click.option("--download-dir", type=click.Path(file_okay=False, path_type=Path), required=True,
              help="Directory to download the artifact into.")
@click.pass_context
def ci_release_consume_artifact(
    ctx: click.Context,
    repo: str,
    commit_sha: str,
    workflow_name: str,
    artifact_name: str,
    download_dir: Path,
) -> None:
    """Download a CI-produced artifact for the given commit.

    Finds the latest successful CI run for ``commit-sha`` that uploaded
    ``artifact-name``, downloads it to ``download-dir``, and exits 0.
    Fails if no matching run or artifact exists.
    """
    import json as _json
    import os as _os
    import subprocess as _subprocess

    env = _os.environ.copy()

    def _gh(*args: str) -> str:
        result = _subprocess.run(
            ["gh"] + list(args),
            capture_output=True, text=True, env=env, timeout=30,
        )
        if result.returncode != 0:
            raise click.ClickException(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    # 1. Find successful runs for this commit
    runs_json = _gh(
        "api", f"repos/{repo}/actions/workflows/{workflow_name}/runs",
        "--jq", f'[.workflow_runs[] | select(.head_sha=="{commit_sha}" and .status=="completed" and .conclusion=="success")] | sort_by(-.id)',
    )
    runs = _json.loads(runs_json)
    if not runs:
        raise click.ClickException(
            f"No successful {workflow_name} run found for commit {commit_sha}."
        )

    # 2. Find the first run that has the required artifact
    for run in runs:
        run_id = run["id"]
        artifacts_json = _gh(
            "api", f"repos/{repo}/actions/runs/{run_id}/artifacts",
            "--jq", f'[.artifacts[] | select(.name=="{artifact_name}")]',
        )
        artifacts = _json.loads(artifacts_json)
        if artifacts:
            artifact_id = artifacts[0]["id"]
            click.echo(f"Found {artifact_name} in run {run_id} (artifact {artifact_id})", err=True)

            # 3. Download artifact
            download_dir.mkdir(parents=True, exist_ok=True)
            _gh(
                "run", "download", str(run_id),
                "--repo", repo,
                "--name", artifact_name,
                "--dir", str(download_dir),
            )
            click.echo(f"Downloaded {artifact_name} to {download_dir}", err=True)
            return

    raise click.ClickException(
        f"No CI run for commit {commit_sha} contains artifact '{artifact_name}'."
    )


@ci_release.command("assemble")
@click.option("--artifact-dir", type=click.Path(file_okay=False, path_type=Path), required=True,
              help="Directory containing downloaded DHF release artifacts.")
@click.option("--wheel", "wheel_paths", multiple=True, type=click.Path(exists=True, path_type=Path),
              help="Wheel file(s) to include in the bundle.")
@click.option("--getting-started", type=click.Path(exists=True, path_type=Path),
              help="GETTING_STARTED.md to include in the bundle.")
@click.option("--version", required=True,
              help="Release version string (e.g., 2.0.42).")
@click.option("--commit-sha", required=True,
              help="Git commit SHA for naming.")
@click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path), required=True,
              help="Output directory for assembled bundles.")
@click.pass_context
def ci_release_assemble(
    ctx: click.Context,
    artifact_dir: Path,
    wheel_paths: tuple[Path, ...],
    getting_started: Path | None,
    version: str,
    commit_sha: str,
    out_dir: Path,
) -> None:
    """Assemble release bundles from downloaded artifacts.

    Produces two zip files in ``out_dir``:
    - ``compliantflow-{version}-{hash}.zip``: wheel + GETTING_STARTED
    - ``DHF-{version}-{hash}.zip``: DHF evidence artifacts
    """
    import zipfile as _zipfile
    import shutil as _shutil

    short_sha = commit_sha[:7]
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── CF bundle: wheel + GETTING_STARTED ──
    cf_name = f"compliantflow-{version}-{short_sha}"
    cf_zip = out_dir / f"{cf_name}.zip"
    with _zipfile.ZipFile(cf_zip, "w", _zipfile.ZIP_DEFLATED) as zf:
        for wp in wheel_paths:
            zf.write(wp, wp.name)
        if getting_started:
            zf.write(getting_started, getting_started.name)
    click.echo(f"CF_ZIP={cf_zip}", err=False)
    click.echo(f"Created {cf_zip}", err=True)

    # ── DHF bundle: evidence artifacts ──
    dhf_name = f"DHF-{version}-{short_sha}"
    dhf_zip = out_dir / f"{dhf_name}.zip"
    with _zipfile.ZipFile(dhf_zip, "w", _zipfile.ZIP_DEFLATED) as zf:
        for fpath in sorted(artifact_dir.rglob("*")):
            if fpath.is_file() and not fpath.name.startswith("."):
                zf.write(fpath, str(fpath.relative_to(artifact_dir)))
    click.echo(f"DHF_ZIP={dhf_zip}", err=False)
    click.echo(f"Created {dhf_zip}", err=True)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@main.command("init")
def init_cmd() -> None:
    """Interactive onboarding: set up the full CompliantFlow infrastructure.

    Walks through collecting project details, then:
    \b
      1. Creates a private DHF repository from the built-in template (optional)
      2. Opens a pull request in the product repo adding the compliance CI gate
      3. Configures LLM API key secrets for AI-assisted checks (optional)

    Requires the 'gh' CLI to be installed and authenticated.
    """
    from compliantflow.init_cmd import run_init
    run_init()


# ---------------------------------------------------------------------------
# review-pr
# ---------------------------------------------------------------------------

@main.command("review-pr")
@click.option("--diff", "diff_file", default=None, metavar="FILE",
              help="Path to a unified diff file. Use '-' to read from stdin.")
@click.option("--pr", "pr_number", default=None, metavar="NUMBER",
              help="GitHub PR number. Fetches diff via 'gh pr diff'.")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Path to governance directory. Defaults to ./governance.")
@click.option("--post-comment", is_flag=True, default=False,
              help="Post the checklist as a GitHub PR comment (requires --pr and gh CLI).")
@click.pass_context
def review_pr(ctx: click.Context, diff_file: str | None, pr_number: str | None,
              governance_dir: str | None, post_comment: bool) -> None:
    """Analyse a PR diff and produce a DHF compliance action checklist.

    Suggestion layer only — no pass/fail exit code. The CI gate remains
    the authoritative compliance enforcer.

    \b
    Example:
      git diff main...HEAD | python -m compliantflow --dhf path/to/DHF review-pr --diff -
      python -m compliantflow --dhf path/to/DHF review-pr --pr 42
      python -m compliantflow --dhf path/to/DHF review-pr --pr 42 --post-comment
    """
    import subprocess

    if diff_file is None and pr_number is None:
        raise click.UsageError("Provide either --diff <file> or --pr <number>.")

    # Read diff
    if pr_number:
        try:
            result = subprocess.run(
                ["gh", "pr", "diff", str(pr_number)],
                capture_output=True, text=True, check=True,
            )
            diff_text = result.stdout
        except subprocess.CalledProcessError as exc:
            raise click.ClickException(f"gh pr diff failed: {exc.stderr.strip()}")
        except FileNotFoundError:
            raise click.ClickException("'gh' CLI not found. Install the GitHub CLI to use --pr.")
    elif diff_file == "-":
        diff_text = sys.stdin.read()
    else:
        diff_text = Path(diff_file).read_text(encoding="utf-8")

    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    result = core.review_pr(diff_text, governance_dir=gov_dir)

    checklist = result["checklist"]
    changed = result["changed_items"]
    analyzed = result["chains_analyzed"]

    # Build full comment body
    header = (
        f"## CompliantFlow DHF Review\n\n"
        f"**Changed DHF items detected:** {', '.join(changed) if changed else 'none'}\n"
        f"**Chains analysed:** {', '.join(analyzed) if analyzed else 'none'}\n\n"
        f"### Required DHF Actions\n\n"
        f"{checklist}\n\n"
        f"---\n"
        f"_Generated by CompliantFlow · Suggestion layer — not a compliance gate_"
    )

    click.echo(header)

    if post_comment and pr_number:
        try:
            subprocess.run(
                ["gh", "pr", "comment", str(pr_number), "--body", header],
                check=True,
            )
            click.echo(f"✓ Comment posted to PR #{pr_number}", err=True)
        except subprocess.CalledProcessError as exc:
            raise click.ClickException(f"gh pr comment failed: {exc.stderr.strip()}")


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------

@main.command("context")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Path to governance directory. Defaults to ./governance.")
@click.option("--standard", default=None, metavar="ID",
              help="Filter compliance policies to this standard (e.g. IEC_62304).")
@click.option("--summary", is_flag=True, default=False,
              help="Emit policy IDs and headings only — omit check details.")
@click.option("--format", "fmt", default="json", show_default=True,
              type=click.Choice(["json", "yaml"], case_sensitive=False),
              help="Output format.")
@click.pass_context
def context(ctx: click.Context, governance_dir: str | None, standard: str | None,
            summary: bool, fmt: str) -> None:
    """Output DHF schema, lifecycle rules, and compliance policy summaries for AI agents.

    Provides the full item type schema (fields, allowed values, ID prefixes),
    global lifecycle states, and compliance policy summaries from governance
    YAML files in a machine-readable format.  Run this before generating or
    editing DHF content to avoid CI failures from invalid field values.

    \b
    Example:
      python -m compliantflow --dhf path/to/DHF context
      python -m compliantflow --dhf path/to/DHF context --standard IEC_62304 --summary
      python -m compliantflow --dhf path/to/DHF context --format yaml
    """
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    result = core.get_context(gov_dir, standard=standard, summary=summary)

    if fmt == "yaml":
        try:
            import yaml as _yaml
            click.echo(_yaml.dump(result, default_flow_style=False, allow_unicode=True))
        except ImportError:
            raise click.ClickException("PyYAML is required for --format yaml. Install it with: pip install pyyaml")
    else:
        click.echo(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@main.command("status")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Path to governance directory. Defaults to ./governance.")
@click.option("--live", is_flag=True, default=False,
              help="Run fresh compliance checks instead of reading from persisted run store.")
@click.option("--format", "fmt", default="text", show_default=True,
              type=click.Choice(["text", "json"], case_sensitive=False),
              help="Output format.")
@click.pass_context
def status(ctx: click.Context, governance_dir: str | None, live: bool, fmt: str) -> None:
    """Show at-a-glance compliance posture: scores, traceability, defects, release.

    Reads compliance scores from the persisted run store by default.
    Use --live to run fresh checks (invokes LLM for semantic policies).

    \b
    Example:
      python -m compliantflow --dhf path/to/DHF status
      python -m compliantflow --dhf path/to/DHF status --live --format json
    """
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    result = core.get_status(gov_dir, live=live)

    if fmt == "json":
        click.echo(json.dumps(result, default=str))
        return

    # Human-readable text output
    click.echo("\n── Compliance ──────────────────────────────────")
    compliance = result.get("compliance", [])
    if not compliance:
        click.echo("  No governance files found.")
    for entry in compliance:
        score = entry.get("score")
        score_str = f"{score:.0f}%" if score is not None else "n/a"
        passed = entry.get("passed_policies", "?")
        total = entry.get("total_policies", "?")
        source = entry.get("source", "")
        ts = str(entry.get("last_run_at", ""))[:16].replace("T", " ")
        status_icon = "✓" if score is not None and score == 100.0 else "✗"
        click.echo(f"  {status_icon} {entry['standard']}: {score_str} ({passed}/{total}) [{source}] {ts}")

    click.echo("\n── Traceability ─────────────────────────────────")
    trace = result.get("traceability", [])
    if not trace:
        click.echo("  No traceability data.")
    for t in trace:
        icon = "✓" if t["coverage_pct"] == 100.0 else "✗"
        click.echo(
            f"  {icon} {t['parent_type']}→{t['child_type']}: "
            f"{t['coverage_pct']}% ({t['covered']}/{t['total']})"
        )

    click.echo("\n── Open Defects ─────────────────────────────────")
    defs = result.get("open_defects", {})
    count = defs.get("count", 0)
    if count == 0:
        click.echo("  ✓ No open defects.")
    else:
        click.echo(f"  ✗ {count} open defect(s):")
        for d in defs.get("items", [])[:5]:
            click.echo(f"    - {d['id']} [{d['status']}] {d.get('title', '')}")
        if count > 5:
            click.echo(f"    … and {count - 5} more")

    click.echo("\n── Release ──────────────────────────────────────")
    rel = result.get("release")
    if rel is None:
        click.echo("  No REL item found.")
    else:
        icon = "✓" if rel.get("passed") else "✗"
        click.echo(f"  {icon} {rel['rel_id']}: {'ready' if rel.get('passed') else 'not ready'}")
        for c in rel.get("checks", []):
            ci = "✓" if c["passed"] else "✗"
            click.echo(f"    {ci} {c['name']}: {c['details']}")
    click.echo("")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@main.group()
def validate() -> None:
    """Commands for DHF validation."""


@validate.command("traceability")
@click.pass_context
def validate_traceability(ctx: click.Context) -> None:
    """Check required traceability, orphan detection, and graph integrity.

    Exits 1 if any required traceability failures or orphaned items are found.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)

    # Item-level: required traceability + deprecated allowed_parents (adapter)
    adapter_result = core._adapter.validate_traceability()

    # Graph-level: orphan/cycle (networkx)
    graph_result = core.validate()

    failed = False

    # --- Required traceability failures (adapter) ---
    required = adapter_result.get("required", {})
    if not required.get("passed", True):
        failed = True
        for f in required.get("failures", []):
            click.echo(
                f"FAIL [required] {f['id']}: {f['issue']}",
                err=True,
            )

    # --- Graph orphans (deprecated allowed_parents) ---
    if not graph_result.get("valid", True):
        for issue in graph_result.get("issues", []):
            issue_type = issue.get("type", "issue")
            affected = issue.get("items", [])
            if issue_type == "orphans":
                failed = True
                for item in affected:
                    click.echo(
                        f"FAIL [deprecated orphan] {item['uid']}: {item['issue']}",
                        err=True,
                    )
            elif issue_type == "cycles":
                click.echo(
                    f"WARN [cycles]: {issue['count']} cycle(s) detected",
                    err=True,
                )

    # --- Deprecation warnings ---
    for w in adapter_result.get("deprecation_warnings", []):
        click.echo(f"WARN [deprecated] {w}", err=True)

    # --- Coverage ---
    for cr in adapter_result.get("coverage", []):
        status = "PASS" if cr["passed"] else "FAIL"
        click.echo(
            f"{status} [coverage] {cr['parent_type']}→{cr['child_type']}: "
            f"{cr['covered']}/{cr['total']} covered",
            err=True,
        )

    # --- Summary ---
    if failed:
        click.echo(adapter_result.get("summary", ""), err=True)
        sys.exit(1)

    item_count = len(core.get_all_items())
    click.echo(f"✓ All {item_count} items pass traceability checks.", err=True)


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
    core = _make_core(ctx)

    try:
        parsed = _parse_coverage_pairs(pairs)
    except click.BadParameter as exc:
        click.echo(f"ERROR: {exc.message}", err=True)
        sys.exit(2)

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
@click.option(
    "--persist/--no-persist",
    default=False,
    help="Persist the compliance run to the DHF compliance-runs store.",
)
@click.pass_context
def validate_compliance(
    ctx: click.Context,
    group_id: str,
    governance_dir: str | None,
    persist: bool,
) -> None:
    """Check compliance against a governance policy group.

    GROUP_ID is the filename stem of a policy YAML file (e.g. IEC_62304).
    Outputs the full JSON report to stdout.
    Exits 1 if any policy fails.
    """
    dhf_path: Path = ctx.obj["dhf"]
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    report = core.check_compliance(group_id, governance_dir=gov_dir, persist=persist)
    if report is None:
        click.echo(f"ERROR: Policy group '{group_id}' not found.", err=True)
        sys.exit(1)
    failed = [r for r in report["results"] if not r["passed"]]
    for r in failed:
        click.echo(f"  ✗ [{r['policy_id']}] {r['policy_text']}: {r['details']}", err=True)
        rem = r.get("remediation")
        if rem:
            guidance = rem.get("guidance", "")
            items = rem.get("items", [])
            line = f"     → {guidance}"
            if items:
                preview = ", ".join(items[:5])
                if len(items) > 5:
                    preview += f" (+{len(items) - 5} more)"
                line += f" [{preview}]"
            click.echo(line, err=True)
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


@validate.command("release")
@click.argument("rel_id")
@click.pass_context
def validate_release(ctx: click.Context, rel_id: str) -> None:
    """Evaluate whether a REL item meets all release criteria.

    REL_ID is the identifier of the release (e.g. REL-002).

    Checks:
      1. REL item exists.
      2. All included CRs are completed.
      3. No open DEF items exist (draft/open/in_progress).
      4. All SYS requirements are verified.

    Outputs a JSON report to stdout.
    Exits 0 if all checks pass; exits 1 if any fail.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    report = core.validate_release(rel_id)
    click.echo(json.dumps(report, default=str))
    failed = [c for c in report["checks"] if not c["passed"]]
    if failed:
        for c in failed:
            click.echo(f"  ✗ [{c['name']}] {c['details']}", err=True)
        click.echo(
            f"✗ Release gate FAILED: {len(failed)}/{len(report['checks'])} check(s) did not pass.",
            err=True,
        )
        sys.exit(1)
    click.echo(
        f"✓ Release gate PASSED: all {len(report['checks'])} checks passed for {rel_id}.",
        err=True,
    )


@validate.command("draft")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--type", "item_type", default=None, metavar="TYPE",
              help="Item type code (e.g. SYS). Inferred from id prefix if omitted.")
@click.option("--format", "fmt", default="json", show_default=True,
              type=click.Choice(["json", "text"], case_sensitive=False),
              help="Output format.")
@click.pass_context
def validate_draft(ctx: click.Context, file: str, item_type: str | None, fmt: str) -> None:
    """Validate a draft DHF item YAML against the doc-type field schema.

    Checks required fields and allowed values without requiring a full CI run.
    Graph-dependent checks (traceability, verification) are out of scope.
    Exits 0 on pass, 1 on validation failure.

    \b
    Example:
      python -m compliantflow --dhf path/to/DHF validate draft my_item.yaml
      python -m compliantflow --dhf path/to/DHF validate draft my_item.yaml --type SYS
    """
    import yaml as _yaml

    with open(file, "r", encoding="utf-8") as f:
        try:
            item_data = _yaml.safe_load(f)
        except Exception as exc:
            raise click.ClickException(f"Failed to parse YAML: {exc}")

    if not isinstance(item_data, dict):
        raise click.ClickException("Item file must be a YAML mapping.")

    core = _make_core(ctx)
    result = core.validate_draft(item_data, type_name=item_type)

    if fmt == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        valid = result["valid"]
        icon = "✓" if valid else "✗"
        item_type_str = result.get("type") or "unknown"
        click.echo(f"{icon} {item_type_str}: {'valid' if valid else 'invalid'}")
        for w in result.get("warnings", []):
            click.echo(f"  ⚠  {w['field']}: {w['message']}")
        for e in result.get("errors", []):
            click.echo(f"  ✗  {e['field']}: {e['message']}")

    if not result["valid"]:
        sys.exit(1)


@validate.group("compliance-history")
def validate_compliance_history() -> None:
    """Compliance run history commands."""


@validate_compliance_history.command("list")
@click.argument("group_id")
@click.option("--since", default=None, metavar="DATE",
              help="Filter to runs at or after this ISO 8601 date (e.g. 2026-01-01).")
@click.pass_context
def validate_compliance_history_list(
    ctx: click.Context,
    group_id: str,
    since: str | None,
) -> None:
    """List persisted compliance runs for GROUP_ID.

    Outputs each run as a JSON object on stdout (NDJSON).
    """
    from dhf_util.local_adapter import LocalDHFAdapter
    dhf_path: Path = ctx.obj["dhf"]
    adapter = LocalDHFAdapter(dhf_path, auto_commit=False)
    runs = adapter.get_compliance_runs(group_id, since_date=since)
    for run in runs:
        click.echo(json.dumps(run, default=str))
    click.echo(f"({len(runs)} run(s) for '{group_id}')", err=True)


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
    core = _make_core(ctx)
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
    core = _make_core(ctx)
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
@click.option("--junit", "junit_paths", multiple=True, type=click.Path(exists=True),
              help="JUnit XML file(s) for test status (in-memory only, not stored in DHF).")
@click.pass_context
def report_traceability(ctx: click.Context, doc_types: tuple, output: str,
                        junit_paths: tuple) -> None:
    """Generate a traceability matrix PDF.

    \b
    Example:
      python -m compliantflow report traceability UC CRS SYS SYSARCH \\
        --output traceability_report.pdf
    """
    core = _make_core(ctx)
    out = Path(output)
    report_result = _write_traceability_report(core, doc_types, out, junit_paths)
    click.echo(f"✓ Traceability report written to {out} "
               f"({report_result['rows']} rows)", err=True)


@report.command("compliance")
@click.argument("group_id")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Path to governance directory. Defaults to ./governance.")
@click.option("--output", "-o", default=None, show_default=False,
              help="Output file path. Defaults to compliance_report.pdf or compliance_report.json.")
@click.option("--format", "fmt", default="pdf", show_default=True,
              type=click.Choice(["pdf", "json"], case_sensitive=False),
              help="Output format: pdf (default) or json for programmatic consumption.")
@click.pass_context
def report_compliance(ctx: click.Context, group_id: str,
                      governance_dir: str | None, output: str | None, fmt: str) -> None:
    """Generate a compliance evidence report (PDF or JSON).

    \b
    Examples:
      python -m compliantflow report compliance IEC_62304 --governance-dir governance
      python -m compliantflow report compliance IEC_62304 --format json --output report.json
    """
    from compliantflow.report_generator import generate_compliance_pdf, generate_compliance_json
    gov_dir = Path(governance_dir) if governance_dir else Path("governance")
    core = _make_core(ctx)
    result = core.check_compliance(group_id, governance_dir=gov_dir)
    if result is None:
        click.echo(f"ERROR: Policy group '{group_id}' not found.", err=True)
        sys.exit(1)
    default_name = f"compliance_report.{'json' if fmt == 'json' else 'pdf'}"
    out = Path(output) if output else Path(default_name)
    if fmt == "json":
        generate_compliance_json(result, out)
    else:
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


# ---------------------------------------------------------------------------
# cr group
# ---------------------------------------------------------------------------

@main.group()
def cr() -> None:
    """Commands for Change Request git-evidence management."""


@cr.group("workflow")
def cr_workflow() -> None:
    """Reusable CR workflow orchestration commands."""


@cr_workflow.command("complete")
@click.option("--dhf-repo", type=click.Path(file_okay=False, path_type=Path),
              help="DHF repository root. Defaults to the parent of --dhf.")
@click.option("--cr", "cr_id", required=True, metavar="CR_ID",
              help="Change Request ID to complete.")
@click.option("--by", "performed_by", default="compliantflow", show_default=True,
              help="Actor recorded on the CR lifecycle transition.")
@click.option("--commit/--no-commit", "commit_changes", default=True, show_default=True,
              help="Commit DHF repository changes when the transition modifies files.")
@click.option("--push", is_flag=True, default=False,
              help="Push committed DHF repository changes to the configured remote.")
@click.option("--message", default=None, metavar="TEXT",
              help="Commit message. Defaults to 'chore: complete CR-ID [skip ci]'.")
@click.pass_context
def cr_workflow_complete(
    ctx: click.Context,
    dhf_repo: Path | None,
    cr_id: str,
    performed_by: str,
    commit_changes: bool,
    push: bool,
    message: str | None,
) -> None:
    """Complete a CR in a DHF repository after implementation merge."""
    from dhf_util.change_requests import complete_change_request

    repo_root, dhf_root = _resolve_dhf_repo_paths(ctx, dhf_repo)
    adapter = _make_adapter_for_dhf_root(dhf_root)

    try:
        transition = complete_change_request(adapter, cr_id, performed_by=performed_by)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    changed = _git_has_changes(repo_root)
    committed = False
    pushed = False
    commit_message = message or f"chore: complete {cr_id} [skip ci]"

    if changed and commit_changes:
        _run_git(repo_root, ["add", "-A"])
        if _git_has_changes(repo_root):
            _run_git(repo_root, ["commit", "-m", commit_message])
            committed = True
            if push:
                _run_git(repo_root, ["push"])
                pushed = True

    result = {
        "cr_id": cr_id,
        "dhf_repo": str(repo_root),
        "dhf_root": str(dhf_root),
        "transition": transition,
        "changed": changed,
        "committed": committed,
        "pushed": pushed,
        "commit_message": commit_message if committed else None,
    }
    click.echo(json.dumps(result, default=str))


@cr_workflow.command("intake-github-issue")
@click.option("--dhf-repo", type=click.Path(file_okay=False, path_type=Path),
              help="DHF repository root. Defaults to the parent of --dhf.")
@click.option("--event", "event_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="GitHub issue event JSON path, usually GITHUB_EVENT_PATH.")
@click.option("--comments", "comments_path", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="JSON file containing existing issue comments.")
@click.option("--active-milestone", default=None,
              help="Milestone required for CR intake. Defaults to current ISO week.")
@click.option("--marker-name", default="compliantflow-cr", show_default=True,
              help="HTML comment marker name used to detect prior CR intake.")
@click.option("--branch-prefix", default="cr", show_default=True,
              help="Branch prefix for the generated CR branch.")
@click.option("--title-prefix", default="cr", show_default=True,
              help="PR title prefix for the generated CR PR.")
@click.option("--write", is_flag=True, default=False,
              help="Create the CR item in the DHF. Without this, only compute the next CR ID.")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path),
              help="Optional JSON output path.")
@click.pass_context
def cr_workflow_intake_github_issue(
    ctx: click.Context,
    dhf_repo: Path | None,
    event_path: Path,
    comments_path: Path | None,
    active_milestone: str | None,
    marker_name: str,
    branch_prefix: str,
    title_prefix: str,
    write: bool,
    output: Path | None,
) -> None:
    """Prepare a CR from a GitHub issue event."""
    from compliantflow.cr_intake import (
        current_iso_week_milestone,
        load_comments,
        load_github_issue_event,
        prepare_cr_from_issue,
    )

    _, dhf_root = _resolve_dhf_repo_paths(ctx, dhf_repo)
    adapter = _make_adapter_for_dhf_root(dhf_root)
    result = prepare_cr_from_issue(
        load_github_issue_event(event_path),
        active_milestone or current_iso_week_milestone(),
        load_comments(comments_path),
        write=write,
        adapter=adapter,
        marker_name=marker_name,
        branch_prefix=branch_prefix,
        title_prefix=title_prefix,
    )
    payload = {
        "should_create": result.should_create,
        "reason": result.reason,
        "cr_id": result.cr_id,
        "branch": result.branch,
        "cr_path": result.cr_path,
        "title": result.title,
    }
    text = json.dumps(payload, indent=2)
    if output:
        output.write_text(text + "\n", encoding="utf-8")
    click.echo(text)


@cr_workflow.command("intake-github-issue-ci")
@click.option("--dhf-repo", type=click.Path(file_okay=False, path_type=Path),
              help="DHF repository root. Defaults to the parent of --dhf.")
@click.option("--event", "event_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="GitHub issue event JSON path, usually GITHUB_EVENT_PATH.")
@click.option("--comments", "comments_path", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="JSON file containing existing issue comments. Defaults to fetching comments via gh api.")
@click.option("--active-milestone", default=None,
              help="Milestone required for CR intake. Defaults to current ISO week.")
@click.option("--marker-name", default="compliantflow-cr", show_default=True,
              help="HTML comment marker name used to detect prior CR intake.")
@click.option("--branch-prefix", default="cr", show_default=True,
              help="Branch prefix for the generated CR branch.")
@click.option("--title-prefix", default="cr", show_default=True,
              help="PR title prefix for the generated CR PR.")
@click.option("--write", is_flag=True, default=False,
              help="Create the CR item in the DHF. Without this, only compute the next CR ID.")
@click.option("--create-branch", is_flag=True, default=False,
              help="Create and push a DHF branch for the CR.")
@click.option("--open-pr", is_flag=True, default=False,
              help="Open a DHF pull request for the CR branch.")
@click.option("--source-repo", default=None, metavar="OWNER/REPO",
              help="GitHub repository of the source issue (for PR and comment).")
@click.option("--comment-source-issue", is_flag=True, default=False,
              help="Post a comment on the source issue linking to the created CR.")
@click.option("--issue-number", type=int, default=None,
              help="Source issue number. Defaults to the event payload number.")
@click.option("--github-token", default=None, metavar="TOKEN",
              help="GitHub token for branch push and PR/comment operations.")
@click.option("--milestone-title", default=None, metavar="TITLE",
              help="Milestone title for the PR description. Defaults to event milestone.")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path),
              help="Optional JSON output path.")
@click.option("--github-output", type=click.Path(dir_okay=False, path_type=Path),
              help="Optional GitHub Actions output file path.")
@click.pass_context
def cr_workflow_intake_github_issue_ci(
    ctx: click.Context,
    dhf_repo: Path | None,
    event_path: Path,
    comments_path: Path | None,
    active_milestone: str | None,
    marker_name: str,
    branch_prefix: str,
    title_prefix: str,
    write: bool,
    create_branch: bool,
    open_pr: bool,
    source_repo: str | None,
    comment_source_issue: bool,
    issue_number: int | None,
    github_token: str | None,
    milestone_title: str | None,
    output: Path | None,
    github_output: Path | None,
) -> None:
    """Full CI intake pipeline: prepare CR + GitHub plumbing (branch, PR, comment).

    Wraps the intake-github-issue logic and adds git/PR/comment operations
    that WebTPS or any product repo would otherwise script manually.
    Requires 'gh' CLI and 'git' in PATH.
    """
    from compliantflow.cr_intake import (
        current_iso_week_milestone,
        load_github_issue_event,
        prepare_cr_from_issue,
    )

    repo_root, dhf_root = _resolve_dhf_repo_paths(ctx, dhf_repo)
    adapter = _make_adapter_for_dhf_root(dhf_root)
    gh_token = github_token or os.environ.get("GH_TOKEN") or ""
    source_token = os.environ.get("GITHUB_TOKEN") or gh_token
    gh_env = _github_env(gh_token)

    # Resolve event data
    event = load_github_issue_event(event_path)
    issue_num = issue_number or event.number
    src_repo = source_repo or os.environ.get("GITHUB_REPOSITORY", "")
    milestone = milestone_title or event.milestone or ""

    # Step 1: Prepare CR
    result = prepare_cr_from_issue(
        event,
        active_milestone or current_iso_week_milestone(),
        _load_issue_comments(
            comments_path,
            source_repo=src_repo,
            issue_number=issue_num,
            source_token=source_token,
        ),
        write=write,
        adapter=adapter,
        marker_name=marker_name,
        branch_prefix=branch_prefix,
        title_prefix=title_prefix,
    )

    # Step 2: GitHub plumbing (branch, PR, comment)
    branch_url = ""
    pr_url = ""
    if result.should_create and write:
        branch = result.branch
        if create_branch:
            _run_git(repo_root, ["checkout", "-B", branch])
            _run_git(repo_root, ["add", "-A"])
            if _git_has_changes(repo_root):
                _run_git(repo_root, ["commit", "-m", f"cr: create {result.cr_id} from issue"])
                if gh_token:
                    _run_git(repo_root, ["push", "--force", "--set-upstream", "origin", branch])
                else:
                    _run_git(repo_root, ["push", "--force", "--set-upstream", "origin", branch])

        if open_pr and src_repo:
            try:
                existing = subprocess.run(
                    ["gh", "pr", "list", "--head", branch, "--json", "url",
                     "--jq", ".[0].url"],
                    cwd=repo_root, capture_output=True, text=True, env=gh_env,
                )
                if existing.returncode == 0 and existing.stdout.strip():
                    pr_url = existing.stdout.strip()
                else:
                    body = (
                        f"Automated CR intake from {src_repo} issue:\n\n"
                        f"- Source issue: {event.html_url}\n"
                        f"- Target weekly milestone: {milestone}\n\n"
                        f"This PR creates {result.cr_id}. Human approval is required."
                    )
                    proc = subprocess.run(
                        ["gh", "pr", "create", "--head", branch, "--base", "main",
                         "--title", result.title, "--body", body],
                        cwd=repo_root, capture_output=True, text=True, env=gh_env,
                    )
                    if proc.returncode == 0:
                        pr_url = proc.stdout.strip()
            except FileNotFoundError:
                click.echo("WARNING: 'gh' CLI not found; skipping PR creation.", err=True)

        if comment_source_issue and src_repo and issue_num and result.cr_id:
            comment_body = (
                f"CR created from this issue.\n\n"
                f"CR: {result.cr_id}\n"
                f"DHF PR: {pr_url}\n\n"
                f"<!-- {marker_name}: {result.cr_id} -->\n"
                f"<!-- {marker_name}-pr: {pr_url} -->"
            )
            try:
                subprocess.run(
                    ["gh", "issue", "comment", str(issue_num), "--body", comment_body,
                     "--repo", src_repo],
                    capture_output=True, text=True, env=_github_env(source_token), check=False,
                )
            except FileNotFoundError:
                click.echo("WARNING: 'gh' CLI not found; skipping issue comment.", err=True)

    # Step 3: Output (GitHub Actions output format)
    payload = {
        "should_create": result.should_create,
        "reason": result.reason,
        "cr_id": result.cr_id,
        "branch": result.branch,
        "branch_url": branch_url,
        "pr_url": pr_url,
        "title": result.title,
    }
    text = json.dumps(payload, indent=2)
    if output:
        output.write_text(text + "\n", encoding="utf-8")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f_out:
            for key, value in payload.items():
                val = str(value) if value is not None else ""
                if isinstance(value, bool):
                    val = str(value).lower()
                f_out.write(f"{key}={val}\n")
    click.echo(text)


@cr_workflow.command("complete-from-github-pr")
@click.option("--dhf-repo", type=click.Path(file_okay=False, path_type=Path),
              help="DHF repository root. Defaults to the parent of --dhf.")
@click.option("--event", "event_path", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None, help="GitHub pull request event JSON (GITHUB_EVENT_PATH).")
@click.option("--pr-title", default=None, metavar="TITLE",
              help="PR title to parse. Defaults to reading from --event.")
@click.option("--by", "performed_by", default="compliantflow", show_default=True,
              help="Actor recorded on the CR lifecycle transition.")
@click.option("--push", is_flag=True, default=False,
              help="Push committed DHF repository changes.")
@click.option("--message", default=None, metavar="TEXT",
              help="Commit message. Defaults to 'chore: complete CR-ID [skip ci]'.")
@click.pass_context
def cr_workflow_complete_from_github_pr(
    ctx: click.Context,
    dhf_repo: Path | None,
    event_path: Path | None,
    pr_title: str | None,
    performed_by: str,
    push: bool,
    message: str | None,
) -> None:
    """Complete a CR from a merged GitHub PR event.

    Parses the CR ID from the PR title (regex CR-\\d+), then delegates
    to ``cr workflow complete``.  Exits 0 with a skip message when no
    CR ID is found — the workflow should never block deployment.
    """
    import re as _re

    title = pr_title or ""
    if not title and event_path:
        try:
            event_data = json.loads(event_path.read_text(encoding="utf-8"))
            title = event_data.get("pull_request", {}).get("title", "")
        except (json.JSONDecodeError, OSError):
            pass

    cr_match = _re.search(r"CR-\d+", title) if title else None
    if not cr_match:
        payload = {"skip": True, "reason": "No CR ID found in PR title"}
        click.echo(json.dumps(payload))
        return

    cr_id = cr_match.group(0)

    repo_root, dhf_root = _resolve_dhf_repo_paths(ctx, dhf_repo)
    adapter = _make_adapter_for_dhf_root(dhf_root)

    # Configure git identity for commit
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "GitHub Actions [bot]"],
        capture_output=True, check=False,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email",
         "github-actions[bot]@users.noreply.github.com"],
        capture_output=True, check=False,
    )

    try:
        from dhf_util.change_requests import complete_change_request
        transition = complete_change_request(adapter, cr_id, performed_by=performed_by)
    except ValueError as exc:
        # CR may already be in a terminal state — skip gracefully instead of failing
        item = adapter.get_item(cr_id)
        current_status = item.get("status", "unknown") if item else "unknown"
        if current_status in ("completed", "cancelled"):
            click.echo(f"SKIP: {cr_id} is already '{current_status}' — nothing to do.", err=True)
            return
        raise click.ClickException(str(exc)) from exc

    changed = _git_has_changes(repo_root)
    commit_message = message or f"chore: complete {cr_id} [skip ci]"
    committed = False
    pushed = False

    if changed:
        _run_git(repo_root, ["add", "-A"])
        if _git_has_changes(repo_root):
            _run_git(repo_root, ["commit", "-m", commit_message])
            committed = True
            if push:
                _run_git(repo_root, ["push"])
                pushed = True

    result = {
        "cr_id": cr_id,
        "pr_title": title,
        "transition": transition,
        "changed": changed,
        "committed": committed,
        "pushed": pushed,
    }
    click.echo(json.dumps(result, default=str))


@cr.command("check-status")
@click.argument("cr_id")
@click.pass_context
def cr_check_status(ctx: click.Context, cr_id: str) -> None:
    """Check that a Change Request exists and is in an authorized state.

    CR_ID is the identifier of the change request (e.g. CR-012).
    Outputs a JSON object to stdout.
    Exits 0 if the CR exists and is in an in-progress state; exits 1 otherwise.

    Note: linked commits/PRs are evidence recorded AFTER the work is merged.
    This gate only verifies the CR is authorized — not that evidence exists yet.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    item = core.get_item(cr_id)
    if item is None:
        click.echo(json.dumps({"cr_id": cr_id, "found": False, "error": f"CR '{cr_id}' not found"}))
        click.echo(f"ERROR: CR '{cr_id}' not found.", err=True)
        sys.exit(1)

    status = item.get("status", "")
    valid_statuses = {"new", "analyzing", "developing"}
    valid = status in valid_statuses

    result = {
        "cr_id": cr_id,
        "found": True,
        "status": status,
        "valid": valid,
    }
    click.echo(json.dumps(result, default=str))

    if valid:
        click.echo(f"✓ CR '{cr_id}' is authorized (status: {status}).", err=True)
    else:
        click.echo(
            f"✗ CR '{cr_id}' is not authorized: status is '{status}' "
            f"(expected one of: {', '.join(sorted(valid_statuses))}).",
            err=True,
        )
        sys.exit(1)


@cr.command("generate-report")
@click.argument("cr_id")
@click.option("--since", default=None, metavar="DATE",
              help="Only include commits after this date (ISO 8601).")
@click.pass_context
def cr_generate_report(ctx: click.Context, cr_id: str, since: str | None) -> None:
    """Scan git log to generate a CR-PR evidence report.

    Outputs a JSON object to stdout with the CR details and associated commits
    extracted from git log messages mentioning CR_ID.

    The resulting JSON can be written to a file and consumed by the
    ``cr_git_evidence`` policy check via COMPLIANTFLOW_CR_REPORT_PATH.
    """
    import subprocess  # noqa: PLC0415
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    item = core.get_item(cr_id)

    cr_data: dict = {}
    if item:
        cr_data = {
            "cr_id": cr_id,
            "title": item.get("title", ""),
            "status": item.get("status", ""),
            "affected_items": item.get("affected_items") or [],
            "implementation_prs": item.get("implementation_prs") or [],
        }
    else:
        cr_data = {"cr_id": cr_id, "found": False}

    # Scan git log for commits mentioning this CR ID
    git_args = [
        "git", "-C", str(dhf_path.parent),
        "log", "--all", "--format=%H %s",
        f"--grep={cr_id}",
    ]
    if since:
        git_args += [f"--after={since}"]

    commits = []
    pr_numbers: list[str] = []
    try:
        import re  # noqa: PLC0415
        proc = subprocess.run(git_args, capture_output=True, text=True, timeout=30)
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            sha = parts[0]
            message = parts[1] if len(parts) > 1 else ""
            commits.append({"sha": sha, "message": message})
            # Extract PR numbers from GitHub squash-merge format: "Title (#123)"
            for match in re.finditer(r'\(#(\d+)\)', message):
                pr_num = match.group(1)
                if pr_num not in pr_numbers:
                    pr_numbers.append(pr_num)
    except Exception as exc:
        click.echo(f"WARNING: git log scan failed: {exc}", err=True)

    cr_data["commits"] = commits
    cr_data["implementation_prs"] = pr_numbers
    click.echo(json.dumps(cr_data, default=str))
    click.echo(
        f"({len(commits)} commit(s) referencing {cr_id} found in git log)", err=True
    )


# ---------------------------------------------------------------------------
# test group
# ---------------------------------------------------------------------------

@main.group()
def test() -> None:
    """Commands for test result integration."""


@test.command("import")
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "fmt", default="junit", show_default=True,
              type=click.Choice(["junit"], case_sensitive=False),
              help="Test result format.")
@click.option("--tester", default="", help="Name of the tester or CI agent.")
@click.option("--run-id", default="", help="CI run ID.")
@click.option("--run-url", default="", help="URL to the CI run.")
@click.option("--commit", default="", help="Git commit SHA.")
@click.pass_context
def test_import(
    ctx: click.Context,
    path: str,
    fmt: str,
    tester: str,
    run_id: str,
    run_url: str,
    commit: str,
) -> None:
    """Import test results from a JUnit XML file.

    PATH is the path to the test result file.
    Outputs a JSON summary to stdout.
    """
    adapter = _make_adapter(ctx)
    summary = _import_results_file(adapter, Path(path), tester, run_id, run_url, commit)
    summary.pop("path", None)
    click.echo(json.dumps(summary, default=str))
    click.echo(
        f"✓ Imported {summary['imported']} result(s), "
        f"skipped {summary['skipped']}, "
        f"updated {len(summary['items_updated'])} item(s).",
        err=True,
    )
    if summary["failed_tcs"]:
        click.echo(f"  ✗ Failing TCs: {summary['failed_tcs']}", err=True)


@test.command("status")
@click.argument("tc_id")
@click.pass_context
def test_status(ctx: click.Context, tc_id: str) -> None:
    """Show the latest test result for a TC.

    TC_ID is the test case identifier (e.g. TC-SYS-001-001).
    Outputs a JSON object to stdout.
    Exits 1 if the TC is not found.
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    result = core.get_test_result(tc_id)
    if result is None:
        click.echo(json.dumps({"tc_id": tc_id, "found": False}))
        click.echo(f"ERROR: TC '{tc_id}' not found.", err=True)
        sys.exit(1)
    click.echo(json.dumps(result, default=str))
    status = result.get("testing_status", "UNKNOWN")
    click.echo(f"  {tc_id}: {status}", err=True)


@test.command("list")
@click.option("--status", "status_filter", default=None,
              type=click.Choice(["PASS", "FAIL", "SKIP"], case_sensitive=False),
              help="Filter by testing status.")
@click.pass_context
def test_list(ctx: click.Context, status_filter: str | None) -> None:
    """List all imported test results.

    Outputs one JSON object per result to stdout (NDJSON).
    """
    dhf_path: Path = ctx.obj["dhf"]
    core = _make_core(ctx)
    sf = status_filter.upper() if status_filter else None
    results = core.get_all_test_results(status_filter=sf)
    for rec in results.values():
        click.echo(json.dumps(rec, default=str))
    click.echo(f"({len(results)} result(s))", err=True)


# ---------------------------------------------------------------------------
# migrate group
# ---------------------------------------------------------------------------

@main.group()
def migrate() -> None:
    """Migrate external repository formats into a CompliantFlow DHF."""


@migrate.command("rdm")
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--dry-run", is_flag=True, default=False,
    help="Parse and map items without writing any files.",
)
@click.option(
    "--report-output", default=None, metavar="FILE",
    help="Write a Markdown completeness report to FILE after migration.",
)
@click.pass_context
def migrate_rdm(ctx: click.Context, source_dir: Path, dry_run: bool,
                report_output: str | None) -> None:
    """Migrate an Innolitics RDM repository into this DHF.

    SOURCE_DIR is the root of the RDM repository to migrate.

    Discovers all YAML requirement files under SOURCE_DIR, maps them to
    CompliantFlow doc types, converts reST content to Markdown, writes items
    into DHF/items/, and prints a JSON migration report to stdout.

    After writing items, runs post-migration field schema validation and
    categorises results into clean / gaps / skipped.  Use --report-output to
    save a Markdown completeness report.

    Use --dry-run to preview the mapping without writing any files.

    \b
    Example:
      python -m compliantflow --dhf path/to/DHF migrate rdm /path/to/rdm-repo
      python -m compliantflow --dhf path/to/DHF migrate rdm /path/to/rdm-repo --report-output migration_report.md
    """
    from compliantflow.migrate.rdm import RDMMigrator, generate_migration_markdown

    dhf_path: Path = ctx.obj["dhf"]
    dhf_items_dir = dhf_path / "items"

    migrator = RDMMigrator(source_dir=source_dir)
    migration_report = migrator.migrate(dhf_items_dir=dhf_items_dir, dry_run=dry_run)

    n_created = len(migration_report["created"])
    n_skipped = len(migration_report["skipped"])
    n_review = len(migration_report["needs_review"])
    suffix = " (dry run)" if dry_run else ""

    # Post-migration validation (skipped in dry-run mode)
    if not dry_run:
        core = _make_core(ctx)
        completeness = core.validate_migration_report(migration_report)
        click.echo(json.dumps(completeness, indent=2, default=str))

        if report_output:
            md = generate_migration_markdown(completeness)
            Path(report_output).write_text(md, encoding="utf-8")
            click.echo(f"✓ Markdown report written to {report_output}", err=True)

        n_gaps = completeness["summary"]["gaps"]
        click.echo(
            f"\n✓ Migration complete{suffix}: "
            f"{n_created} created ({completeness['summary']['clean']} clean, "
            f"{n_gaps} gap(s)), {n_skipped} skipped",
            err=True,
        )
        if n_gaps > 0 or n_skipped > 0:
            click.echo(
                "⚠  Review required before migration is considered complete.",
                err=True,
            )
    else:
        click.echo(json.dumps(migration_report, indent=2, default=str))
        click.echo(
            f"\n✓ Migration complete{suffix}: "
            f"{n_created} created, {n_skipped} skipped, {n_review} need review",
            err=True,
        )


# ---------------------------------------------------------------------------
# export group
# ---------------------------------------------------------------------------

@main.group()
def export() -> None:
    """Assemble submission and export artifacts."""


@export.command("submission")
@click.option("--governance-dir", default=None, metavar="PATH",
              help="Directory containing governance YAML files. Defaults to DHF/governance/.")
@click.option("--output-dir", default=".", show_default=True, metavar="PATH",
              help="Directory where the submission ZIP will be written.")
@click.option("--force", is_flag=True, default=False,
              help="Skip the compliance completeness gate and assemble anyway.")
@click.pass_context
def export_submission(
    ctx: click.Context,
    governance_dir: str | None,
    output_dir: str,
    force: bool,
) -> None:
    """Assemble a 510(k) submission evidence package.

    Runs the compliance completeness gate across all configured standards,
    then bundles the following artifacts into a dated ZIP:

    \b
      cover_document.pdf        — FDA eSTAR section mapping table
      traceability_report.pdf   — full traceability matrix
      compliance_{standard}.pdf — one per configured standard
      soup_list.pdf             — SOUP items with vulnerability status
      risk_rcm_summary.pdf      — RISK and RCM items
      test_results_summary.pdf  — test result summary
      cr_evidence.pdf           — closed CR history

    The package will not be produced if any compliance gate check is failing,
    unless --force is passed.
    """
    from compliantflow.submission import assemble_submission, SubmissionGateError

    dhf_path: Path = ctx.obj["dhf"]
    gov_dir = Path(governance_dir) if governance_dir else dhf_path / "governance"
    out_dir = Path(output_dir)

    if not gov_dir.is_dir():
        raise click.ClickException(
            f"Governance directory not found: {gov_dir}\n"
            "Pass --governance-dir or set COMPLIANTFLOW_GOVERNANCE_DIR."
        )

    core = _make_core(ctx)

    try:
        zip_path = assemble_submission(core, gov_dir, out_dir, force=force)
    except SubmissionGateError as exc:
        raise click.ClickException(str(exc))

    click.echo(f"✓ Submission package written to: {zip_path}", err=True)
    click.echo(str(zip_path))
