"""`verify dhf` — schema, links, cycles and coverage across the DHF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from medharness.services.envelope import gate_result
from medharness.services.traceability import analyse


def ci_structural_gate(
    dhf_path: Path,
    strict: bool = False,
) -> dict[str, Any]:
    """Run the DHF structural validation gate.

    Returns a dict with ``passed`` (bool) and ``results`` keyed by
    ``schema``, ``traceability``, and ``coverage``.  Each result entry
    is a dict with its own ``passed`` and details.
    """
    from dhfkit.store import open_store

    adapter = open_store(dhf_path)

    passed = True
    results: dict[str, Any] = {
        "coverage_gaps": [],
        "verification_gaps": [],
    }

    r = adapter.validate_schema()
    results["schema"] = {
        "passed": r.get("valid", True),
        "valid": r.get("valid", True),
        "item_count": r.get("item_count", 0),
        "errors": r.get("errors", []),
    }
    if not r.get("valid", True):
        passed = False

    try:
        tr = analyse(adapter)
    except Exception as exc:  # noqa: BLE001
        # Reporting zero findings on a DHF the analysis could not read is a
        # pass indistinguishable from a sound one. Say it could not run.
        tr = {}
        results["traceability_error"] = f"traceability could not be checked: {exc}"
        passed = False
    required = tr.get("required", {})
    coverage_list = tr.get("coverage", [])
    dangling = tr.get("dangling", [])
    cycles = tr.get("cycles", [])
    mistyped = tr.get("mistyped", [])
    results["traceability"] = {
        "passed": required.get("passed", True)
        and not dangling
        and not mistyped
        and not cycles
        and all(c.get("passed", True) for c in coverage_list),
        "required": required,
        "dangling": dangling,
        "mistyped": mistyped,
        "cycles": cycles,
        "coverage": coverage_list,
        "summary": tr.get("summary", ""),
    }
    if not required.get("passed", True):
        passed = False
    # A link that resolves to nothing is always an error — unlike an uncovered
    # item, it is not a gap in the design but a broken reference.
    if dangling:
        passed = False
    # Same class as a dangling link: a broken reference, not a design gap.
    if cycles or mistyped:
        passed = False
    for c in coverage_list:
        if not c.get("passed", True) and strict:
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

    # verification_criteria gaps: verifiable items missing the field
    _REQUIREMENTS = frozenset(adapter.config.requirement_types())
    verification_gaps = []
    try:
        for item in adapter.list_items():
            uid = item.get("id", "")
            type_code = uid.split("-")[0] if "-" in uid else ""
            if type_code in _REQUIREMENTS:
                vc = str(item.get("verification_criteria") or "").strip()
                if not vc:
                    verification_gaps.append({
                        "id": uid,
                        "type": type_code,
                        # Says the field is optional. Without that, a reader
                        # sees `validate` pass and concludes the gate
                        # is warning about a field the schema never defined.
                        "issue": "verification_criteria is empty — an optional "
                                 "field, but §5.7 verification needs a stated "
                                 "criterion to verify against",
                    })
        results["placeholders"] = _placeholders(adapter)
        results["invalid_statuses"] = _invalid_statuses(adapter)
    except Exception as exc:  # noqa: BLE001
        # Say so. Swallowing this reported "no verification_criteria gaps"
        # on a DHF whose items could not be read — a pass indistinguishable
        # from a clean one.
        results["verification_gaps_error"] = (
            f"verification_criteria could not be checked: {exc}"
        )
    results["verification_gaps"] = verification_gaps

    errors, warnings = _structural_messages(results, strict)
    schema_n = results.get("schema", {}).get("item_count", 0)
    # `errors` is what made the gate fail (docs/interface.md), so a gate cannot
    # carry one and still pass. `passed` was computed before the messages were
    # built, so an error added there — a check that could not run, say — left
    # the two disagreeing.
    passed = passed and not errors
    return gate_result(
        "verify dhf", passed,
        f"{schema_n} item(s) checked; {len(errors)} error(s), {len(warnings)} warning(s).",
        errors=errors, warnings=warnings, results=results,
    )


def _invalid_statuses(adapter) -> list[dict]:
    """Items whose `status` is not a state of their type: anyone can write one by hand."""
    found = []
    for item in adapter.list_items():
        allowed = adapter.config.valid_states(item.get("type", ""))
        status = item.get("status")
        if status and allowed is not None and status not in allowed:
            found.append({"id": item["id"], "type": item["type"], "status": status, "allowed": sorted(allowed)})
    return found


def _placeholders(adapter) -> list[dict]:
    """Per item, the title and content fields whose text matches one of the config's `placeholder_patterns`."""
    import re

    patterns = [re.compile(p, re.IGNORECASE) for p in adapter.config.placeholder_patterns]
    if not patterns:
        return []
    text_fields = {
        dt.code: [p["name"] for p in dt.properties or []
                  if isinstance(p, dict) and p.get("format") in ("short_text", "long_text")]
        for dt in adapter.config.doc_types
    }
    found = []
    for item in adapter.list_items():
        fields = [
            field for field in text_fields.get(item.get("type"), [])
            if isinstance(item.get(field), str) and any(p.search(item[field]) for p in patterns)
        ]
        if fields:
            found.append({"id": item["id"], "fields": fields})
    return found


def _structural_messages(results: dict, strict: bool) -> tuple[list[str], list[str]]:
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
            f"{d['source']}.{d['field']} → {d['target']}: target does not exist"
        )
    for m in trace.get("mistyped", []):
        errors.append(
            f"{m['source']}.{m['field']} → {m['target']}: {m['found']} is not one of {', '.join(m['expected'])}"
        )
    for cycle in trace.get("cycles", []):

        path = " → ".join(cycle + [cycle[0]]) if len(cycle) > 1 else f"{cycle[0]} → itself"
        errors.append(f"Traceability cycle: {path}")

    # Uncovered items block only under --strict; anywhere else they
    # are a gap in design still to be written, not a broken reference.
    bucket = errors if strict else warnings
    for gap in results.get("coverage_gaps", []):
        bucket.append(
            f"{gap['parent_type']}->{gap['child_type']}: "
            f"{len(gap.get('uncovered') or [])} uncovered"
        )
    for gap in results.get("verification_gaps", []):
        warnings.append(f"{gap['id']}: {gap['issue']}")
    # A status that is no state of its type is a broken record, like a broken link.
    errors.extend(
        f"{s['id']}: status '{s['status']}' is not a state of {s['type']} (one of {', '.join(s['allowed'])})"
        for s in results.get("invalid_statuses", [])
    )
    # Content that still says nothing is design to be written, like an uncovered
    # item: it advises, and blocks under --strict.
    bucket.extend(f"{p['id']}: placeholder text in {', '.join(p['fields'])}" for p in results.get("placeholders", []))
    # A check that could not run is an error, not silence: reporting zero gaps
    # because the items would not load is the same output as a clean DHF.
    if results.get("verification_gaps_error"):
        errors.append(results["verification_gaps_error"])
    if results.get("traceability_error"):
        errors.append(results["traceability_error"])

    return errors, warnings
