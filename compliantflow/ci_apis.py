"""Reusable CI gate APIs — library functions that CLI commands and tests call.

Each function returns a structured result dict. No print side effects.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DEFAULT_ACCEPTANCE_COVERAGE_PAIRS = ("UC:CRS", "CRS:SYS", "SYS:SRS", "SRS:SWDD")
DEFAULT_TRACEABILITY_DOC_TYPES = ("UC", "CRS", "SYS", "SRS", "SWDD")


# ---------------------------------------------------------------------------
# Shared utility helpers (used by both cli.py and ci_apis.py)
# ---------------------------------------------------------------------------


def _parse_coverage_pairs(pairs: tuple[str, ...]) -> list[tuple[str, str]]:
    parsed = []
    for pair in pairs:
        if ":" not in pair:
            raise ValueError(
                f"invalid pair '{pair}', expected PARENT:CHILD format."
            )
        parent, child = pair.split(":", 1)
        parsed.append((parent.strip(), child.strip()))
    return parsed


def _collect_junit_paths(
    junit_files: tuple[Path, ...] = (),
    junit_dirs: tuple[Path, ...] = (),
) -> list[Path]:
    collected: list[Path] = []
    seen: set[str] = set()

    def _add(p: Path) -> None:
        resolved = str(p.resolve())
        if resolved in seen:
            return
        seen.add(resolved)
        collected.append(p)

    for jf in junit_files:
        if not jf.exists():
            continue
        if not jf.is_file():
            continue
        _add(jf)

    for jd in junit_dirs:
        if not jd.exists() or not jd.is_dir():
            continue
        for xml_path in sorted(jd.rglob("*.xml")):
            if xml_path.is_file():
                _add(xml_path)

    return collected


def _run_acceptance_gate(core, junit_paths: list[Path], coverage_pairs: tuple[str, ...]) -> dict:
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


def _available_doc_types(adapter) -> list[str]:
    if hasattr(adapter, "get_available_doc_types"):
        return sorted(adapter.get_available_doc_types())
    doc_specs = getattr(adapter, "_doc_specs", None)
    if isinstance(doc_specs, dict):
        return sorted(doc_specs.keys())
    raise RuntimeError("Configured DHF adapter does not expose available document types.")


def _generate_specification_artifacts(adapter, out_dir: Path,
                                       doc_types: tuple[str, ...]) -> list[dict]:
    if not hasattr(adapter, "export_pdf"):
        raise RuntimeError("Configured DHF adapter does not support PDF export.")
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


def _generate_plan_artifacts(dhf_path: Path, out_dir: Path) -> list[dict]:
    plans_dir = dhf_path / "documents" / "plans"
    if not plans_dir.is_dir():
        return []
    try:
        import markdown as _markdown
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
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
        tuple(str(path) for path in junit_paths),
    )
    return {
        "out_dir": str(out_dir),
        "specifications": specifications,
        "plans": plans,
        "traceability": traceability,
        "junit_files": [str(path) for path in junit_paths],
    }


# ---------------------------------------------------------------------------
# ci_structural_gate — backs ci dhf-validate
# ---------------------------------------------------------------------------


def ci_structural_gate(
    dhf_path: Path,
    governance_dir: Path | None = None,
    run_schema: bool = True,
    run_traceability: bool = True,
    coverage_pairs: tuple[str, ...] = (),
    fail_on_uncovered: bool = False,
) -> dict[str, Any]:
    """Run the DHF structural validation gate.

    Returns a dict with ``passed`` (bool) and ``results`` keyed by
    ``schema``, ``traceability``, and ``coverage``.  Each result entry
    is a dict with its own ``passed`` and details.
    """
    from dhf_util.local_adapter import LocalDHFAdapter
    from compliantflow.core import CompliantFlowCore

    adapter = LocalDHFAdapter(dhf_path)
    core = CompliantFlowCore(adapter)

    passed = True
    results: dict[str, dict] = {}

    if run_schema:
        r = adapter.validate_schema()
        results["schema"] = {
            "passed": r.get("valid", True),
            "valid": r.get("valid", True),
            "item_count": r.get("item_count", 0),
            "errors": r.get("errors", []),
        }
        if not r.get("valid", True):
            passed = False

    if run_traceability:
        tr = adapter.validate_traceability()
        required = tr.get("required", {})
        coverage_list = tr.get("coverage", [])
        results["traceability"] = {
            "passed": required.get("passed", True)
            and all(c.get("passed", True) for c in coverage_list),
            "required": required,
            "coverage": coverage_list,
            "summary": tr.get("summary", ""),
        }
        if not required.get("passed", True):
            passed = False
        for c in coverage_list:
            if not c.get("passed", True) and fail_on_uncovered:
                passed = False

    if coverage_pairs:
        pairs = _parse_coverage_pairs(coverage_pairs)
        cov = core.check_coverage(pairs)
        cov_passed = cov.get("passed", True)
        if not cov_passed:
            passed = False
        results["coverage"] = {
            "passed": cov_passed,
            "pairs": cov.get("results", []),
        }

    return {"passed": passed, "results": results}


# ---------------------------------------------------------------------------
# ci_compliance_gate — backs ci compliance-check
# ---------------------------------------------------------------------------


def ci_compliance_gate(
    dhf_path: Path,
    governance_dir: Path,
    standards: tuple[str, ...],
    continue_on_error: bool = False,
) -> dict[str, Any]:
    """Run compliance checks for the given standards.

    Returns a dict with ``passed`` (bool) and a ``results`` list of
    per-standard dicts: ``{standard, score, passed_policies, total_policies, failed}``.
    """
    from dhf_util.local_adapter import LocalDHFAdapter
    from compliantflow.core import CompliantFlowCore

    adapter = LocalDHFAdapter(dhf_path)
    core = CompliantFlowCore(adapter)

    passed = True
    reports: list[dict] = []

    for standard in standards:
        gov = governance_dir.resolve() if governance_dir else Path("governance")
        try:
            report = core.check_compliance(standard, str(gov))
        except Exception as exc:
            passed = False
            reports.append({
                "standard": standard,
                "score": 0.0,
                "passed_policies": 0,
                "total_policies": 0,
                "failed": True,
                "error": str(exc),
            })
            if not continue_on_error:
                break
            continue

        if report is None:
            passed = False
            reports.append({
                "standard": standard,
                "score": 0.0,
                "passed_policies": 0,
                "total_policies": 0,
                "failed": True,
                "error": "policy group not found",
            })
            if not continue_on_error:
                break
            continue

        score = report.get("score", 0)
        total = report.get("total_policies", 0)
        passed_count = report.get("passed_policies", 0)
        failed = passed_count < total

        reports.append({
            "standard": standard,
            "score": score,
            "passed_policies": passed_count,
            "total_policies": total,
            "failed": failed,
        })

        if failed:
            passed = False

    return {"passed": passed, "results": reports}


# ---------------------------------------------------------------------------
# ci_test_coverage_gate — backs ci test-coverage
# ---------------------------------------------------------------------------


def ci_test_coverage_gate(
    dhf_path: Path,
    junit_paths: list[Path],
    req_types: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Check that every requirement has test coverage from JUnit evidence.

    Returns a dict with ``passed`` (bool) and a ``results`` list of
    per-type coverage dicts.
    """
    from dhf_util.local_adapter import LocalDHFAdapter

    if not junit_paths:
        return {
            "passed": False,
            "error": "No JUnit files found.",
            "results": [],
        }

    covered_reqs: set[str] = set()
    for jp in junit_paths:
        if not jp.is_file():
            continue
        tree = ET.parse(jp)
        for tc in tree.iter("testcase"):
            failures = list(tc.iter("failure"))
            errors = list(tc.iter("error"))
            skipped = list(tc.iter("skipped"))
            if failures or errors or skipped:
                continue
            for props in tc.iter("properties"):
                for prop in props.iter("property"):
                    if prop.get("name") == "compliantflow.links":
                        value = prop.get("value", "")
                        if value:
                            covered_reqs.update(
                                v.strip() for v in value.split(",") if v.strip()
                            )
                        break

    adapter = LocalDHFAdapter(dhf_path)
    all_items = adapter.list_items()

    passed = True
    results: list[dict] = []
    default_types = req_types if req_types else ("SRS", "SYS", "CRS")

    for rt in default_types:
        config = adapter._config
        dt = config.get_doc_type(rt)
        if not dt:
            results.append({
                "type": rt,
                "passed": True,
                "covered": 0,
                "total": 0,
                "uncovered": [],
                "warning": f"Unknown requirement type",
            })
            continue
        prefix = dt.prefix
        req_items = [it for it in all_items if it["id"].startswith(prefix)]
        if not req_items:
            continue
        covered_count = 0
        uncovered: list[str] = []
        for ri in req_items:
            if ri["id"] in covered_reqs:
                covered_count += 1
            else:
                uncovered.append(ri["id"])
        total = len(req_items)
        type_passed = covered_count == total
        if not type_passed:
            passed = False
        results.append({
            "type": rt,
            "passed": type_passed,
            "covered": covered_count,
            "total": total,
            "uncovered": uncovered,
        })

    return {"passed": passed, "results": results}


# ---------------------------------------------------------------------------
# build_evidence_bundle — backs ci evidence bundle
# ---------------------------------------------------------------------------


def build_evidence_bundle(
    dhf_path: Path,
    out_dir: Path,
    junit_paths: list[Path] = (),
    coverage_pairs: tuple[str, ...] = (),
    traceability_types: tuple[str, ...] = (),
    compliance_standards: tuple[str, ...] = (),
    governance_dir: Path | None = None,
    run_id: str = "",
    run_url: str = "",
    commit_sha: str = "",
    continue_on_gate_failure: bool = False,
) -> dict[str, Any]:
    """Produce a self-contained CI evidence bundle.

    Returns a dict with ``gate_passed`` (bool), ``manifest``, and
    ``artifacts`` keyed by type.
    """
    from dhf_util.local_adapter import LocalDHFAdapter
    from compliantflow.core import CompliantFlowCore

    adapter = LocalDHFAdapter(dhf_path)
    core = CompliantFlowCore(adapter)

    if junit_paths:
        core.inject_junit_results(junit_paths)

    gate_result = _run_acceptance_gate(core, list(junit_paths), coverage_pairs)
    gate_passed = gate_result.get("passed", False)

    out_dir.mkdir(parents=True, exist_ok=True)

    doc_types = traceability_types if traceability_types else tuple()
    trace_types: tuple = (
        traceability_types
        if traceability_types
        else DEFAULT_TRACEABILITY_DOC_TYPES
    )

    artifacts = _run_artifact_generation(
        adapter, core, dhf_path, out_dir, doc_types, trace_types,
        list(junit_paths), skip_plans=False,
    )

    compliance_dir = out_dir / "compliance"
    compliance_dir.mkdir(parents=True, exist_ok=True)
    compliance_reports: list[dict] = []
    if compliance_standards and governance_dir:
        for standard in compliance_standards:
            output_pdf = compliance_dir / f"{standard}_Compliance_Report.pdf"
            try:
                report = core.check_compliance(standard, str(governance_dir))
                if report:
                    from compliantflow.report_generator import generate_compliance_pdf
                    generate_compliance_pdf(report, output_pdf)
                    compliance_reports.append({
                        "standard": standard,
                        "path": str(output_pdf),
                        "score": report.get("score", 0),
                        "passed": report.get("passed_policies", 0) == report.get("total_policies", 0),
                    })
            except Exception:
                compliance_reports.append({
                    "standard": standard,
                    "path": str(output_pdf),
                    "error": "generation_failed",
                })

    summary = {
        "dhf_root": str(dhf_path),
        "run_id": run_id,
        "run_url": run_url,
        "commit_sha": commit_sha,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_passed": gate_passed,
        "gate": gate_result,
        "artifacts": artifacts,
        "compliance_reports": compliance_reports,
    }
    summary_path = out_dir / "evidence-summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8"
    )

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
    manifest_path.write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )

    return {
        "gate_passed": gate_passed,
        "manifest": manifest,
        "artifacts": artifacts,
        "compliance_reports": compliance_reports,
    }


# ---------------------------------------------------------------------------
# release artifact consumption and assembly
# ---------------------------------------------------------------------------


def consume_release_artifact(
    repo: str,
    commit_sha: str,
    workflow_name: str = "ci-pipeline.yml",
    artifact_name: str = "dhf-release-artifacts",
    download_dir: Path | None = None,
) -> dict[str, Any]:
    """Download a CI-produced artifact for the given commit via gh CLI.

    Returns:
        {"downloaded_to": str, "artifact_id": int, "run_id": int}
    Raises RuntimeError on failure.
    """
    import os as _os
    import subprocess as _subprocess
    import json as _json

    download_dir = download_dir or Path("/tmp/release-artifacts")
    env = _os.environ.copy()

    def _gh(*args: str) -> str:
        result = _subprocess.run(
            ["gh"] + list(args),
            capture_output=True, text=True, env=env, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"gh {' '.join(args)} failed: {result.stderr.strip()}"
            )
        return result.stdout.strip()

    runs_json = _gh(
        "api", f"repos/{repo}/actions/workflows/{workflow_name}/runs",
        "--jq",
        f'[.workflow_runs[] | select(.head_sha=="{commit_sha}" and .status=="completed" and .conclusion=="success")] | sort_by(-.id)',
    )
    runs = _json.loads(runs_json)
    if not runs:
        raise RuntimeError(
            f"No successful {workflow_name} run found for commit {commit_sha}."
        )

    for run in runs:
        run_id = run["id"]
        artifacts_json = _gh(
            "api", f"repos/{repo}/actions/runs/{run_id}/artifacts",
            "--jq", f'[.artifacts[] | select(.name=="{artifact_name}")]',
        )
        artifacts = _json.loads(artifacts_json)
        if artifacts:
            artifact_id = artifacts[0]["id"]
            download_dir.mkdir(parents=True, exist_ok=True)
            _gh(
                "run", "download", str(run_id),
                "--repo", repo,
                "--name", artifact_name,
                "--dir", str(download_dir),
            )
            return {
                "downloaded_to": str(download_dir),
                "artifact_id": artifact_id,
                "run_id": run_id,
            }

    raise RuntimeError(
        f"No CI run for commit {commit_sha} contains artifact '{artifact_name}'."
    )


def assemble_release_bundle(
    artifact_dir: Path,
    wheel_paths: tuple[Path, ...] = (),
    getting_started: Path | None = None,
    version: str = "",
    commit_sha: str = "",
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Assemble release bundles from downloaded artifacts.

    Returns:
        {"cf_zip": str, "dhf_zip": str}
    """
    import zipfile as _zipfile

    out_dir = out_dir or Path("/tmp/release-bundles")
    out_dir.mkdir(parents=True, exist_ok=True)

    short_sha = commit_sha[:7] if commit_sha else "unknown"

    cf_name = (
        f"compliantflow-{version}-{short_sha}"
        if version
        else f"compliantflow-{short_sha}"
    )
    cf_zip = out_dir / f"{cf_name}.zip"
    with _zipfile.ZipFile(cf_zip, "w", _zipfile.ZIP_DEFLATED) as zf:
        for wp in wheel_paths:
            zf.write(wp, wp.name)
        if getting_started and getting_started.is_file():
            zf.write(getting_started, getting_started.name)

    dhf_name = f"DHF-{version}-{short_sha}" if version else f"DHF-{short_sha}"
    dhf_zip = out_dir / f"{dhf_name}.zip"
    with _zipfile.ZipFile(dhf_zip, "w", _zipfile.ZIP_DEFLATED) as zf:
        for fpath in sorted(artifact_dir.rglob("*")):
            if fpath.is_file() and not fpath.name.startswith("."):
                zf.write(fpath, str(fpath.relative_to(artifact_dir)))

    return {
        "cf_zip": str(cf_zip),
        "dhf_zip": str(dhf_zip),
    }
