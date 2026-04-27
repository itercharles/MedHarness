"""PDF report generation for traceability and compliance evidence."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Dict, Any, List


def escapeXml(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_traceability_pdf(matrix: Dict[str, Any], output_path: Path) -> None:
    """Render a traceability matrix as a PDF."""
    html = _traceability_html(matrix)
    _to_pdf(html, output_path)


def generate_compliance_pdf(report: Dict[str, Any], output_path: Path) -> None:
    """Render a compliance report as a PDF."""
    html = _compliance_html(report)
    _to_pdf(html, output_path)


def generate_compliance_json(report: Dict[str, Any], output_path: Path) -> None:
    """Write a compliance report as a versioned JSON file for programmatic consumption."""
    import json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, default=str, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

_CSS = """
    body { font-family: Arial, sans-serif; font-size: 10px; color: #222; margin: 20mm; }
    h1   { font-size: 16px; margin-bottom: 4px; }
    h2   { font-size: 12px; margin-top: 16px; margin-bottom: 4px; border-bottom: 1px solid #ccc; padding-bottom: 2px; }
    .meta { font-size: 9px; color: #666; margin-bottom: 12px; }
    table { border-collapse: collapse; width: 100%; margin-top: 6px; }
    th    { background: #2c5f8a; color: white; padding: 5px 6px; text-align: left; font-size: 9px; }
    td    { padding: 4px 6px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
    tr:nth-child(even) td { background: #f7f9fb; }
    .pass { color: #1a7a3c; font-weight: bold; }
    .fail { color: #b91c1c; font-weight: bold; }
    .warn { color: #b45309; font-weight: bold; }
    .orphan td { background: #fff8e1 !important; }
    .incomplete td { background: #fde8e8 !important; }
    .summary { margin: 8px 0 14px 0; padding: 8px 12px; background: #f0f4f8;
               border-left: 4px solid #2c5f8a; font-size: 10px; }
    .summary b { font-size: 13px; }
"""

_TIMESTAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _vs_badge(vs: str) -> str:
    if vs == "verified":
        return '<span class="pass">VERIFIED</span>'
    if vs == "failed":
        return '<span class="fail">FAILED</span>'
    if vs == "not_verified":
        return '<span class="warn">NOT VERIFIED</span>'
    return '<span style="color:#999">—</span>'


def _traceability_html(matrix: Dict[str, Any]) -> str:
    columns: List[str] = matrix["columns"]
    rows: List[Dict] = matrix["rows"]
    test_results: Dict[str, Any] = matrix.get("test_results") or {}
    coverage: Dict[str, List[Dict]] = matrix.get("coverage") or {}

    total    = len(rows)
    complete = sum(1 for r in rows if r.get("is_complete"))
    orphans  = sum(1 for r in rows if r.get("is_orphan"))
    verified = sum(1 for r in rows if r.get("verification_status") == "verified")
    tc_total = len(test_results)
    tc_pass  = sum(1 for v in test_results.values() if v.get("status") == "PASS")
    tc_fail  = sum(1 for v in test_results.values() if v.get("status") == "FAIL")

    # Count verified items across all coverage levels
    cov_verified = sum(
        1 for items in coverage.values() for item in items
        if item.get("status") == "verified"
    )
    cov_total = sum(len(items) for items in coverage.values())

    col_headers = "".join(f"<th>{c}</th>" for c in columns)
    col_headers += "<th>Traceability</th><th>Test Status</th>"

    body_rows = []
    for r in rows:
        if r.get("is_orphan"):
            css = "orphan"
            trace_status = f'<span class="fail">ORPHAN ({r.get("orphan_type", "")})</span>'
        elif not r.get("is_complete"):
            css = "incomplete"
            trace_status = '<span class="fail">INCOMPLETE</span>'
        else:
            css = ""
            trace_status = '<span class="pass">COMPLETE</span>'

        vs = r.get("verification_status")
        if vs == "failed":
            css = css or "incomplete"
        test_status = _vs_badge(vs or "")

        cells = "".join(f"<td>{r.get(c) or '—'}</td>" for c in columns)
        cells += f"<td>{trace_status}</td><td>{test_status}</td>"
        body_rows.append(f'<tr class="{css}">{cells}</tr>')

    # Per-level test coverage sections
    coverage_sections = ""
    level_labels = {"SRS": "Software Requirements (SRS)", "SYS": "System Requirements (SYS)",
                    "CRS": "Clinical Requirements (CRS)", "UC": "Use Cases (UC)"}
    for level, items in coverage.items():
        if not items:
            continue
        lv = sum(1 for i in items if i.get("status") == "verified")
        lf = sum(1 for i in items if i.get("status") == "failed")
        label = level_labels.get(level, level)
        cov_rows = []
        for item in items:
            item_id  = item["id"]
            title    = escapeXml(item.get("title", ""))
            vs_badge = _vs_badge(item.get("status", ""))
            tests    = item.get("tests") or []
            if tests:
                test_list = "<ul style='margin:0;padding-left:14px'>" + "".join(
                    f"<li style='color:{'#1a7a3c' if t['status']=='PASS' else '#b91c1c'}'>"
                    f"{escapeXml(t['name'])}</li>"
                    for t in tests
                ) + "</ul>"
            else:
                test_list = '<span style="color:#999">No tests</span>'
            row_css = "" if item.get("status") == "verified" else "incomplete"
            cov_rows.append(
                f"<tr class='{row_css}'>"
                f"<td style='white-space:nowrap;width:8%'>{item_id}</td>"
                f"<td style='width:28%'>{title}</td>"
                f"<td style='white-space:nowrap;width:10%'>{vs_badge}</td>"
                f"<td>{test_list}</td></tr>"
            )
        coverage_sections += f"""
<h2>{label} — Test Coverage ({lv} verified / {lf} failed / {len(items)} total)</h2>
<table>
  <thead><tr>
    <th>ID</th><th>Requirement</th><th>Status</th><th>Tests</th>
  </tr></thead>
  <tbody>{''.join(cov_rows)}</tbody>
</table>"""

    # DHF-stored test results detail section (may be empty when using JUnit-only flow)
    tc_rows = []
    for tc_id, rec in sorted(test_results.items()):
        status = rec.get("status", "")
        ok = status == "PASS"
        status_html = f'<span class="{"pass" if ok else "fail"}">{status}</span>'
        links = ", ".join(rec.get("links") or []) or "—"
        run_id = rec.get("run_id") or "—"
        tc_rows.append(
            f"<tr><td style='white-space:nowrap'>{tc_id}</td>"
            f"<td>{rec.get('title', '')}</td>"
            f"<td style='white-space:nowrap'>{status_html}</td>"
            f"<td>{links}</td>"
            f"<td>{run_id}</td></tr>"
        )

    tc_section = ""
    if tc_rows:
        tc_section = f"""
<h2>Test Results ({tc_pass} pass / {tc_fail} fail / {tc_total} total)</h2>
<table>
  <thead><tr>
    <th style="width:10%">TC ID</th><th style="width:35%">Title</th>
    <th style="width:8%">Status</th><th style="width:30%">Linked Items</th>
    <th>Run ID</th>
  </tr></thead>
  <tbody>{''.join(tc_rows)}</tbody>
</table>"""

    cov_summary = (
        f'&nbsp;&nbsp; <b style="color:#1a7a3c">{cov_verified}/{cov_total}</b> req. verified'
        if cov_total else ""
    )

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{_CSS}</style></head><body>
<h1>Traceability Report</h1>
<div class="meta">Generated: {_TIMESTAMP} &nbsp;|&nbsp; Columns: {' → '.join(columns)}</div>
<div class="summary">
  <b>{complete}/{total}</b> complete &nbsp;&nbsp;
  <b style="color:#b91c1c">{orphans}</b> orphan(s) &nbsp;&nbsp;
  <b style="color:#1a7a3c">{verified}</b> matrix rows verified
  {cov_summary}
</div>
<h2>Traceability Matrix</h2>
<table><thead><tr>{col_headers}</tr></thead>
<tbody>{''.join(body_rows)}</tbody></table>
{coverage_sections}
{tc_section}
</body></html>"""


def _compliance_html(report: Dict[str, Any]) -> str:
    results  = report.get("results", [])
    total    = report.get("total_policies", len(results))
    passed   = report.get("passed_policies", 0)
    failed   = total - passed
    score    = report.get("score", 0.0)
    source   = report.get("source_id", "")

    pass_color = "#1a7a3c" if failed == 0 else "#b91c1c"

    rows = []
    for r in results:
        pid      = r.get("policy_id", "")
        ptext    = r.get("policy_text", "")
        details  = r.get("details", "")
        ok       = r.get("passed", False)
        status   = '<span class="pass">PASS</span>' if ok else '<span class="fail">FAIL</span>'
        rows.append(
            f"<tr><td style='white-space:nowrap'>{pid}</td>"
            f"<td>{ptext}</td>"
            f"<td style='white-space:nowrap'>{status}</td>"
            f"<td>{details}</td></tr>"
        )

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{_CSS}</style></head><body>
<h1>Compliance Report — {source}</h1>
<div class="meta">Generated: {_TIMESTAMP}</div>
<div class="summary">
  Score: <b style="color:{pass_color}">{score:.1f}%</b> &nbsp;&nbsp;
  <b>{passed}</b> passed &nbsp;&nbsp;
  <b style="color:#b91c1c">{failed}</b> failed &nbsp;&nbsp;
  of <b>{total}</b> policies
</div>
<table>
  <thead><tr><th style="width:6%">ID</th><th style="width:45%">Policy</th>
  <th style="width:6%">Result</th><th>Rationale / Details</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>
</body></html>"""


# ---------------------------------------------------------------------------
# PDF conversion
# ---------------------------------------------------------------------------

def _to_pdf(html: str, output_path: Path) -> None:
    from weasyprint import HTML
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(output_path))
