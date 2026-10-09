"""Everything one release needs, built in one pass — IEC 62304 §9.

`build_release` runs the checks (`services/verify_release.py` and the other
`verify_*` gates), writes the baseline, the software BOM, the SBOM and the
evidence bundle — specifications, plans, traceability reports, a hashed
manifest — to one directory, and, only when all of that passed, records the
REL item. What makes a release unfit is judged in `verify_release`; this module
only builds.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import click

from dhfkit.store import open_store
from medharness.services import git
from medharness.services.soup_sync import _KNOWN_MANIFESTS, _dispatch_parser
from medharness.services.traceability import coverage_matrices
from medharness.services.verify_release import (
    RELEASABLE_STATE,
    known_anomalies,
    still_closed,
    unreleasable_crs,
)


# ---------------------------------------------------------------------------
# Evidence files: specifications, plans, traceability reports, the manifest
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Baseline, BOM, release notes and the REL record
# ---------------------------------------------------------------------------

def _auto_collect_crs(dhf: Path) -> list[str]:
    """Return IDs of completed CRs not already referenced in a REL item."""
    released_crs: set[str] = set()
    completed_unreleased: list[str] = []

    for item in open_store(dhf).list_items():
        item_type = item.get("type")
        if item_type == "REL":
            for cr_id in item.get("included_items") or []:
                released_crs.add(cr_id)
        elif item_type == "CR":
            state = item.get("status") or ""
            if state == RELEASABLE_STATE:
                completed_unreleased.append(item["id"])

    return sorted(uid for uid in completed_unreleased if uid not in released_crs)


# ---------------------------------------------------------------------------
# BOM collection
# ---------------------------------------------------------------------------

def _collect_bom(dhf: Path, manifest_paths: list[Path]) -> tuple[dict, list[str]]:
    """Collect SOUP items and manifest packages into a software BOM.

    Returns ``(bom_dict, errors)`` where errors is non-empty when any manifest
    is unreadable or unsupported — callers must propagate these to avoid
    producing an incomplete BOM that silently looks successful.
    """
    bom_errors: list[str] = []

    dhf_soup: list[dict] = []
    for item in open_store(dhf).list_items():
        if item.get("type") == "SOUP":
            dhf_soup.append({
                # Items expose "id"; keep the artifact key as "uid" so existing
                # release-baseline.json consumers are unaffected.
                "uid": item["id"],
                "name": item.get("name", ""),
                "version": item.get("version", ""),
                "manufacturer": item.get("manufacturer", ""),
                "license": item.get("license", ""),
                "safety_class": item.get("safety_class", ""),
            })

    manifest_packages: list[dict] = []
    for path in manifest_paths:
        # Support is decided by filename, not by catching the parser's error:
        # a malformed package.json raises JSONDecodeError, which is a ValueError,
        # and reporting that as "unsupported format" would send a reader looking
        # for the wrong problem.
        if path.name not in _KNOWN_MANIFESTS:
            bom_errors.append(f"Unsupported manifest format for BOM: {path}")
            continue
        try:
            # The same dispatch `build soup` uses. This listed requirements.txt and
            # package.json by hand and failed the whole baseline on the other
            # seven formats `build soup` reads — a project on a lockfile could sync
            # its SOUP register and then not build a release from it.
            manifest_packages.extend(_dispatch_parser(path))
        except Exception as exc:  # noqa: BLE001
            bom_errors.append(f"Failed to parse BOM manifest {path}: {exc}")

    return {"dhf_soup": dhf_soup, "manifest_packages": manifest_packages}, bom_errors


# ---------------------------------------------------------------------------
# Release notes generation
# ---------------------------------------------------------------------------

def _generate_release_notes(
    version: str,
    cr_ids: list[str],
    bom: dict,
    dhf: Path,
) -> str:
    lines: list[str] = [f"# Release {version}", ""]

    if cr_ids:
        lines.append("## Included Change Requests")
        for cr_id in sorted(cr_ids):
            item = open_store(dhf).get_item(cr_id)
            title = item.get("title", "") if item else ""
            lines.append(f"- {cr_id}: {title}")
        lines.append("")

    soup_count = len(bom.get("dhf_soup") or [])
    if soup_count:
        lines.append("## Software BOM")
        lines.append(f"{soup_count} SOUP component(s) in DHF — see software-bom.json for details.")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def _refused(version: str, cr_ids: list[str], errors: list[str],
             known_anomalies: list[dict] = ()) -> dict:
    """The baseline of a release that failed a gate before anything was written."""
    return {
        "outcome": "completed_with_errors",
        "version": version,
        "cr_ids": sorted(cr_ids),
        "known_anomalies": list(known_anomalies),
        "release_notes": "",
        "artifacts": [],
        "soup_count": 0,
        "manifest_packages_count": 0,
        "errors": errors,
        "warnings": [],
    }


def build_release_baseline(
    dhf: Path,
    version: str,
    manifest_paths: list[Path],
    cr_ids: list[str],
    out_dir: Path,
) -> dict:
    """Check the CRs and anomalies, and write the baseline and BOM artifacts."""
    errors: list[str] = []
    warnings: list[str] = []

    # Auto-collect CRs if none provided
    if not cr_ids:
        cr_ids = _auto_collect_crs(dhf)

    # Gate: all CRs must be completed
    gate_violations = unreleasable_crs(dhf, cr_ids)
    for v in gate_violations:
        errors.append(f"{v['cr']}: {v['issue']}")

    if gate_violations:
        return _refused(version, cr_ids, errors)

    # Gate: unresolved defects must each carry an assessment (§9.7)
    anomalies, anomaly_errors = known_anomalies(dhf)
    errors.extend(anomaly_errors)
    if anomaly_errors:
        return _refused(version, cr_ids, errors, anomalies)

    # Collect BOM — propagate any manifest errors so an incomplete BOM fails loudly
    bom, bom_errors = _collect_bom(dhf, manifest_paths)
    errors.extend(bom_errors)

    # Generate release notes
    release_notes = _generate_release_notes(version, cr_ids, bom, dhf)

    soup_count = len(bom.get("dhf_soup") or [])
    manifest_packages_count = len(bom.get("manifest_packages") or [])

    # Build baseline record
    baseline = {
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "included_crs": sorted(cr_ids),
        "soup_count": soup_count,
        "manifest_packages_count": manifest_packages_count,
        "known_anomalies": anomalies,
        "release_notes": release_notes,
    }

    bom_record = {
        "version": version,
        "generated_at": baseline["generated_at"],
        "dhf_soup": bom["dhf_soup"],
        "manifest_packages": bom["manifest_packages"],
    }

    # Write artifacts
    artifacts: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        baseline_path = out_dir / "release-baseline.json"
        baseline_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        artifacts.append(str(baseline_path))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Failed to write release-baseline.json: {exc}")

    try:
        bom_path = out_dir / "software-bom.json"
        bom_path.write_text(json.dumps(bom_record, indent=2), encoding="utf-8")
        artifacts.append(str(bom_path))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Failed to write software-bom.json: {exc}")

    # The same components in the format a regulator asks for. software-bom.json
    # is dhfkit's own shape and stays as it is; this is the CycloneDX view of
    # the release, which is what FDA cybersecurity guidance and the EU CRA want.
    try:
        from importlib.metadata import version as pkg_version

        from dhfkit.sbom import build_sbom, merge_release_components, purl_gap, write_sbom

        soup_items = [i for i in open_store(dhf).list_items() if i.get("type") == "SOUP"]
        components = merge_release_components(soup_items, bom["manifest_packages"])
        try:
            tool_version = pkg_version("medharness")
        except Exception:  # noqa: BLE001
            tool_version = "unknown"
        try:
            project_name = open_store(dhf).config.project_name
        except Exception:  # noqa: BLE001
            # Cosmetic metadata. It must not turn a successful release into
            # completed_with_errors — a name the SBOM cannot read is not a
            # reason to fail the baseline.
            project_name = dhf.resolve().parent.name
        document = build_sbom(
            components, project_name=project_name, tool_version=tool_version,
        )
        sbom_path, _changed = write_sbom(document, out_dir / "sbom.cdx.json")
        artifacts.append(str(sbom_path))
        # A component with no purl is one a consumer of the SBOM cannot resolve;
        # the two causes need different fixes, so each is named.
        for component in document["components"]:
            if "purl" not in component:
                props = {p["name"]: p["value"] for p in component.get("properties", [])}
                reason = purl_gap(component["name"], component["version"],
                                  props.get("dhfkit:ecosystem", ""))
                warnings.append(f"{component['bom-ref']}: no purl in the SBOM — {reason}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Failed to write sbom.cdx.json: {exc}")

    return {
        "outcome": "completed_with_errors" if errors else "completed",
        "version": version,
        "cr_ids": sorted(cr_ids),
        "known_anomalies": anomalies,
        "release_notes": release_notes,
        "artifacts": artifacts,
        "soup_count": soup_count,
        "manifest_packages_count": manifest_packages_count,
        "errors": errors,
        "warnings": warnings,
    }


def record_release(dhf: Path, baseline: dict) -> str:
    """Create the REL item for a baseline that passed. Returns its ID."""
    item = open_store(dhf).create_item({
        "type": "REL",
        "version": baseline["version"],
        "included_items": baseline["cr_ids"],
        # §9.7: the anomalies this release ships with, carried on the record
        # rather than only in the generated artifact.
        "known_anomalies": baseline["known_anomalies"],
        "release_notes": baseline["release_notes"],
    })
    return item["id"]


def build_release(
    dhf: Path,
    version: str,
    out_dir: Path,
    *,
    manifest_paths: list[Path] = (),
    cr_ids: list[str] = (),
    junit_paths: list[Path] = (),
    doc_format: str = "html",
    write: bool = False,
) -> dict:
    """Check, build and optionally record one release.

    The DHF is checked by `verify dhf`'s own gate with coverage gaps failing: a
    release is not the place for advisory findings, and a second definition of
    "the DHF is sound" is how two gates came to disagree before.
    """
    from medharness.services.verify_dhf import ci_structural_gate

    gate = ci_structural_gate(dhf, strict=True)
    baseline = build_release_baseline(dhf, version, list(manifest_paths), list(cr_ids), out_dir)
    # Last, so its manifest hashes the baseline's files as well as its own.
    manifest = build_evidence_bundle(
        dhf, out_dir, version=version, junit_paths=list(junit_paths), doc_format=doc_format,
        gate=gate,
    )

    closure_errors, closure_warnings = still_closed(dhf, baseline["cr_ids"], list(junit_paths))
    errors = [f"DHF: {e}" for e in gate["errors"]] + baseline["errors"] + closure_errors
    warnings = list(baseline.get("warnings", [])) + closure_warnings
    rel_uid: Optional[str] = None
    if write and not errors:
        try:
            rel_uid = record_release(dhf, baseline)
        except Exception as exc:  # noqa: BLE001
            # The artifacts are written; a REL the store refused is reported,
            # not raised, so the run still says what it produced.
            errors.append(f"Failed to create REL item: {exc}")

    return {
        "outcome": "completed_with_errors" if errors else "completed",
        "version": version,
        "cr_ids": baseline["cr_ids"],
        "rel_uid": rel_uid,
        "soup_count": baseline["soup_count"],
        "artifacts": [f["path"] for f in manifest["files"]],
        "errors": errors,
        "warnings": warnings,
    }
