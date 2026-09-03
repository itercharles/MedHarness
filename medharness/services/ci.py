"""Reusable CI gate APIs — library functions that CLI commands and tests call.

Each function returns a structured result dict. No print side effects.
"""

from __future__ import annotations

import hashlib
import json
import re
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
from dhfkit.junit_parser import (
    DEFAULT_TEST_LEVEL,
    JUNIT_LEVEL,
    JUNIT_LINKS,
    JUNIT_TESTING,
    LINKS_TAG_RE,
    TESTING_TAG_RE,
    TEST_LEVELS,
)
from dhfkit.testing_points import parse_testing_points


# ---------------------------------------------------------------------------
# Gate result envelope
# ---------------------------------------------------------------------------

#: Keys every gate result carries, whatever the gate. A caller — a CI script or
#: an agent — parses this once and handles any gate, present or future.
ENVELOPE_KEYS = ("gate", "passed", "summary", "errors", "warnings", "details")


def gate_result(
    gate: str,
    passed: bool,
    summary: str,
    *,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    **details: Any,
) -> dict[str, Any]:
    """Wrap a gate outcome in the common envelope.

    Gate-specific payload goes under ``details`` rather than at the top level,
    so adding a field to one gate cannot change the shape callers rely on.
    Before this, the only key shared by every gate was ``passed`` — five gates
    meant five parsers.

    ``errors`` are what made the gate fail; ``warnings`` are what it noticed
    without failing. Both are plain strings, already phrased for a human,
    because the machine-readable form of the same information is in ``details``.
    """
    return {
        "gate": gate,
        "passed": passed,
        "summary": summary,
        "errors": list(errors or []),
        "warnings": list(warnings or []),
        "details": details,
    }


def envelope_from(gate: str, raw: dict) -> dict:
    """Restructure a gate's own dict into the common envelope.

    The gate keeps building its own messages — it knows what its findings mean.
    This only moves the gate-specific keys under ``details`` so the top level is
    identical across gates.
    """
    return gate_result(
        gate,
        bool(raw.get("passed", False)),
        str(raw.get("summary") or ""),
        errors=raw.get("errors") or [],
        warnings=raw.get("warnings") or [],
        **{k: v for k, v in raw.items()
           if k not in ("passed", "summary", "errors", "warnings")},
    )


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
    results: dict[str, Any] = {
        "coverage_gaps": [],
        "orphans": [],
        "verification_gaps": [],
    }

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
        dangling = tr.get("dangling", [])
        results["traceability"] = {
            "passed": required.get("passed", True)
            and not dangling
            and all(c.get("passed", True) for c in coverage_list),
            "required": required,
            "dangling": dangling,
            "coverage": coverage_list,
            "summary": tr.get("summary", ""),
        }
        if not required.get("passed", True):
            passed = False
        # A link that resolves to nothing is always an error — unlike an uncovered
        # item, it is not a gap in the design but a broken reference.
        if dangling:
            passed = False
        for c in coverage_list:
            if not c.get("passed", True) and fail_on_uncovered:
                passed = False

        # Structured extracts for machine consumers
        results["coverage_gaps"] = [
            {
                "matrix": c.get("matrix"),
                "parent_type": c.get("parent_type"),
                "child_type": c.get("child_type"),
                "uncovered": c.get("uncovered", []),
            }
            for c in coverage_list
            if not c.get("passed", True)
        ]
        results["orphans"] = tr.get("orphans", [])

        # verification_criteria gaps: verifiable items missing the field
        _VERIFIABLE = frozenset({"CRS", "SYS", "SRS"})
        verification_gaps = []
        try:
            for item in adapter.list_items():
                uid = item.get("id", "")
                type_code = uid.split("-")[0] if "-" in uid else ""
                if type_code in _VERIFIABLE:
                    vc = str(item.get("verification_criteria") or "").strip()
                    if not vc:
                        verification_gaps.append({
                            "id": uid,
                            "type": type_code,
                            # Says the field is optional. Without that, a reader
                            # sees `validate schema` pass and concludes the gate
                            # is warning about a field the schema never defined.
                            "issue": "verification_criteria is empty — an optional "
                                     "field, but §5.7 verification needs a stated "
                                     "criterion to verify against",
                        })
        except Exception:
            pass
        results["verification_gaps"] = verification_gaps

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

    errors, warnings = _structural_messages(results, fail_on_uncovered)
    schema_n = results.get("schema", {}).get("item_count", 0)
    return gate_result(
        "verify dhf", passed,
        f"{schema_n} item(s) checked; {len(errors)} error(s), {len(warnings)} warning(s).",
        errors=errors, warnings=warnings, results=results,
    )


def _structural_messages(results: dict, fail_on_uncovered: bool) -> tuple[list[str], list[str]]:
    """Split structural findings into what blocks and what merely advises."""
    errors: list[str] = []
    warnings: list[str] = []

    schema = results.get("schema") or {}
    errors.extend(str(e) for e in (schema.get("errors") or []))

    trace = results.get("traceability") or {}
    for failure in (trace.get("required") or {}).get("failures", []):
        errors.append(f"{failure.get('id')}: {failure.get('issue')}")
    for d in trace.get("dangling", []):
        errors.append(
            f"{d['source']}.{d['field']} -> {d['target']}: target does not exist"
        )

    # Uncovered items block only under --fail-on-uncovered; anywhere else they
    # are a gap in design still to be written, not a broken reference.
    bucket = errors if fail_on_uncovered else warnings
    for gap in results.get("coverage_gaps", []):
        bucket.append(
            f"{gap['parent_type']}->{gap['child_type']}: "
            f"{len(gap.get('uncovered') or [])} uncovered"
        )
    for gap in results.get("verification_gaps", []):
        warnings.append(f"{gap['id']}: {gap['issue']}")

    # --coverage-pair results live under their own key; a caller who asked for a
    # pair explicitly gets an error, not a warning.
    for row in (results.get("coverage") or {}).get("pairs", []):
        if row.get("error"):
            errors.append(f"{row['parent_type']}->{row['child_type']}: {row['error']}")
        elif not row.get("passed", True):
            errors.append(
                f"{row['parent_type']}->{row['child_type']}: "
                f"{row['covered']}/{row['total']} covered"
            )
    return errors, warnings


# ---------------------------------------------------------------------------
# ci_test_coverage_gate — backs ci test-coverage
# ---------------------------------------------------------------------------


def _levels_by_type(raw: Any, req_types: tuple[str, ...]) -> dict[str, list[str]]:
    """Resolve ``required_test_levels`` to the levels each requirement type needs.

    Two forms, because one of them could not express what IEC 62304 actually
    asks. A flat list applied to every type meant a project could only demand
    all levels of every requirement or none of any:

        required_test_levels: [unit, integration, system]

        required_test_levels:
          SRS: [unit, integration]     # §5.5, §5.6
          SYS: [system]                # §5.7

    The flat form still means "every type", so an existing activity map keeps
    behaving exactly as it did. A mapping requires nothing of a type it omits —
    silence is "not required here", not "inherit the others".
    """
    if isinstance(raw, dict):
        return {
            rt: [lvl for lvl in (raw.get(rt) or []) if lvl in TEST_LEVELS]
            for rt in req_types
        }
    flat = [lvl for lvl in (raw or []) if lvl in TEST_LEVELS]
    return {rt: list(flat) for rt in req_types}


def ci_test_coverage_gate(
    dhf_path: Path,
    junit_paths: list[Path],
    req_types: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Check requirement coverage from JUnit evidence.

    Returns a dict with ``passed`` (bool) and a ``results`` list of
    per-type coverage dicts.

    Every requirement must have at least one passing linked test.
    If a requirement declares numbered test points in its ``testing`` field,
    each declared point must also be covered by at least one passing linked test.
    """
    from dhfkit.local_adapter import LocalDHFAdapter

    if not junit_paths:
        return gate_result(
            "verify tests", False,
            "No JUnit files found.",
            errors=["No JUnit files found — pass --junit-dir or --junit."],
            results=[],
        )

    covered_reqs: set[str] = set()
    covered_pairs: set[tuple[str, str]] = set()
    # requirement -> the levels that actually verified it. §5.6 and §5.7 ask for
    # integration and system testing as distinct records; without this a suite
    # of unit tests alone made every requirement read as verified.
    covered_levels: dict[str, set[str]] = {}
    seen_levels: set[str] = set()
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
            name = tc.get("name", "")
            props: dict[str, str] = {}
            properties_el = tc.find("properties")
            if properties_el is not None:
                for prop in properties_el.findall("property"):
                    pname = prop.get("name", "")
                    if pname:
                        props[pname] = prop.get("value", "")

            links_from_props = [v.strip() for v in props.get(JUNIT_LINKS, "").split(",") if v.strip()]
            testing_from_props = [v.strip() for v in props.get(JUNIT_TESTING, "").split(",") if v.strip()]
            links_from_name = LINKS_TAG_RE.findall(name)
            testing_from_name = TESTING_TAG_RE.findall(name)

            all_links = list(dict.fromkeys(links_from_props + links_from_name))
            all_points = list(dict.fromkeys(testing_from_props + testing_from_name))

            level = (props.get(JUNIT_LEVEL) or "").strip().lower()
            if level not in TEST_LEVELS:
                level = DEFAULT_TEST_LEVEL
            seen_levels.add(level)

            covered_reqs.update(all_links)
            for req_id in all_links:
                covered_levels.setdefault(req_id, set()).add(level)
                for point_id in all_points:
                    covered_pairs.add((req_id, point_id))

    adapter = LocalDHFAdapter(dhf_path)
    all_items = adapter.list_items()

    passed = True
    results: list[dict] = []
    testing_points: list[dict] = []
    default_types = req_types if req_types else ("SRS", "SYS", "CRS")

    # Levels the declared safety class requires. Absent a class this is empty and
    # the level dimension is inert, so a project that has not opted in to
    # classification sees exactly the behaviour it saw before.
    raw_levels = adapter._config.required_activities().get("required_test_levels")
    required_levels = _levels_by_type(raw_levels, default_types)
    level_gaps: list[dict] = []

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
            req_id = ri["id"]
            has_req_coverage = req_id in covered_reqs
            testing_text = ri.get("testing") or ""
            points = parse_testing_points(testing_text)
            uncovered_points = [pt for pt in points if (req_id, pt) not in covered_pairs]
            if uncovered_points:
                passed = False
                testing_points.append({
                    "req_id": req_id,
                    "total": len(points),
                    "covered": len(points) - len(uncovered_points),
                    "uncovered": uncovered_points,
                    "passed": False,
                })
            elif points:
                testing_points.append({
                    "req_id": req_id,
                    "total": len(points),
                    "covered": len(points),
                    "uncovered": [],
                    "passed": True,
                })

            levels_for_type = required_levels.get(rt) or []
            if has_req_coverage and levels_for_type:
                have = covered_levels.get(req_id, set())
                missing_levels = [lvl for lvl in levels_for_type if lvl not in have]
                if missing_levels:
                    passed = False
                    level_gaps.append({
                        "req_id": req_id,
                        "have": sorted(have),
                        "missing": missing_levels,
                    })

            if has_req_coverage:
                covered_count += 1
            else:
                uncovered.append(req_id)
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

    errors = [
        f"{row['type']}: {row['covered']}/{row['total']} requirements covered"
        for row in results if not row.get("passed") and "warning" not in row
    ] + [
        f"{tp['req_id']}: test points {', '.join(tp['uncovered'])} uncovered"
        for tp in testing_points if not tp["passed"]
    ] + [
        f"{gap['req_id']}: verified at {', '.join(gap['have']) or 'no level'} "
        f"but missing {', '.join(gap['missing'])}"
        for gap in level_gaps
    ]
    warnings = [row["warning"] for row in results if row.get("warning")]
    covered = sum(r.get("covered", 0) for r in results)
    total = sum(r.get("total", 0) for r in results)
    return gate_result(
        "verify tests", passed,
        f"{covered}/{total} requirement(s) covered by passing tests.",
        errors=errors, warnings=warnings,
        results=results,
        testing_points=testing_points,
        required_levels=required_levels,
        levels_seen=sorted(seen_levels),
        level_gaps=level_gaps,
    )


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
    doc_format: str = "html",
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
        list(junit_paths), skip_plans=False, doc_format=doc_format,
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

    An item becomes a manual-verification candidate when any of these DHF item
    fields are set: ``critical_safety == True``, ``verification_method`` contains
    ``"Inspection"`` or ``"Demonstration"``, or ``category == "Usability"``.

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


# ---------------------------------------------------------------------------
# validate_verification_completeness — backs ci validate-verification
# ---------------------------------------------------------------------------

_NON_TEST_METHODS = frozenset({"Inspection", "Analysis", "Demonstration"})
# Item types that carry a verification_method field — RISK, RCM, SWDD, etc. do not.
_VERIFIABLE_ITEM_TYPES = frozenset({"CRS", "SRS", "SYS", "SOUP"})


def validate_verification_completeness(
    dhf_path: Path,
    junit_paths: list[Path] = (),
    req_types: tuple[str, ...] = (),
    enforce_test_evidence: bool = False,
) -> dict[str, Any]:
    """Check that every requirement has a declared verification method with evidence.

    Three distinct gap categories are returned:

    - ``missing_method``: items with no ``verification_method`` field declared.
      These are unconditional failures — no verification can be planned or
      tracked without a declared method.

    - ``unverified_test``: items that declare "Test" as a method but have no
      linked passing test case in the provided JUnit evidence. Gate failure when
      JUnit paths are supplied; warning when no JUnit paths are provided.

    - ``manual_review_required``: items that declare only non-Test methods
      (Inspection, Analysis, Demonstration). These cannot be automatically
      verified; they are surfaced for human sign-off tracking. Not a gate
      failure by default.

    Args:
        dhf_path: Path to the DHF directory.
        junit_paths: JUnit XML files providing test evidence (optional).
        req_types: Requirement type codes to check (default: SRS, SYS, CRS).

    Returns:
        {
          "passed": bool,
          "missing_method": [{"id": str, "type": str, "title": str}],
          "unverified_test": [{"id": str, "type": str, "title": str}],
          "manual_review_required": [{"id": str, "type": str, "title": str, "methods": list[str]}],
          "summary": str,
        }
    """
    import xml.etree.ElementTree as ET

    from dhfkit.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(dhf_path)
    all_items = adapter.list_items()
    config = adapter._config

    # Resolve configured prefixes so custom prefixes (e.g. SYSREQ-) are handled correctly.
    default_types = req_types if req_types else ("SRS", "SYS", "CRS")
    prefix_to_code: dict[str, str] = {}
    for rt in default_types:
        dt = config.get_doc_type(rt)
        if dt:
            prefix_to_code[dt.prefix] = rt

    # Build set of requirement IDs covered by passing tests
    covered_by_test: set[str] = set()
    for jp in junit_paths:
        if not jp.is_file():
            continue
        tree = ET.parse(jp)
        for tc in tree.iter("testcase"):
            if list(tc.iter("failure")) or list(tc.iter("error")) or list(tc.iter("skipped")):
                continue
            for props in tc.iter("properties"):
                for prop in props.iter("property"):
                    if prop.get("name") == JUNIT_LINKS:
                        for link in (prop.get("value") or "").split(","):
                            link = link.strip()
                            if link:
                                covered_by_test.add(link)

    missing_method: list[dict] = []
    unverified_test: list[dict] = []
    manual_review_required: list[dict] = []

    for item in all_items:
        uid = item.get("id", "")
        type_code = next((code for pfx, code in prefix_to_code.items() if uid.startswith(pfx)), None)
        if not type_code:
            continue

        raw_method = item.get("verification_method")
        if isinstance(raw_method, str):
            methods = [m.strip() for m in raw_method.split(",") if m.strip()] if raw_method.strip() else []
        elif isinstance(raw_method, list):
            methods = [str(m).strip() for m in raw_method if str(m).strip()]
        else:
            methods = []

        title = item.get("title", "")
        entry = {"id": uid, "type": type_code, "title": title}

        if not methods:
            missing_method.append(entry)
            continue

        test_methods = [m for m in methods if m == "Test"]
        non_test_methods = [m for m in methods if m in _NON_TEST_METHODS]

        if test_methods and uid not in covered_by_test:
            unverified_test.append(entry)

        if non_test_methods and not test_methods:
            manual_review_required.append({**entry, "methods": non_test_methods})

    has_junit = bool(junit_paths)
    # enforce_test_evidence=True: Test items without passing TCs always fail even
    # when no JUnit files are provided — used by the CR closure gate where missing
    # evidence is itself the failure, not an acceptable "not yet checked" state.
    passed = not missing_method and (not unverified_test if (has_junit or enforce_test_evidence) else True)

    parts = []
    if missing_method:
        parts.append(f"{len(missing_method)} missing verification_method")
    if unverified_test:
        parts.append(f"{len(unverified_test)} unverified (Test method, no passing TC)")
    if manual_review_required:
        parts.append(f"{len(manual_review_required)} require manual sign-off")
    summary = ("PASS" if passed else "FAIL") + " — " + ", ".join(parts) if parts else "All verification checks passed."

    return envelope_from("verify verification", {
        "passed": passed,
        "errors": (
            [f"{g['id']}: no verification_method declared" for g in missing_method]
            + [f"{g['id']}: declares Test but has no passing evidence" for g in unverified_test]
        ),
        "warnings": [
            f"{g['id']}: verified by {', '.join(g['methods'])} — needs manual review"
            for g in manual_review_required
        ],
        "missing_method": missing_method,
        "unverified_test": unverified_test,
        "manual_review_required": manual_review_required,
        "summary": summary,
    })


def _parse_accepted_vulns(item: dict, soup_id: str) -> tuple[dict[str, str], list[str]]:
    """Read a SOUP item's ``accepted_vulns`` into {vuln_id: rationale}.

    IEC 62304 §8.1.2 requires SOUP anomalies to be *evaluated*, not necessarily
    fixed. An acceptance is only honoured when it names a specific vulnerability
    ID and records why it is acceptable — a bare ID carries no assessment, and
    blanket acceptance would silently absorb newly published CVEs.

    Returns ({vuln_id: rationale}, malformed_entry_messages).
    """
    accepted: dict[str, str] = {}
    problems: list[str] = []

    for entry in item.get("accepted_vulns") or []:
        if not isinstance(entry, dict):
            problems.append(
                f"{soup_id} — accepted_vulns entry {entry!r} must be a mapping with "
                "'id' and 'rationale'; the vulnerability still blocks."
            )
            continue
        vuln_id = str(entry.get("id") or "").strip()
        rationale = str(entry.get("rationale") or "").strip()
        if not vuln_id:
            problems.append(f"{soup_id} — accepted_vulns entry is missing 'id'.")
            continue
        if not rationale:
            problems.append(
                f"{soup_id} — accepted_vulns entry {vuln_id} is missing 'rationale'; "
                "record why the vulnerability is acceptable or it will keep blocking."
            )
            continue
        accepted[vuln_id] = rationale

    return accepted, problems


_VULN_DETAIL_BUDGET = 25


def _vuln_detail(vuln_id: str, batch_entry: dict, *, fetch: bool) -> dict:
    """Build a reportable vulnerability record for *vuln_id*.

    osv.dev's ``querybatch`` returns only ``id`` and ``modified`` — summary and
    severity live on the per-vulnerability endpoint — so a batch entry alone
    cannot describe what is wrong. Fetch that detail when *fetch* is set, and
    always emit a URL so the finding stays actionable if the lookup fails.
    """
    import json as _json
    import urllib.error
    import urllib.request

    summary = batch_entry.get("summary") or ""
    severity = (
        batch_entry.get("database_specific", {}).get("severity")
        or (batch_entry.get("severity") or [{}])[0].get("score", "")
    )

    if fetch and vuln_id and not summary:
        try:
            with urllib.request.urlopen(
                f"https://api.osv.dev/v1/vulns/{vuln_id}", timeout=10
            ) as resp:
                detail = _json.loads(resp.read())
            summary = detail.get("summary") or (detail.get("details") or "").split("\n")[0]
            severity = severity or detail.get("database_specific", {}).get("severity") or ""
        except (urllib.error.URLError, ValueError, TimeoutError):
            pass  # URL below still identifies the finding

    return {
        "id": vuln_id,
        "summary": summary.strip()[:200],
        "severity": severity,
        "url": f"https://osv.dev/vulnerability/{vuln_id}" if vuln_id else "",
    }


def soup_vuln_gate(dhf_path: Path, *, offline_mode: str = "fail") -> dict:
    """Check SOUP items against the OSV vulnerability database.

    For each SOUP item that has both ``name`` and ``ecosystem`` fields, queries
    https://api.osv.dev/v1/querybatch and reports known vulnerabilities.

    Items without an ``ecosystem`` field are skipped with a note so adopters can
    add the field without breaking CI.

    A vulnerability listed in the item's ``accepted_vulns`` (with a rationale) is
    reported as accepted rather than blocking — see :func:`_parse_accepted_vulns`.

    Args:
        offline_mode: ``"fail"`` (default) treats an unreachable osv.dev as a gate
            failure. ``"warn"`` reports the outage but leaves the gate passing, for
            air-gapped or proxy-restricted pipelines where the scan runs elsewhere.

    Returns:
        {
          "passed": bool,
          "soup_count": int,
          "checked_count": int,
          "vulnerable": [{"soup_id", "name", "version", "vulns": [...]}],
          "accepted": [{"soup_id", "name", "version", "vuln_id", "rationale"}],
          "skipped": [{"soup_id", "reason"}],
          "acceptance_problems": [str],
          "error": str | None,
          "summary": str,
        }
    """
    import json as _json
    import urllib.error
    import urllib.request

    from dhfkit.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(dhf_path)
    all_items = adapter.list_items()
    soup_items = [it for it in all_items if it.get("type") == "SOUP"]

    checkable: list[dict] = []
    skipped: list[dict] = []
    acceptance_problems: list[str] = []

    for item in soup_items:
        soup_id = item.get("id", "?")
        name = str(item.get("name") or "").strip()
        version = str(item.get("version") or "").strip()
        ecosystem = str(item.get("ecosystem") or "").strip()
        accepted, problems = _parse_accepted_vulns(item, soup_id)
        acceptance_problems.extend(problems)
        if not name or not version:
            skipped.append({"soup_id": soup_id, "reason": "missing name or version"})
            continue
        if not ecosystem:
            skipped.append({"soup_id": soup_id, "reason": "ecosystem not specified — add e.g. ecosystem: PyPI"})
            continue
        checkable.append({
            "soup_id": soup_id, "name": name, "version": version,
            "ecosystem": ecosystem, "accepted": accepted,
        })

    if not checkable:
        n_soup = len(soup_items)
        return envelope_from("verify soup", {
            "passed": True,
            "soup_count": n_soup,
            "checked_count": 0,
            "vulnerable": [],
            "accepted": [],
            "skipped": skipped,
            "acceptance_problems": acceptance_problems,
            "error": None,
            "summary": (
                f"{n_soup} SOUP item(s) found; none checkable "
                "(add 'ecosystem' field to enable vulnerability scanning)."
            ) if n_soup else "No SOUP items in DHF.",
        })

    queries = [
        {"package": {"name": c["name"], "ecosystem": c["ecosystem"]}, "version": c["version"]}
        for c in checkable
    ]
    body = _json.dumps({"queries": queries}).encode()
    req = urllib.request.Request(
        "https://api.osv.dev/v1/querybatch",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            results = _json.loads(resp.read()).get("results", [])
    except urllib.error.URLError as exc:
        tolerated = offline_mode == "warn"
        outage = f"osv.dev unreachable: {exc}"
        return envelope_from("verify soup", {
            "passed": tolerated,
            # The outage belongs in the envelope, not a private key: a caller
            # that handles `errors`/`warnings` for every gate handles this too.
            "errors": [] if tolerated else [outage],
            "warnings": [outage] if tolerated else [],
            "soup_count": len(soup_items),
            "checked_count": 0,
            "vulnerable": [],
            "accepted": [],
            "skipped": skipped,
            "acceptance_problems": acceptance_problems,
            "error": f"osv.dev unreachable: {exc}",
            "summary": (
                f"SOUP vulnerability scan skipped — osv.dev unreachable ({exc}). "
                "Gate tolerated the outage (--offline-mode warn); scan SOUP through "
                "your offline process to keep IEC 62304 §8.1.2 evidence complete."
                if tolerated
                else f"SOUP vulnerability check failed: {exc}"
            ),
        })

    vulnerable: list[dict] = []
    accepted_found: list[dict] = []
    detail_budget = _VULN_DETAIL_BUDGET
    for meta, result in zip(checkable, results):
        vulns_raw = result.get("vulns") or []
        if not vulns_raw:
            continue
        blocking = []
        for v in vulns_raw:
            vuln_id = v.get("id", "")
            rationale = meta["accepted"].get(vuln_id)
            if rationale is not None:
                accepted_found.append({
                    "soup_id": meta["soup_id"],
                    "name": meta["name"],
                    "version": meta["version"],
                    "vuln_id": vuln_id,
                    "rationale": rationale,
                })
                continue
            blocking.append(_vuln_detail(vuln_id, v, fetch=detail_budget > 0))
            detail_budget -= 1
        if blocking:
            vulnerable.append({
                "soup_id": meta["soup_id"],
                "name": meta["name"],
                "version": meta["version"],
                "vulns": blocking,
            })

    passed = len(vulnerable) == 0
    n_vuln = sum(len(v["vulns"]) for v in vulnerable)
    summary_parts = [
        f"{len(soup_items)} SOUP item(s), {len(checkable)} checked.",
        f"{n_vuln} unresolved vulnerability(-ies) across {len(vulnerable)} item(s)."
        if not passed
        else "No unresolved vulnerabilities found.",
    ]
    if accepted_found:
        summary_parts.append(f"{len(accepted_found)} documented as accepted.")
    return envelope_from("verify soup", {
        "passed": passed,
        # Phrased exactly as a reader needs it — severity and a URL fallback
        # included — so the CLI renders the envelope instead of rebuilding the
        # same line beside it. Two renderers printed every vulnerability twice.
        "errors": [
            f"{item['soup_id']} ({item['name']}@{item['version']}): {v['id']} — "
            + (f"[{v['severity']}] " if v.get("severity") else "")
            + (v.get("summary") or v.get("url") or "see osv.dev")
            for item in vulnerable for v in item["vulns"]
        ],
        "warnings": list(acceptance_problems) + [
            f"{a['soup_id']}: {a['vuln_id']} accepted — {a['rationale']}"
            for a in accepted_found
        ],
        "soup_count": len(soup_items),
        "checked_count": len(checkable),
        "vulnerable": vulnerable,
        "accepted": accepted_found,
        "skipped": skipped,
        "acceptance_problems": acceptance_problems,
        "error": None,
        "summary": " ".join(summary_parts),
    })


def _check_cr_fields(cr_item: dict, cr_id: str) -> list[dict]:
    """Check that generate-dhf mandatory CR fields are populated.

    Returns a list of issue dicts for each missing or invalid field.
    """
    issues: list[dict] = []
    if not str(cr_item.get("implementation_notes") or "").strip():
        issues.append({
            "field": "implementation_notes",
            "issue": (
                f"CR {cr_id} — implementation_notes is absent; "
                "run generate-dhf Step 3 to record the implementation plan."
            ),
        })
    if not isinstance(cr_item.get("affected_risk_items"), list):
        issues.append({
            "field": "affected_risk_items",
            "issue": (
                f"CR {cr_id} — affected_risk_items is absent; "
                "run generate-dhf Step 2.5 to record risk impact (use [] if none)."
            ),
        })
    triage = cr_item.get("triage_result")
    if not isinstance(triage, dict) or triage.get("verdict") != "approved":
        issues.append({
            "field": "triage_result",
            "issue": (
                f"CR {cr_id} — triage_result.verdict is not 'approved'; "
                "run generate-dhf Step 1 to record the triage decision."
            ),
        })
    return issues


def _check_design_review(dhf_path: Path, cr_id: str) -> list[dict]:
    """Check that the design stage was approved.

    An APR item is the record of record: it is a DHF item, so it appears in the
    traceability matrix and the evidence bundle, and the revision it covers is
    its own commit rather than a field that could be edited to disagree.

    The legacy docs/reviews/<CR>-Design-Review.md convention is still accepted so
    projects mid-flight are not stranded; `dhfkit approval import` converts it.
    """
    from dhfkit.approval import find_approvals

    try:
        approvals = find_approvals(dhf_path, approves=cr_id, stage="design")
    except Exception:  # noqa: BLE001 — fall through to the file convention
        approvals = []

    if approvals:
        latest = approvals[-1]
        verdict = str(latest.get("verdict") or "unknown")
        if verdict == "approved":
            return []
        return [{
            "field": "design_review",
            "issue": (
                f"CR {cr_id} — {latest['id']} records verdict '{verdict}', not "
                "'approved'; resolve open issues before closing."
            ),
        }]

    review_file = dhf_path.parent / "docs" / "reviews" / f"{cr_id}-Design-Review.md"
    if not review_file.exists():
        return [{
            "field": "design_review",
            "issue": (
                f"CR {cr_id} — no approval record. Expected an APR item approving "
                f"{cr_id} at the design stage, or the legacy review file at "
                f"docs/reviews/{cr_id}-Design-Review.md. Run 'change plan' to "
                "generate the design review, or 'approval act' to record a decision."
            ),
        }]
    verdict = "unknown"
    for line in review_file.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("**Verdict:**"):
            lower = stripped.lower()
            if "approved" in lower:
                verdict = "approved"
            elif "needs revision" in lower:
                verdict = "needs_revision"
            break
    if verdict != "approved":
        return [{
            "field": "design_review",
            "issue": (
                f"CR {cr_id} — design review verdict is '{verdict}', not 'approved'; "
                "resolve open issues before closing."
            ),
        }]
    return []


def _closure_errors(incomplete=(), missing=(), gaps=(), unverified=()) -> list[str]:
    """Phrase closure findings for the envelope.

    Shared by every exit path: an early return that skips the later checks
    still has to say why it failed, or a caller sees `passed: false` with an
    empty `errors` and nothing to act on.
    """
    return (
        [i["issue"] for i in incomplete]
        + [f"{m}: named in proposed_new_items but absent from the DHF" for m in missing]
        + [f"{g['id']}: no verification_method declared" for g in gaps]
        + [f"{g['id']}: declares Test but has no passing JUnit evidence" for g in unverified]
    )


def cr_closure_gate(
    cr_id: str,
    dhf_path: Path,
    junit_paths: tuple[Path, ...] = (),
) -> dict:
    """Verify that a CR is fully closed: all proposed items created and verified.

    Checks:
    1. CR item carries implementation_notes, affected_risk_items, and an approved triage_result.
    2. A design review file exists at docs/reviews/<CR>-Design-Review.md with verdict=approved.
    3. All ``proposed_new_items`` from the CR item exist in the DHF.
    4. All created items of verifiable types have ``verification_method`` set.
    5. Items with ``Test`` method have passing JUnit evidence (when JUnit provided).

    Args:
        cr_id: CR identifier (e.g. CR-012).
        dhf_path: Path to the DHF directory.
        junit_paths: JUnit XML files providing test evidence (optional).

    Returns:
        {
          "passed": bool,
          "cr_id": str,
          "incomplete_cr_fields": [{"field": str, "issue": str}],
          "missing_items": [{"type": str, "title": str, "issue": str}],
          "verification_gaps": [{"id": str, "type": str, "title": str}],
          "unverified_test": [{"id": str, "type": str, "title": str}],
          "manual_review_required": [{"id": str, "type": str, "title": str, "methods": list}],
          "summary": str,
        }
    """
    from dhfkit.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(dhf_path)
    all_items = adapter.list_items()
    config = adapter._config

    # Load proposed_new_items from the CR item — generate-dhf Step 4 writes this
    # field via `dhf item update` so it persists in the CR YAML alongside the CR itself.
    cr_item = adapter.get_item(cr_id) or {}
    incomplete_cr_fields = _check_cr_fields(cr_item, cr_id)
    incomplete_cr_fields.extend(_check_design_review(dhf_path, cr_id))

    raw = cr_item.get("proposed_new_items")
    if raw is None:
        return envelope_from("verify completion", {
            "passed": False,
            "errors": _closure_errors(incomplete=incomplete_cr_fields) + [
                f"CR {cr_id}: proposed_new_items is absent — re-run generate-dhf "
                f"Step 4 to record the items created in this session."
            ],
            "cr_id": cr_id,
            "incomplete_cr_fields": incomplete_cr_fields,
            "missing_items": [],
            "verification_gaps": [],
            "unverified_test": [],
            "manual_review_required": [],
            "summary": (
                f"CR {cr_id} — proposed_new_items field is absent from the CR item; "
                "re-run generate-dhf Step 4 to record the items created in this session."
            ),
        })
    proposed: list[dict] = [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []

    if not proposed:
        return envelope_from("verify completion", {
            "passed": not bool(incomplete_cr_fields),
            "errors": _closure_errors(incomplete=incomplete_cr_fields),
            "cr_id": cr_id,
            "incomplete_cr_fields": incomplete_cr_fields,
            "missing_items": [],
            "verification_gaps": [],
            "unverified_test": [],
            "manual_review_required": [],
            "summary": (
                f"CR {cr_id} — proposed_new_items is empty; no artifact reconciliation required."
                if not incomplete_cr_fields
                else f"CR {cr_id} — proposed_new_items is empty but CR fields are incomplete."
            ),
        })

    # Scope item lookup to those generated by this specific CR when possible.
    # generate-dhf writes affected_items onto the CR item after every run, so
    # we can avoid counting pre-existing DHF items of the same type as coverage
    # for this CR's proposed items.
    affected_ids: set[str] = set(cr_item.get("affected_items") or [])
    items_by_id = {it["id"]: it for it in all_items}
    # When affected_ids is available use it; otherwise fall back to all DHF items.
    scoped_items = (
        [items_by_id[uid] for uid in affected_ids if uid in items_by_id]
        if affected_ids else all_items
    )

    # Check each proposed item by (type, title).
    # Deduplicate proposed entries first: if the same (type, title) appears N times,
    # only one real DHF item is required — duplicate proposals are a LLM authoring
    # quirk, not a requirement for N identical items.
    seen_proposed: set[tuple[str, str]] = set()
    deduped_proposed: list[dict] = []
    for entry in proposed:
        item_type = str(entry.get("type", "")).strip().upper()
        title = str(entry.get("title", "")).strip()
        if not item_type or not title:
            continue
        key = (item_type, title.lower())
        if key not in seen_proposed:
            seen_proposed.add(key)
            deduped_proposed.append({"type": item_type, "title": title})

    missing_items: list[dict] = []
    for entry in deduped_proposed:
        item_type = entry["type"]
        title = entry["title"]
        dt = config.get_doc_type(item_type)
        prefix = dt.prefix if dt else f"{item_type}-"
        title_lower = title.lower()
        found = any(
            it["id"].startswith(prefix)
            and str(it.get("title", "")).strip().lower() == title_lower
            for it in scoped_items
        )
        if not found:
            missing_items.append({
                "type": item_type,
                "title": title,
                "issue": f"No {item_type} item matching '{title}' found in CR's generated artifacts",
            })

    # Determine which types to check for verification — restrict to types that
    # carry a verification_method field. RISK, RCM, SWDD, etc. do not have that
    # field, so including them would produce false missing_method failures.
    proposed_types = list({e["type"] for e in deduped_proposed})
    verifiable = [t for t in proposed_types if t in _VERIFIABLE_ITEM_TYPES]

    if not verifiable:
        # CR proposes only non-verifiable items (RISK, RCM, SWDD, …).
        # Scanning the whole DHF would flag pre-existing deficiencies unrelated to this CR.
        passed = not missing_items and not incomplete_cr_fields
        parts = [f"{len(missing_items)} proposed item(s) not found in CR artifacts"] if missing_items else []
        if incomplete_cr_fields:
            parts.append(f"{len(incomplete_cr_fields)} CR field(s) incomplete")
        summary = ("PASS" if passed else "FAIL") + (" — " + ", ".join(parts) if parts else "")
        if passed:
            summary = f"CR {cr_id} closure verified — all proposed items present."
        return envelope_from("verify completion", {
            "passed": passed,
            "errors": _closure_errors(incomplete=incomplete_cr_fields,
                                      missing=missing_items),
            "cr_id": cr_id,
            "incomplete_cr_fields": incomplete_cr_fields,
            "missing_items": missing_items,
            "verification_gaps": [],
            "unverified_test": [],
            "manual_review_required": [],
            "summary": summary,
        })

    verify_result = validate_verification_completeness(
        dhf_path,
        junit_paths=junit_paths,
        req_types=tuple(verifiable),
        enforce_test_evidence=True,
    )

    passed = not missing_items and verify_result["passed"] and not incomplete_cr_fields

    parts: list[str] = []
    if incomplete_cr_fields:
        parts.append(f"{len(incomplete_cr_fields)} CR field(s) incomplete")
    if missing_items:
        parts.append(f"{len(missing_items)} proposed item(s) not found in CR artifacts")
    if not verify_result["passed"]:
        parts.append(verify_result["summary"])
    summary = ("PASS" if passed else "FAIL") + (" — " + ", ".join(parts) if parts else "")
    if passed and not parts:
        summary = f"CR {cr_id} closure verified — all proposed items present and verified."

    return envelope_from("verify completion", {
        "passed": passed,
        "errors": _closure_errors(
            incomplete=incomplete_cr_fields, missing=missing_items,
            gaps=verify_result["details"].get("missing_method", []),
            unverified=verify_result["details"].get("unverified_test", []),
        ),
        "cr_id": cr_id,
        "incomplete_cr_fields": incomplete_cr_fields,
        "missing_items": missing_items,
        # verify_result is itself an envelope now; its findings live in details.
        "verification_gaps": verify_result["details"].get("missing_method", []),
        "unverified_test": verify_result["details"].get("unverified_test", []),
        "manual_review_required": verify_result["details"].get("manual_review_required", []),
        "summary": summary,
    })



# ---------------------------------------------------------------------------
# classification_gate — backs verify classification
# ---------------------------------------------------------------------------

_SAFETY_CLASSES = ("A", "B", "C")


def classification_gate(dhf_path: Path) -> dict:
    """Check the declared software safety class and what it requires.

    IEC 62304 §4.3 makes the class the axis the standard turns on: it decides
    which activities are required at all. Without a declared class the tool can
    verify that items are consistent with each other, but not that the project
    has done what its class demands.

    An undeclared class is reported as a warning rather than a failure, so an
    existing DHF keeps passing until it opts in.

    Returns:
        {
          "passed": bool,
          "declared": str | None,
          "rationale_present": bool,
          "missing_item_types": [{"code", "clause_hint"}],
          "module_overrides": [{"id", "safety_class", "justified": bool}],
          "warnings": [str],
          "errors": [str],
          "summary": str,
        }
    """
    from dhfkit.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(dhf_path)
    config = adapter._config

    declared = (config.software_safety_class or "").strip().upper()
    rationale = (config.classification_rationale or "").strip()
    warnings: list[str] = []
    errors: list[str] = []

    if not declared:
        return envelope_from("verify classification", {
            "passed": True,
            "declared": None,
            "rationale_present": False,
            "missing_item_types": [],
            "module_overrides": [],
            "warnings": [
                "No software_safety_class declared in DHF/config/global.yaml. "
                "IEC 62304 §4.3 requires one, and it determines which activities "
                "this project must complete. Set A, B, or C to enable the check."
            ],
            "errors": [],
            "summary": "No safety class declared — classification checks are inactive.",
        })

    if declared not in _SAFETY_CLASSES:
        errors.append(
            f"software_safety_class is '{declared}'; expected one of "
            f"{', '.join(_SAFETY_CLASSES)}."
        )
    if not rationale:
        errors.append(
            "classification_rationale is empty. The class is a judgement about the "
            "device, and the reasoning belongs in the record."
        )

    required = config.required_activities()
    no_activities = declared in _SAFETY_CLASSES and not required
    if no_activities:
        # An error, not a warning. Declaring the class *is* taking the opt-in, so
        # the gate is no longer inert — it is being asked to do a job it cannot
        # do. Reported as a pass, a project sees green and believes it is being
        # audited while nothing is checked against the class at all.
        errors.append(
            f"Class {declared} is declared but safety_activities.yaml defines no "
            f"activities for it, so nothing is being checked against the class. "
            f"Run 'medharness upgrade --apply' to obtain the file, then edit it "
            f"to match what this project has agreed."
        )

    present_types = {
        str(item.get("id", "")).rsplit("-", 1)[0]
        for item in adapter.list_items()
        if item.get("id")
    }
    present_codes = set()
    for item_type in adapter.list_item_types():
        prefix = (item_type.get("prefix") or "").rstrip("-")
        if prefix and prefix in present_types:
            present_codes.add(item_type.get("code"))

    missing_item_types = [
        {"code": code, "clause_hint": _CLASS_CLAUSE_HINTS.get(code, "")}
        for code in (required.get("required_items") or [])
        if code not in present_codes
    ]
    for entry in missing_item_types:
        errors.append(
            f"Class {declared} requires {entry['code']} items and the DHF has none"
            + (f" ({entry['clause_hint']})." if entry["clause_hint"] else ".")
        )

    # §4.3(b) allows a software item to carry a lower class than the system when
    # segregation is documented. Record the overrides; an unjustified one is a
    # gap rather than an error, since the justification may live in the
    # architecture rather than on the item.
    module_overrides = []
    for item in adapter.list_items():
        override = str(item.get("safety_class") or "").strip().upper()
        if not override or not str(item.get("id", "")).startswith("MODULE-"):
            continue
        justified = bool(str(item.get("segregation_rationale") or "").strip())
        module_overrides.append(
            {"id": item["id"], "safety_class": override, "justified": justified}
        )
        if not justified:
            warnings.append(
                f"{item['id']} declares safety_class {override}, below the system "
                f"class {declared}, without a segregation_rationale (§4.3(b))."
            )

    passed = not errors
    summary = f"Class {declared}: " + (
        "no activities defined for this class — nothing was checked."
        if no_activities
        else "all required activities present." if passed
        else f"{len(errors)} gap(s)."
    )
    return envelope_from("verify classification", {
        "passed": passed,
        "declared": declared,
        "rationale_present": bool(rationale),
        "missing_item_types": missing_item_types,
        "module_overrides": module_overrides,
        "warnings": warnings,
        "errors": errors,
        "summary": summary,
    })


_CLASS_CLAUSE_HINTS = {
    "SYSARCH": "§5.3 architectural design",
    "SWDD": "§5.4 detailed design",
    "MODULE": "§5.4 detailed design",
    "RISK": "§7 / ISO 14971",
    "RCM": "§7 risk control",
}


# ---------------------------------------------------------------------------
# plans_gate — backs verify plans
# ---------------------------------------------------------------------------

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)

# Boilerplate the scaffold ships. Removing it is housekeeping, not authorship,
# so it is normalised out of both sides before comparison — otherwise deleting
# the banner would make an untouched plan look partially written.
_TEMPLATE_BANNER = re.compile(
    r"^.*(?:Starter Content|scaffolded by MedHarness|Template — adapt|"
    r"starter plan|Replace for Your Project).*$",
    re.MULTILINE | re.IGNORECASE,
)


def _strip_banner(markdown_text: str) -> str:
    return _TEMPLATE_BANNER.sub("", markdown_text)


def _sections(markdown_text: str, min_level: int = 2) -> dict:
    """Split a plan into {heading: body}, so comparison is per-section.

    Whole-file comparison would be useless — a project that edits one section
    makes the file differ and the plan would read as written.

    Level-1 sections are excluded by default: the body under a document's title
    is its own front matter, and edits there are formatting rather than the
    substance §5.1 asks a plan to carry.
    """
    sections: dict[str, str] = {}
    matches = list(_HEADING.finditer(markdown_text))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        if len(match.group(1)) < min_level:
            continue
        sections[match.group(2).strip()] = markdown_text[start:end].strip()
    return sections


def plans_gate(dhf_path: Path) -> dict:
    """Check that the plans the declared safety class requires have been written.

    IEC 62304 §5.1 requires a development plan that is maintained, and the
    scaffold ships seven plans as templates. Nothing verified any of them was
    ever filled in: a DHF of untouched placeholders passed every gate.

    Detection compares each plan against the template it came from, section by
    section. Sentinel text ("starter content") only appears in one of the seven
    templates, so a marker-based check would miss six — and deleting a banner is
    not the same as writing a plan.

    A plan whose every section still matches the template has not been
    maintained, and fails. Individual unchanged sections are reported as
    warnings: a project may legitimately accept some shipped wording, and the
    tool cannot tell that from neglect.
    """
    from dhfkit.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(dhf_path)
    config = adapter._config
    declared = (config.software_safety_class or "").strip().upper()
    required = config.required_activities().get("required_plans") or []

    if not declared:
        return envelope_from("verify plans", {
            "passed": True,
            "declared": None,
            "checked": [],
            "missing": [],
            "unwritten": [],
            "partial": [],
            "skipped": [],
            "warnings": [
                "No software_safety_class declared, so no plans are required yet. "
                "Declare one in global.yaml to activate this check."
            ],
            "summary": "No safety class declared — plan checks are inactive.",
        })

    templates_dir = _plan_templates_dir()
    plans_dir = dhf_path / "documents" / "plans"
    project_name = config.project_name

    checked, missing, unwritten, partial, skipped = [], [], [], [], []

    for stem in sorted(required):
        filename = f"{stem}.md"
        plan_path = plans_dir / filename
        if not plan_path.exists():
            missing.append({"plan": filename})
            continue

        template_path = templates_dir / filename if templates_dir else None
        if template_path is None or not template_path.exists():
            skipped.append({
                "plan": filename,
                "reason": "no shipped template to compare against",
            })
            continue

        project_sections = _sections(_strip_banner(plan_path.read_text(encoding="utf-8")))
        template_sections = _sections(_strip_banner(
            _fill_placeholders(template_path.read_text(encoding="utf-8"), project_name)
        ))

        untouched = [
            heading for heading, body in template_sections.items()
            if project_sections.get(heading, "").strip() == body.strip() and body.strip()
        ]
        comparable = [h for h, b in template_sections.items() if b.strip()]

        if comparable and len(untouched) == len(comparable):
            unwritten.append({"plan": filename, "sections": len(untouched)})
        elif untouched:
            partial.append({"plan": filename, "sections": untouched})
        else:
            checked.append({"plan": filename})

    all_plans = {p.name for p in plans_dir.glob("*.md")} if plans_dir.is_dir() else set()
    not_required = sorted(all_plans - {f"{s}.md" for s in required})

    warnings = [
        f"{entry['plan']}: {len(entry['sections'])} section(s) still match the "
        f"shipped template — {', '.join(entry['sections'][:3])}"
        + ("…" if len(entry["sections"]) > 3 else "")
        for entry in partial
    ]
    errors = (
        [f"{e['plan']} is required for Class {declared} and is absent." for e in missing]
        + [
            f"{e['plan']} is unchanged from the template — §5.1 requires a plan "
            f"that is maintained, not one that was scaffolded."
            for e in unwritten
        ]
    )

    passed = not errors
    return envelope_from("verify plans", {
        "passed": passed,
        "declared": declared,
        "checked": checked,
        "missing": missing,
        "unwritten": unwritten,
        "partial": partial,
        "skipped": skipped + [{"plan": p, "reason": f"not required for Class {declared}"}
                             for p in not_required],
        "warnings": warnings,
        "errors": errors,
        "summary": (
            f"Class {declared}: {len(checked)} plan(s) written, "
            f"{len(missing)} missing, {len(unwritten)} unchanged."
        ),
    })


def _plan_templates_dir() -> Optional[Path]:
    try:
        import dhfkit
        candidate = Path(dhfkit.__file__).resolve().parent / "templates" / "plans"
        return candidate if candidate.is_dir() else None
    except Exception:  # noqa: BLE001 — absence is reported, not fatal
        return None


def _fill_placeholders(text: str, project_name: str) -> str:
    """Apply the substitutions the scaffold makes, so comparison is like-for-like."""
    return (
        text.replace("{{project_name}}", project_name)
        .replace("{{medharness_repo}}", "itercharles/MedHarness")
        .replace("{{primary_test_tool}}", "pytest")
    )
