"""The files `build release` bundles: specifications, plans, the traceability report."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from medharness.services import git
from medharness.services.traceability import coverage_matrices



class _MissingPDFDeps(RuntimeError):
    """Raised when WeasyPrint or its native libraries are not available."""


def write_traceability_report(adapter, doc_types: tuple[str, ...], output: Path,
                                junit_paths: tuple[str, ...] = ()) -> dict:
    from medharness.services.traceability_report import traceability_report

    matrix = traceability_report(adapter.list_items(), adapter.list_item_types(),
                                 list(doc_types), adapter.config, [Path(p) for p in junit_paths])
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

    md = format_traceability_matrix_markdown(matrix)
    html_body = _markdown.markdown(md, extensions=["tables", "fenced_code", "toc"])
    css_path = (
        Path(__file__).resolve().parents[2]
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


def format_traceability_matrix_markdown(matrix: dict) -> str:
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
                tests = ", ".join(
                    f"{t['name']} [{t['status']}]" for t in it.get("tests") or []
                ) or "—"
                lines.append(
                    f"| {_esc(it.get('id'))} | {_esc(it.get('title') or '')} "
                    f"| {_esc(it.get('status', 'not_verified'))} | {_esc(tests)} |"
                )
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by MedHarness*")
    return "\n".join(lines)


def _generate_specification_artifacts(adapter, out_dir: Path,
                                      doc_types: tuple[str, ...],
                                      doc_format: str, version: str) -> list[dict]:
    # Rendered straight into out_dir: evidence is a copy of the DHF's state,
    # and producing it must not change the DHF.
    spec_dir = out_dir / "specifications"
    generated = []
    for doc_type in doc_types:
        try:
            generated.append(adapter.render_spec(doc_type, doc_format, spec_dir, version))
        except RuntimeError as exc:
            # Renderer unavailable (e.g. PDF without native libs) — the message
            # already says what to install, so present it rather than traceback.
            raise click.ClickException(str(exc)) from exc
    return generated


def generate_release_artifacts(
    adapter,
    out_dir: Path,
    junit_paths: list[Path],
    version: str,
    doc_format: str = "html",
) -> dict:
    """Every specification, every plan, and a traceability report per configured matrix, into out_dir.

    The first matrix keeps the name `Requirements_Traceability_Report`; the others
    are named for their matrix. A release that shipped only the first left the
    risk-to-control chain out of its own evidence.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    specifications = _generate_specification_artifacts(
        adapter, out_dir, tuple(sorted(adapter.get_available_doc_types())), doc_format, version
    )
    plans = _generate_plan_artifacts(adapter, out_dir, doc_format)
    traceability = [
        write_traceability_report(
            adapter,
            tuple(matrix.path),
            out_dir / "traceability" / f"{_report_stem(matrix.name, first=index == 0)}.{doc_format}",
            [str(path) for path in junit_paths],
        )
        for index, matrix in enumerate(coverage_matrices(adapter.config))
    ]
    return {
        "out_dir": str(out_dir),
        "specifications": specifications,
        "plans": plans,
        "traceability": traceability,
        "junit_files": [str(path) for path in junit_paths],
    }


def _report_stem(matrix_name: str, *, first: bool) -> str:
    if first:
        return "Requirements_Traceability_Report"
    return re.sub(r"[^A-Za-z0-9]+", "_", matrix_name).strip("_") + "_Traceability_Report"


def _generate_plan_artifacts(adapter, out_dir: Path, doc_format: str = "html") -> list[dict]:
    # The plans are records: the store lists them and hands over their text.
    # Only the output directory below is this command's own.
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
            render_pdf(string=document, base_url=str(source.parent)).write_pdf(str(output))
        else:
            output.write_text(document, encoding="utf-8")
        generated.append({"source": str(source or plan_id), "path": str(output)})
    return generated


def build_evidence_bundle(
    dhf_path: Path,
    out_dir: Path,
    *,
    version: str,
    junit_paths: list[Path] = (),
    doc_format: str = "html",
    gate: dict,
) -> dict[str, Any]:
    """Write the specifications, traceability and test evidence, then a manifest.

    Records the gate it is given rather than running its own. The manifest
    hashes every file in ``out_dir``, so whatever was written there before this
    runs is covered too. Returns the manifest.
    """
    from dhfkit.store import open_store

    adapter = open_store(dhf_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = generate_release_artifacts(
        adapter, out_dir, list(junit_paths), version,
        doc_format=doc_format,
    )

    provenance = {
        "commit_sha": git.head(dhf_path.resolve().parent) or "",
        "dhf_root": str(dhf_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_passed": gate["passed"],
    }
    (out_dir / "evidence-summary.json").write_text(
        json.dumps({**provenance, "gate": gate, "artifacts": artifacts},
                   indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    files: list[dict] = []
    for candidate in sorted(out_dir.rglob("*")):
        if not candidate.is_file() or candidate.name.startswith("."):
            continue
        files.append({
            "path": str(candidate.relative_to(out_dir)),
            "size": candidate.stat().st_size,
            "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        })
    manifest = {**provenance, "files": files}
    (out_dir / "evidence-manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest
