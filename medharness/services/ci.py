"""Reusable CI gate APIs — library functions that CLI commands and tests call.

Each function returns a structured result dict. No print side effects.
"""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from medharness._helpers import (
    DEFAULT_ACCEPTANCE_COVERAGE_PAIRS,
    DEFAULT_TRACEABILITY_DOC_TYPES,
    _parse_coverage_pairs,
    _run_acceptance_gate,
    _run_artifact_generation,
)
from dhfkit.junit_parser import JUNIT_LINKS


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
    from dhfkit.local_adapter import LocalDHFAdapter
    from medharness.core import MedHarnessCore

    adapter = LocalDHFAdapter(dhf_path)
    core = MedHarnessCore(adapter)

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
    from dhfkit.local_adapter import LocalDHFAdapter

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
                    if prop.get("name") == JUNIT_LINKS:
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
    run_id: str = "",
    run_url: str = "",
    commit_sha: str = "",
    continue_on_gate_failure: bool = False,
) -> dict[str, Any]:
    """Produce a self-contained CI evidence bundle.

    Returns a dict with ``gate_passed`` (bool), ``manifest``, and
    ``artifacts`` keyed by type.
    """
    from dhfkit.local_adapter import LocalDHFAdapter
    from medharness.core import MedHarnessCore

    adapter = LocalDHFAdapter(dhf_path)
    core = MedHarnessCore(adapter)

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

    compliance_reports: list[dict] = []

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
# Test coverage computation for AI harness
# ---------------------------------------------------------------------------


def compute_item_coverage(
    junit_paths: list[Path],
    adapter=None,
) -> dict:
    """Parse JUnit XML files and return coverage plus manual-verification hints.

    Returns:
        {
          "computed": True,
          "coverage_by_item": dict,
          "uncovered_requirements": dict,
          "manual_verification_candidates": dict,
          "manual_verification_criteria": dict,
        }
    """
    from dhfkit.junit_parser import parse_junit_xml

    coverage_by_item: dict[str, list[str]] = {}
    for jp in junit_paths:
        if not jp.is_file():
            continue
        for result in parse_junit_xml(jp):
            if result.testing_status != "PASS":
                continue
            for link in result.links or []:
                coverage_by_item.setdefault(link.strip(), []).append(result.id)

    uncovered: dict[str, list[str]] = {}
    item_type_map: dict[str, str] = {}
    manual_candidates: dict[str, dict[str, list[str] | str]] = {}
    if adapter is not None:
        try:
            all_items = adapter.list_items()
            item_type_map = {it["id"]: it.get("type", "") for it in all_items}
            for item in all_items:
                reasons: list[str] = []
                if item.get("critical_safety") is True:
                    reasons.append("critical_safety")

                verification_method = item.get("verification_method")
                if isinstance(verification_method, list):
                    for method in verification_method:
                        if method in {"Inspection", "Demonstration"}:
                            reasons.append(f"verification_method:{method}")

                category = item.get("category")
                if category == "Usability":
                    reasons.append("category:Usability")

                if reasons:
                    manual_candidates[item["id"]] = {
                        "type": item.get("type", ""),
                        "reasons": reasons,
                    }
        except Exception:
            pass

    default_types = ("SRS", "SYS", "CRS")
    for rt in default_types:
        prefix = f"{rt}-"
        uncovered[rt] = []
        for item_id in item_type_map:
            if item_id.startswith(prefix) and item_id not in coverage_by_item:
                uncovered[rt].append(item_id)

    return {
        "computed": len(junit_paths) > 0,
        "coverage_by_item": coverage_by_item,
        "uncovered_requirements": {k: v for k, v in uncovered.items() if v},
        "manual_verification_candidates": manual_candidates,
        "manual_verification_criteria": {
            "critical_safety": True,
            "verification_methods": ["Inspection", "Demonstration"],
            "categories": ["Usability"],
        },
    }
