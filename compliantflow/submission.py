"""510(k) Submission Evidence Package assembler.

Assembles a dated ZIP artifact containing all required compliance evidence
for a 510(k) or CE mark submission. Will not produce a package if any
compliance gate is failing (unless --force is passed).

Artifact structure inside the ZIP:
  cover_document.pdf          — FDA eSTAR section mapping table
  traceability_report.pdf     — full traceability matrix
  compliance_{standard}.pdf   — one per configured standard
  soup_list.pdf               — SOUP items with vulnerability status
  risk_rcm_summary.pdf        — RISK and RCM items
  test_results_summary.pdf    — test result summary
  cr_evidence.pdf             — closed CR history
"""

from __future__ import annotations

import datetime
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Any, Optional

if TYPE_CHECKING:
    from compliantflow.core import CompliantFlowCore


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assemble_submission(
    core: "CompliantFlowCore",
    governance_dir: Path,
    output_dir: Path,
    force: bool = False,
) -> Path:
    """Assemble a submission evidence ZIP.

    Args:
        core:           CompliantFlowCore instance.
        governance_dir: Directory containing governance YAML files.
        output_dir:     Directory where the ZIP will be written.
        force:          If True, skip the completeness gate and assemble anyway.

    Returns:
        Path to the generated ZIP file.

    Raises:
        SubmissionGateError: If any compliance check fails and force=False.
    """
    if not force:
        _run_completeness_gate(core, governance_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    zip_path = output_dir / f"submission_{date_str}.zip"

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _write_traceability_report(core, tmp_path)
        _write_compliance_reports(core, governance_dir, tmp_path)
        _write_soup_list(core, tmp_path)
        _write_risk_rcm_summary(core, tmp_path)
        _write_test_results_summary(core, tmp_path)
        _write_cr_evidence(core, tmp_path)
        _write_cover_document(tmp_path, governance_dir, date_str)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(tmp_path.iterdir()):
                zf.write(f, f.name)

    return zip_path


# ---------------------------------------------------------------------------
# Completeness gate
# ---------------------------------------------------------------------------

class SubmissionGateError(Exception):
    """Raised when one or more compliance checks fail and force=False."""

    def __init__(self, failures: List[Dict[str, Any]]) -> None:
        self.failures = failures
        lines = [f"  - {f['standard']}: {f['passed_policies']}/{f['total_policies']} policies passed"
                 for f in failures]
        super().__init__(
            "Submission package blocked — compliance gate failed:\n" + "\n".join(lines)
        )


def _run_completeness_gate(core: "CompliantFlowCore", governance_dir: Path) -> None:
    """Run compliance checks for all standards; raise SubmissionGateError on any failure."""
    failures: List[Dict[str, Any]] = []
    for gov_file in sorted(governance_dir.glob("*.yaml")):
        group_id = gov_file.stem
        report = core.check_compliance(group_id, governance_dir)
        if report and report.get("passed_policies", 0) < report.get("total_policies", 0):
            failures.append({
                "standard": group_id,
                "passed_policies": report.get("passed_policies", 0),
                "total_policies": report.get("total_policies", 0),
            })
    if failures:
        raise SubmissionGateError(failures)


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------

def _write_traceability_report(core: "CompliantFlowCore", tmp: Path) -> None:
    from compliantflow import report_generator
    matrix = core.build_traceability_matrix(["UC", "CRS", "SYS", "SRS", "SWDD"])
    report_generator.generate_traceability_pdf(matrix, tmp / "traceability_report.pdf")


def _write_compliance_reports(
    core: "CompliantFlowCore", governance_dir: Path, tmp: Path
) -> None:
    from compliantflow import report_generator
    for gov_file in sorted(governance_dir.glob("*.yaml")):
        group_id = gov_file.stem
        report = core.check_compliance(group_id, governance_dir)
        if report:
            report_generator.generate_compliance_pdf(
                report, tmp / f"compliance_{group_id}.pdf"
            )


def _write_soup_list(core: "CompliantFlowCore", tmp: Path) -> None:
    from compliantflow import report_generator
    soup_items = [i for i in core.get_all_items() if i["id"].startswith("SOUP-")]
    html = _soup_html(soup_items)
    report_generator._to_pdf(html, tmp / "soup_list.pdf")


def _write_risk_rcm_summary(core: "CompliantFlowCore", tmp: Path) -> None:
    from compliantflow import report_generator
    all_items = core.get_all_items()
    risks = [i for i in all_items if i["id"].startswith("RISK-")]
    rcms = [i for i in all_items if i["id"].startswith("RCM-")]
    html = _risk_rcm_html(risks, rcms)
    report_generator._to_pdf(html, tmp / "risk_rcm_summary.pdf")


def _write_test_results_summary(core: "CompliantFlowCore", tmp: Path) -> None:
    from compliantflow import report_generator
    results = core.get_all_test_results()
    html = _test_results_html(results)
    report_generator._to_pdf(html, tmp / "test_results_summary.pdf")


def _write_cr_evidence(core: "CompliantFlowCore", tmp: Path) -> None:
    from compliantflow import report_generator
    all_items = core.get_all_items()
    closed_crs = [i for i in all_items if i["id"].startswith("CR-") and i.get("status") == "closed"]
    html = _cr_evidence_html(closed_crs)
    report_generator._to_pdf(html, tmp / "cr_evidence.pdf")


def _write_cover_document(tmp: Path, governance_dir: Path, date_str: str) -> None:
    from compliantflow import report_generator
    standards = [f.stem for f in sorted(governance_dir.glob("*.yaml"))]
    html = _cover_html(standards, date_str)
    report_generator._to_pdf(html, tmp / "cover_document.pdf")


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

_CSS = """
    body { font-family: Arial, sans-serif; font-size: 10px; color: #222; margin: 20mm; }
    h1   { font-size: 16px; margin-bottom: 4px; }
    h2   { font-size: 12px; margin-top: 16px; margin-bottom: 4px;
           border-bottom: 1px solid #ccc; padding-bottom: 2px; }
    .meta { font-size: 9px; color: #666; margin-bottom: 12px; }
    table { border-collapse: collapse; width: 100%; margin-top: 6px; }
    th    { background: #2c5f8a; color: white; padding: 5px 6px;
            text-align: left; font-size: 9px; }
    td    { padding: 4px 6px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
    tr:nth-child(even) td { background: #f7f9fb; }
    .pass { color: #1a7a3c; font-weight: bold; }
    .fail { color: #b91c1c; font-weight: bold; }
    .warn { color: #b45309; font-weight: bold; }
    .summary { margin: 8px 0 14px 0; padding: 8px 12px; background: #f0f4f8;
               border-left: 4px solid #2c5f8a; font-size: 10px; }
"""

_TIMESTAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _cover_html(standards: List[str], date_str: str) -> str:
    # FDA eSTAR section mapping
    rows = [
        ("Software Description", "Traceability matrix showing UC→CRS→SYS→SRS→SWDD chain", "traceability_report.pdf"),
        ("Software Safety Classification", "IEC 62304 compliance evidence", "compliance_IEC_62304.pdf"),
        ("Risk Management", "ISO 14971 compliance evidence + RISK/RCM item summary", "compliance_ISO_14971.pdf, risk_rcm_summary.pdf"),
        ("SOUP Documentation", "SOUP items with OSV vulnerability status", "soup_list.pdf"),
        ("Software Testing", "Test result summary with pass/fail by test case", "test_results_summary.pdf"),
        ("Change Management", "Closed CR history with linked implementation commits", "cr_evidence.pdf"),
    ]
    # Add any extra standards
    extra = [s for s in standards if s not in ("IEC_62304", "ISO_14971")]
    for s in extra:
        rows.append((f"Additional Standard: {s}", f"{s} compliance evidence", f"compliance_{s}.pdf"))

    tbody = "".join(
        f"<tr><td>{section}</td><td>{desc}</td><td><code>{files}</code></td></tr>"
        for section, desc, files in rows
    )
    return f"""<html><head><style>{_CSS}</style></head><body>
    <h1>510(k) Submission Evidence Package — Cover Document</h1>
    <div class="meta">Generated: {_TIMESTAMP} &nbsp;|&nbsp; Submission date: {date_str}</div>
    <p>This package was assembled by CompliantFlow from the Design History File.
    Each artifact below corresponds to an FDA eSTAR submission section.</p>
    <table>
      <tr><th>FDA eSTAR Section</th><th>Content</th><th>File(s)</th></tr>
      {tbody}
    </table>
    </body></html>"""


def _soup_html(soup_items: List[Dict[str, Any]]) -> str:
    if not soup_items:
        body = "<p>No SOUP items found in DHF.</p>"
    else:
        rows = "".join(
            f"<tr><td>{i['id']}</td><td>{i.get('title','')}</td>"
            f"<td>{i.get('name','')}</td><td>{i.get('version','')}</td>"
            f"<td>{i.get('vulnerability_status') or '—'}</td></tr>"
            for i in soup_items
        )
        body = f"""<table>
          <tr><th>ID</th><th>Title</th><th>Package</th><th>Version</th><th>Vulnerability Status</th></tr>
          {rows}
        </table>"""
    return f"""<html><head><style>{_CSS}</style></head><body>
    <h1>SOUP List</h1>
    <div class="meta">Generated: {_TIMESTAMP}</div>
    {body}
    </body></html>"""


def _risk_rcm_html(risks: List[Dict[str, Any]], rcms: List[Dict[str, Any]]) -> str:
    def _rows(items: List[Dict[str, Any]], cols: List[str]) -> str:
        return "".join(
            "<tr>" + "".join(f"<td>{i.get(c, '—')}</td>" for c in cols) + "</tr>"
            for i in items
        )

    risk_rows = _rows(risks, ["id", "title", "severity", "probability", "risk_level"])
    rcm_rows = _rows(rcms, ["id", "title", "implementation_status", "verification_status"])
    return f"""<html><head><style>{_CSS}</style></head><body>
    <h1>Risk &amp; Risk Control Measure Summary</h1>
    <div class="meta">Generated: {_TIMESTAMP}</div>
    <h2>RISK Items ({len(risks)})</h2>
    <table>
      <tr><th>ID</th><th>Title</th><th>Severity</th><th>Probability</th><th>Risk Level</th></tr>
      {risk_rows if risks else '<tr><td colspan="5">No RISK items found.</td></tr>'}
    </table>
    <h2>Risk Control Measures ({len(rcms)})</h2>
    <table>
      <tr><th>ID</th><th>Title</th><th>Implementation Status</th><th>Verification Status</th></tr>
      {rcm_rows if rcms else '<tr><td colspan="4">No RCM items found.</td></tr>'}
    </table>
    </body></html>"""


def _test_results_html(results: Dict[str, Any]) -> str:
    items = list(results.values()) if isinstance(results, dict) else (results or [])
    passed = sum(1 for r in items if r.get("status") == "PASS")
    failed = sum(1 for r in items if r.get("status") == "FAIL")
    rows = "".join(
        f"<tr><td>{r.get('id') or r.get('tc_id','')}</td>"
        f"<td>{r.get('title','')}</td>"
        f"<td class=\"{'pass' if r.get('status')=='PASS' else 'fail'}\">{r.get('status','')}</td>"
        f"<td>{r.get('run_id','')}</td></tr>"
        for r in items
    )
    return f"""<html><head><style>{_CSS}</style></head><body>
    <h1>Test Results Summary</h1>
    <div class="meta">Generated: {_TIMESTAMP}</div>
    <div class="summary">
      Total: <b>{len(items)}</b> &nbsp;|&nbsp;
      <span class="pass">PASS: {passed}</span> &nbsp;|&nbsp;
      <span class="fail">FAIL: {failed}</span>
    </div>
    <table>
      <tr><th>TC ID</th><th>Title</th><th>Status</th><th>Run ID</th></tr>
      {rows if items else '<tr><td colspan="4">No test results found.</td></tr>'}
    </table>
    </body></html>"""


def _cr_evidence_html(closed_crs: List[Dict[str, Any]]) -> str:
    rows = "".join(
        f"<tr><td>{cr['id']}</td><td>{cr.get('title','')}</td>"
        f"<td>{', '.join(cr.get('affected_items') or [])}</td>"
        f"<td>{', '.join(cr.get('implementation_prs') or [])}</td></tr>"
        for cr in closed_crs
    )
    return f"""<html><head><style>{_CSS}</style></head><body>
    <h1>CR Evidence Report</h1>
    <div class="meta">Generated: {_TIMESTAMP} &nbsp;|&nbsp; {len(closed_crs)} closed CR(s)</div>
    <table>
      <tr><th>CR ID</th><th>Title</th><th>Affected Items</th><th>Implementation PRs</th></tr>
      {rows if closed_crs else '<tr><td colspan="4">No closed CRs found.</td></tr>'}
    </table>
    </body></html>"""
