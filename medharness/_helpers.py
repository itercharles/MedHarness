"""Shared CLI helpers."""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import click

def _resolve_dhf(dhf_option: str | None) -> Path | None:
    """Return the DHF path from --dhf, or None if not provided."""
    return Path(dhf_option) if dhf_option else None


def _make_core(ctx: click.Context):
    """Instantiate MedHarnessCore from CLI context.

    Single-project mode (default): uses ``ctx.obj["dhf"]`` path with a
    ``LocalDHFAdapter`` (requires the DHF system to be installed alongside
    this tool, e.g. by installing medharness and pointing --dhf at a DHF repo).

    """
    try:
        from dhfkit.local_adapter import LocalDHFAdapter
    except ImportError:
        raise click.ClickException(
            "LocalDHFAdapter not found. Add your DHF system (e.g. a DHF project repo) "
            "to the Python path before running the CLI."
        )
    from medharness.core import MedHarnessCore


    dhf_path: Path = ctx.obj["dhf"]
    return MedHarnessCore(LocalDHFAdapter(dhf_path, auto_commit=False))


def _make_adapter(ctx: click.Context):
    """Instantiate the configured DHF adapter for facade operations."""
    try:
        from dhfkit.local_adapter import LocalDHFAdapter
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


def _summarize_junit_file(path: Path) -> dict:
    from dhfkit.junit_parser import parse_junit_xml

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
            cfg = core._adapter.get_item_type(prefix)
            if not cfg or not cfg.get("has_verification"):
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
            cfg = core._adapter.get_item_type(prefix)
            if not cfg or not cfg.get("has_verification"):
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


class _MissingPDFDeps(RuntimeError):
    """Raised when WeasyPrint or its native libraries are not available."""


def _write_traceability_report(core, doc_types: tuple[str, ...], output: Path,
                                junit_paths: tuple[str, ...] = ()) -> dict:
    matrix = _build_traceability_report_payload(core, doc_types, junit_paths)
    output.parent.mkdir(parents=True, exist_ok=True)

    json_output = output.with_suffix(".json")
    json_output.write_text(json.dumps(matrix, indent=2))

    result: dict = {
        "path": str(json_output),
        "json_path": str(json_output),
        "rows": len(matrix["rows"]),
    }

    if output.suffix.lower() == ".pdf":
        try:
            pdf_path = _render_traceability_matrix_pdf(matrix, output)
        except _MissingPDFDeps as exc:
            result["pdf_skipped"] = str(exc)
        else:
            result["path"] = str(pdf_path)
            result["pdf_path"] = str(pdf_path)

    return result


def _render_traceability_matrix_pdf(matrix: dict, output: Path) -> Path:
    """Render the traceability matrix payload as a Markdown -> HTML -> PDF document.

    WeasyPrint imports its Pango / Cairo / GObject native libraries at import
    time. Missing or mis-versioned native libs surface as ``OSError`` from
    ``cffi.dlopen``, not ``ImportError`` — both are caught so the caller can
    degrade to JSON-only with a ``pdf_skipped`` reason.
    """
    try:
        import markdown as _markdown
        from weasyprint import HTML
    except (ImportError, OSError) as exc:
        raise _MissingPDFDeps(str(exc)) from exc

    md = _format_traceability_matrix_markdown(matrix)
    html_body = _markdown.markdown(md, extensions=["tables", "fenced_code", "toc"])

    css_path = (
        Path(__file__).resolve().parent.parent
        / "dhfkit" / "templates" / "specs" / "styles" / "default.css"
    )
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    full_html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>{html_body}</body></html>"
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=full_html, base_url=str(output.parent)).write_pdf(str(output))
    return output


def _format_traceability_matrix_markdown(matrix: dict) -> str:
    """Render matrix payload as a Markdown traceability matrix document."""
    columns: list[str] = matrix.get("columns") or []
    rows: list[dict] = matrix.get("rows") or []
    coverage: dict[str, list[dict]] = matrix.get("coverage") or {}
    test_results: dict = matrix.get("test_results") or {}

    def _esc(value) -> str:
        if value is None or value == "":
            return "—"
        return str(value).replace("\n", " ").replace("|", r"\|")

    lines: list[str] = []
    lines.append("# Requirements Traceability Matrix")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append(
        "**Trace Path:** " + (" → ".join(columns) if columns else "—")
    )
    lines.append("")

    total_rows = len(rows)
    complete_rows = sum(
        1 for row in rows if columns and all(row.get(c) for c in columns)
    )
    pct = round((complete_rows / total_rows) * 100, 1) if total_rows else 0.0
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total chains:** {total_rows}")
    lines.append(f"- **Complete chains:** {complete_rows} ({pct}%)")
    lines.append(f"- **Incomplete chains:** {total_rows - complete_rows}")
    lines.append("")

    lines.append("## Matrix")
    lines.append("")
    if columns and rows:
        lines.append("| # | " + " | ".join(columns) + " | Status |")
        lines.append("|---|" + "|".join(["---"] * len(columns)) + "|---|")
        for idx, row in enumerate(rows, 1):
            cells = [_esc(row.get(col)) for col in columns]
            status = (
                row.get("verification_status")
                or (row.get("level_statuses") or {}).get(columns[-1], "")
                or "—"
            )
            lines.append(
                f"| {idx} | " + " | ".join(cells) + f" | {_esc(status)} |"
            )
    else:
        lines.append("_No traceability data available._")
    lines.append("")

    if coverage:
        lines.append("## Coverage by Level")
        lines.append("")
        for level in sorted(coverage.keys()):
            items = coverage[level]
            verified = sum(1 for it in items if it.get("status") == "verified")
            pct_l = round((verified / len(items)) * 100, 1) if items else 0.0
            lines.append(f"### {level}")
            lines.append("")
            lines.append(f"- **Total:** {len(items)}")
            lines.append(f"- **Verified:** {verified} ({pct_l}%)")
            lines.append("")
            lines.append("| ID | Title | Status | Tests |")
            lines.append("|---|---|---|---|")
            for it in items:
                # MedHarnessCore.inject_junit_results stores each test as a
                # dict {"name", "status"}; legacy callers may pass plain
                # strings. Handle both.
                test_labels = []
                for t in it.get("tests") or []:
                    if isinstance(t, dict):
                        name = t.get("name") or t.get("id") or ""
                        status = t.get("status") or ""
                        test_labels.append(
                            f"{name} [{status}]" if (name and status) else (name or status)
                        )
                    else:
                        test_labels.append(str(t))
                tests = ", ".join(label for label in test_labels if label) or "—"
                lines.append(
                    f"| {_esc(it.get('id'))} | {_esc(it.get('title') or '')} "
                    f"| {_esc(it.get('status', 'not_verified'))} | {_esc(tests)} |"
                )
            lines.append("")

    if test_results:
        passed = sum(1 for r in test_results.values() if r.get("testing_status") == "PASS")
        failed = sum(1 for r in test_results.values() if r.get("testing_status") == "FAIL")
        skipped = sum(1 for r in test_results.values() if r.get("testing_status") == "SKIP")
        lines.append("## Test Results")
        lines.append("")
        lines.append(f"- **Total:** {len(test_results)}")
        lines.append(f"- **Passed:** {passed}")
        lines.append(f"- **Failed:** {failed}")
        lines.append(f"- **Skipped:** {skipped}")
        lines.append("")

    lines.append("## Compliance References")
    lines.append("")
    lines.append("- IEC 62304 §5.1.1 (Requirements Specification)")
    lines.append("- IEC 62304 §5.1.3 (Requirements Traceability)")
    lines.append("- IEC 62304 §5.5–5.6 (Verification)")
    lines.append("- IEC 62304 §5.7 (System Testing)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Generated by MedHarness*")
    return "\n".join(lines)



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
        from dhfkit.local_adapter import LocalDHFAdapter
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