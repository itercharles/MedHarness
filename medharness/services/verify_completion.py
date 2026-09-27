"""`verify completion` — a CR delivered what it proposed, created and verified."""

from __future__ import annotations

from pathlib import Path

from medharness.services.envelope import envelope_from
from medharness.services.verify_tests import validate_verification_completeness


# Item types that carry a verification_method field — RISK, RCM, SWDD, etc. do not.
_VERIFIABLE_ITEM_TYPES = frozenset({"CRS", "SRS", "SYS", "SOUP"})


def _check_cr_fields(cr_item: dict, cr_id: str) -> list[dict]:
    """Check that the CR fields `build plan` records are populated.

    Returns a list of issue dicts for each missing or invalid field.
    """
    issues: list[dict] = []
    if not str(cr_item.get("implementation_notes") or "").strip():
        issues.append({
            "field": "implementation_notes",
            "issue": (
                f"CR {cr_id} — implementation_notes is absent; "
                "`build plan` records the implementation plan."
            ),
        })
    if not isinstance(cr_item.get("affected_risk_items"), list):
        issues.append({
            "field": "affected_risk_items",
            "issue": (
                f"CR {cr_id} — affected_risk_items is absent; "
                "`build plan` records the risk impact ([] if none)."
            ),
        })
    triage = cr_item.get("triage_result")
    if not isinstance(triage, dict) or triage.get("verdict") != "approved":
        issues.append({
            "field": "triage_result",
            "issue": (
                f"CR {cr_id} — triage_result.verdict is not 'approved'; "
                "`build plan` records the triage decision."
            ),
        })
    return issues


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
    2. All ``proposed_new_items`` from the CR item exist in the DHF.
    3. All created items of verifiable types have ``verification_method`` set.
    4. Items with ``Test`` method have passing JUnit evidence. Without JUnit paths
       the evidence is not checked, and the result says so rather than passing
       quietly.

    Approval is not checked here. It lives in the pull request, which this gate
    does not read — ``workflow check-approval`` does.

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
    config = adapter.config

    # `build plan` records proposed_new_items on the CR item.
    cr_item = adapter.get_item(cr_id) or {}
    incomplete_cr_fields = _check_cr_fields(cr_item, cr_id)

    raw = cr_item.get("proposed_new_items")
    if raw is None:
        return envelope_from("verify completion", {
            "passed": False,
            "errors": _closure_errors(incomplete=incomplete_cr_fields) + [
                f"CR {cr_id}: proposed_new_items is absent — `build plan` records it, "
                f"or set it with `dhfkit item update {cr_id}`."
            ],
            "cr_id": cr_id,
            "incomplete_cr_fields": incomplete_cr_fields,
            "missing_items": [],
            "verification_gaps": [],
            "unverified_test": [],
            "manual_review_required": [],
            "summary": (
                f"CR {cr_id} — proposed_new_items field is absent from the CR item; "
                "`build plan` records it."
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
    # `build plan` writes affected_items onto the CR item after every run, so
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
    matched_ids: set[str] = set()
    for entry in deduped_proposed:
        item_type = entry["type"]
        title = entry["title"]
        dt = config.get_doc_type(item_type)
        prefix = dt.prefix if dt else f"{item_type}-"
        title_lower = title.lower()
        matches = [
            it["id"] for it in scoped_items
            if it["id"].startswith(prefix)
            and str(it.get("title", "")).strip().lower() == title_lower
        ]
        matched_ids.update(matches)
        found = bool(matches)
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

    # Only the items this CR touched. Scanning the whole DHF charged one CR with
    # every starter and legacy requirement that had never declared a method.
    cr_scope = affected_ids | matched_ids
    verify_result = validate_verification_completeness(
        dhf_path,
        junit_paths=junit_paths,
        req_types=tuple(verifiable),
        enforce_test_evidence=True,
        item_ids=cr_scope,
    )

    passed = not missing_items and verify_result["passed"] and not incomplete_cr_fields

    parts: list[str] = []
    if not junit_paths:
        # `enforce_test_evidence=True` above has nothing to enforce against, so
        # a Test-verified item passes closure on the strength of no evidence.
        # Say it rather than let the PASS imply otherwise.
        parts.append("test evidence not checked (no JUnit given)")
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
