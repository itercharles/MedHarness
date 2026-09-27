from __future__ import annotations

"""Shared CLI helpers."""
import json
from datetime import datetime
from pathlib import Path
import click


def _make_adapter(dhf_path: Path):
    from dhfkit.local_adapter import LocalDHFAdapter

    return LocalDHFAdapter(dhf_path)


DEFAULT_TRACEABILITY_DOC_TYPES = ("UC", "CRS", "SYS", "SRS", "SWDD")


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
            # rsplit matches dhfkit's Item.prefix: a doc type may configure a
            # multi-segment prefix such as TC-VER-, which split()[0] reduces
            # to "TC-" and no lookup then matches.
            prefix = item_id.rsplit("-", 1)[0] + "-"
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
            # rsplit matches dhfkit's Item.prefix: a doc type may configure a
            # multi-segment prefix such as TC-VER-, which split()[0] reduces
            # to "TC-" and no lookup then matches.
            prefix = item_id.rsplit("-", 1)[0] + "-"
            cfg = core._adapter.get_item_type(prefix)
            if not cfg or not cfg.get("has_verification"):
                continue
            item = core.get_item(item_id)
            if not item:
                continue
            test_cases = item.get("test_cases") or []
            # Group by the resolved doc-type code so the key matches the matrix
            # columns. Deriving it from the ID guesses wrong for any multi-segment
            # prefix, in either split direction.
            coverage.setdefault(cfg.get("code") or item_id.rsplit("-", 1)[0], []).append({
                "id": item_id,
                "title": item.get("title", ""),
                "status": item.get("verification_status", "not_verified"),
                "tests": test_cases,
            })

    for level in coverage:
        coverage[level].sort(key=lambda x: x["id"])

    matrix["coverage"] = coverage
    return matrix


class _MissingPDFDeps(RuntimeError):
    """Raised when WeasyPrint or its native libraries are not available."""


def _write_traceability_report(core, doc_types: tuple[str, ...], output: Path,
                                junit_paths: tuple[str, ...] = ()) -> dict:
    matrix = _build_traceability_report_payload(core, doc_types, junit_paths)
    output.parent.mkdir(parents=True, exist_ok=True)

    json_output = output.with_suffix(".json")
    json_output.write_text(json.dumps(matrix, indent=2), encoding="utf-8")

    result: dict = {
        "path": str(json_output),
        "json_path": str(json_output),
        "rows": len(matrix["rows"]),
    }

    if output.suffix.lower() in (".pdf", ".html"):
        try:
            rendered = _render_traceability_matrix(matrix, output)
        except _MissingPDFDeps as exc:
            result["pdf_skipped"] = str(exc)
        else:
            result["path"] = str(rendered)
            result[f"{output.suffix.lower()[1:]}_path"] = str(rendered)

    return result


def _render_traceability_matrix(matrix: dict, output: Path) -> Path:
    """Render the matrix to ``output`` as HTML, or as PDF when it ends in .pdf.

    PDF needs WeasyPrint and its native libraries; when either is missing the
    caller degrades to the JSON matrix with a ``pdf_skipped`` reason.
    """
    import markdown as _markdown

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
    if output.suffix.lower() != ".pdf":
        output.write_text(full_html, encoding="utf-8")
        return output
    try:
        from dhfkit.document_generation import load_weasyprint
        HTML = load_weasyprint()
    except (ImportError, OSError) as exc:
        raise _MissingPDFDeps(str(exc)) from exc
    HTML(string=full_html, base_url=str(output.parent)).write_pdf(str(output))
    return output


def _format_traceability_matrix_markdown(matrix: dict) -> str:
    """Render matrix payload as a Markdown traceability matrix document."""
    columns: list[str] = matrix.get("columns") or []
    rows: list[dict] = matrix.get("rows") or []
    coverage: dict[str, list[dict]] = matrix.get("coverage") or {}

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
                                      doc_types: tuple[str, ...],
                                      doc_format: str = "html") -> list[dict]:
    # Rendered straight into out_dir: evidence is a copy of the DHF's state,
    # and producing it must not change the DHF.
    spec_dir = out_dir / "specifications"
    generated = []
    for doc_type in doc_types:
        try:
            generated.append(adapter.render_spec(doc_type, doc_format, spec_dir))
        except RuntimeError as exc:
            # Renderer unavailable (e.g. PDF without native libs) — the message
            # already says what to install, so present it rather than traceback.
            raise click.ClickException(str(exc)) from exc
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
    doc_format: str = "html",
) -> dict:
    selected_doc_types = doc_types or tuple(_available_doc_types(adapter))
    selected_traceability = traceability_types or DEFAULT_TRACEABILITY_DOC_TYPES

    out_dir.mkdir(parents=True, exist_ok=True)
    specifications = _generate_specification_artifacts(
        adapter, out_dir, selected_doc_types, doc_format
    )
    plans = [] if skip_plans else _generate_plan_artifacts(dhf_path, out_dir, doc_format)
    traceability = _write_traceability_report(
        core,
        selected_traceability,
        out_dir / "traceability" / f"Requirements_Traceability_Report.{doc_format}",
        [str(path) for path in junit_paths],
    )
    return {
        "out_dir": str(out_dir),
        "specifications": specifications,
        "plans": plans,
        "traceability": traceability,
        "junit_files": [str(path) for path in junit_paths],
    }


def _generate_plan_artifacts(dhf_path: Path, out_dir: Path,
                             doc_format: str = "html") -> list[dict]:
    from dhfkit.local_adapter import LocalDHFAdapter

    # The plans are records: the store lists them and hands over their text.
    # Only the output directory below is this command's own.
    adapter = LocalDHFAdapter(dhf_path)
    plan_ids = sorted(adapter.list_documents("plans"))
    if not plan_ids:
        return []
    try:
        import markdown as _markdown
    except ImportError as exc:
        raise click.ClickException(
            "The 'markdown' package is required to generate plan artifacts."
        ) from exc

    render_pdf = None
    if doc_format == "pdf":
        try:
            from dhfkit.document_generation import load_weasyprint
            render_pdf = load_weasyprint()
        except (ImportError, OSError) as exc:
            # WeasyPrint imports cleanly but raises OSError when its native
            # cairo/pango libraries are absent, so both cases land here.
            raise click.ClickException(
                f"PDF plan artifacts need medharness[docs] plus native "
                f"cairo/pango libraries: {exc}. Use --doc-format html instead."
            ) from exc

    # The stylesheet is a document too, and its location has moved between
    # scaffold versions — asking by name finds it wherever it now lives.
    css_text = adapter.get_document("default") or ""
    css = f"<style>{css_text}</style>" if css_text else ""

    output_dir = out_dir / "plans"
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []
    for plan_id in plan_ids:
        source = adapter.document_path(plan_id)
        html = _markdown.markdown(
            adapter.get_document(plan_id) or "",
            extensions=["tables", "fenced_code", "toc"],
        )
        document = (
            f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"{css}</head><body>{html}</body></html>"
        )
        output = output_dir / f"{plan_id}.{doc_format}"
        if render_pdf is not None:
            base = str(source.parent) if source else str(dhf_path)
            render_pdf(string=document, base_url=base).write_pdf(str(output))
        else:
            output.write_text(document, encoding="utf-8")
        generated.append({"source": str(source or plan_id), "path": str(output)})
    return generated


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------
