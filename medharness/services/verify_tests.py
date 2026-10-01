"""`verify tests` — each requirement verified by the method it declares."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from dhfkit.junit_parser import read_test_evidence
from dhfkit.testing_points import parse_testing_points
from medharness.services.envelope import envelope_from, gate_result


def ci_test_coverage_gate(
    dhf_path: Path,
    junit_paths: list[Path],
    strict: bool = False,
) -> dict[str, Any]:
    """Check requirement coverage from JUnit evidence.

    Checks every requirement type in the config — a role ending in
    ``_requirement``.

    Returns a dict with ``passed`` (bool) and a ``results`` list of
    per-type coverage dicts.

    Every requirement that needs a test must have at least one passing linked test:
    one whose methods are only Inspection, Analysis or Demonstration does not, and is
    listed for sign-off instead. If a requirement declares numbered test points in its ``testing`` field,
    each declared point must also be covered by at least one passing linked test.
    """
    from dhfkit.store import open_store

    if not junit_paths:
        # Declaring a verification method needs no test run, so returning here
        # skipped a check that had nothing to do with the missing evidence.
        methods = validate_verification_completeness(
            dhf_path, [], enforce_test_evidence=False,
        )
        md = methods.get("details", methods)
        missing = md.get("missing_method", [])
        # Missing evidence still fails: this gate's job is to confirm the tests
        # ran and passed, and it cannot. The method check is extra, not a
        # replacement — reporting FAIL on stderr while exiting 0 was the bug
        # this replaced.
        return gate_result(
            "verify tests", False,
            "No JUnit evidence given — test results were not checked.",
            errors=(
                [f"{g['id']}: no verification_method declared" for g in missing]
                if strict else
                ["No JUnit files found — pass --junit."]
            ),
            warnings=(
                [] if strict else
                [f"{g['id']}: no verification_method declared" for g in missing]
            ),
            results=[],
            missing_method=missing,
            unverified_test=[],
            manual_review_required=md.get("manual_review_required", []),
        )

    evidence = read_test_evidence(junit_paths)
    covered_reqs: set[str] = set()
    covered_pairs: set[tuple[str, str]] = set()
    for test in evidence:
        if test.status != "PASS":
            continue
        covered_reqs.update(test.links)
        covered_pairs.update((link, point) for link in test.links for point in test.testing_points)

    adapter = open_store(dhf_path)
    all_items = adapter.list_items()

    passed = True
    results: list[dict] = []
    testing_points: list[dict] = []

    for rt in adapter.config.requirement_types():
        prefix = adapter.config.get_doc_type(rt).prefix
        req_items = [it for it in all_items if it["id"].startswith(prefix) and _needs_a_test(it)]
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
        for row in results if not row.get("passed")
    ] + [
        f"{tp['req_id']}: test points {', '.join(tp['uncovered'])} uncovered"
        for tp in testing_points if not tp["passed"]
    ]
    warnings: list[str] = []
    covered = sum(r.get("covered", 0) for r in results)
    total = sum(r.get("total", 0) for r in results)

    # Coverage alone reads every requirement as one that should have a test. A
    # requirement verified by Inspection has none by design, and asking the two
    # questions from separate gates produced two answers: this one called it
    # uncovered while `verify verification` called it manual sign-off. Neither
    # was wrong about its half.
    methods = validate_verification_completeness(
        dhf_path, list(junit_paths),
        enforce_test_evidence=bool(junit_paths),
    )
    md = methods.get("details", methods)
    errors += [
        f"{gap['id']}: no verification_method declared"
        for gap in md.get("missing_method", [])
    ] + [
        f"{gap['id']}: declares Test but no passing case is linked"
        for gap in md.get("unverified_test", [])
    ]
    warnings += [
        f"{gap['id']}: verified by {', '.join(gap.get('methods', []))} — needs a "
        f"human sign-off record"
        for gap in md.get("manual_review_required", [])
    ]
    if not junit_paths:
        warnings.append(
            "No JUnit evidence given, so test results were not checked — "
            "pass --junit to verify them."
        )
    # A test that links an ID the DHF does not have is evidence for nothing: the item
    # was renamed or deleted, or the link is a typo. Like a missing method, it warns
    # until asked to block.
    known = {item["id"] for item in all_items}
    stale: dict[str, list[str]] = {}
    for test in evidence:
        if test.status != "SKIP":
            for link in test.links:
                if link not in known:
                    stale.setdefault(link, []).append(test.name)
    unknown_links = [{"id": uid, "tests": sorted(set(names))} for uid, names in sorted(stale.items())]
    (errors if strict else warnings).extend(
        f"{u['id']}: linked by {', '.join(repr(n) for n in u['tests'][:3])} but not in the DHF" for u in unknown_links
    )
    if strict and unknown_links:
        passed = False
    # A requirement with no declared method is a §5.7 gap, but a project that
    # adopted this before the field existed has one on every item. It warns
    # until asked to block, the call `verify dhf` makes for coverage gaps.
    if strict:
        passed = passed and not md.get("missing_method")
    else:
        warnings += [
            f"{gap['id']}: no verification_method declared — pass "
            f"--strict to block on this"
            for gap in md.get("missing_method", [])
        ]
        errors = [e for e in errors if "no verification_method declared" not in e]
    passed = passed and not md.get("unverified_test")

    return gate_result(
        "verify tests", passed,
        f"{covered}/{total} requirement(s) covered by passing tests.",
        errors=errors, warnings=warnings,
        results=results,
        testing_points=testing_points,
        unknown_links=unknown_links,
        missing_method=md.get("missing_method", []),
        unverified_test=md.get("unverified_test", []),
        manual_review_required=md.get("manual_review_required", []),
    )


_NON_TEST_METHODS = frozenset({"Inspection", "Analysis", "Demonstration"})


def _methods(item: dict) -> list[str]:
    """The verification methods an item declares, from either a list or a comma-separated string."""
    raw = item.get("verification_method")
    if isinstance(raw, str):
        return [m.strip() for m in raw.split(",") if m.strip()]
    if isinstance(raw, list):
        return [str(m).strip() for m in raw if str(m).strip()]
    return []


def _needs_a_test(item: dict) -> bool:
    """A requirement verified only by Inspection, Analysis or Demonstration has no test by design.

    One with no declared method is expected to have one: nothing says otherwise.
    """
    methods = _methods(item)
    return not methods or "Test" in methods


def validate_verification_completeness(
    dhf_path: Path,
    junit_paths: list[Path] = (),
    req_types: tuple[str, ...] = (),
    enforce_test_evidence: bool = False,
    item_ids: Iterable[str] | None = None,
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
        req_types: Requirement type codes to check (default: every
            requirement type in the config).
        item_ids: Restrict the scan to these items. A CR-scoped caller must pass
            them; scanning the whole DHF charges one CR with every pre-existing
            requirement that never declared a method.

    Returns:
        {
          "passed": bool,
          "missing_method": [{"id": str, "type": str, "title": str}],
          "unverified_test": [{"id": str, "type": str, "title": str}],
          "manual_review_required": [{"id": str, "type": str, "title": str, "methods": list[str]}],
          "summary": str,
        }
    """
    from dhfkit.store import open_store

    adapter = open_store(dhf_path)
    all_items = adapter.list_items()
    if item_ids is not None:
        in_scope = set(item_ids)
        all_items = [it for it in all_items if it.get("id") in in_scope]
    config = adapter.config

    # Resolve configured prefixes so custom prefixes (e.g. SYSREQ-) are handled correctly.
    default_types = req_types or tuple(config.requirement_types())
    prefix_to_code: dict[str, str] = {}
    for rt in default_types:
        dt = config.get_doc_type(rt)
        if dt:
            prefix_to_code[dt.prefix] = rt

    # Requirement IDs covered by passing tests
    covered_by_test = {
        link for test in read_test_evidence(junit_paths) if test.status == "PASS" for link in test.links
    }

    missing_method: list[dict] = []
    unverified_test: list[dict] = []
    manual_review_required: list[dict] = []

    for item in all_items:
        uid = item.get("id", "")
        type_code = next((code for pfx, code in prefix_to_code.items() if uid.startswith(pfx)), None)
        if not type_code:
            continue

        methods = _methods(item)

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
