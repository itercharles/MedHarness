"""`verify dhf` — schema, links, cycles and coverage across the DHF."""

from __future__ import annotations

import re
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

    results: dict[str, Any] = {
        "coverage_gaps": [],
        "verification_gaps": [],
    }

    r = adapter.validate_schema()
    results["schema"] = {
        "passed": r["valid"],
        "valid": r["valid"],
        "item_count": r["item_count"],
        "errors": r["errors"],
    }

    try:
        tr = analyse(adapter)
    except Exception as exc:  # noqa: BLE001
        # Reporting zero findings on a DHF the analysis could not read is a
        # pass indistinguishable from a sound one. Say it could not run.
        tr = {}
        results["traceability_error"] = f"traceability could not be checked: {exc}"
    coverage_list = tr.get("coverage", [])
    results["traceability"] = {
        "passed": tr.get("passed", True),
        "required": tr.get("required", {}),
        "dangling": tr.get("dangling", []),
        "mistyped": tr.get("mistyped", []),
        "cycles": tr.get("cycles", []),
        "coverage": coverage_list,
        "summary": tr.get("summary", ""),
    }

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
            uid = item["id"]
            type_code = item["type"]
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

    findings = structural_findings(results, dhf_path, strict)
    errors = [f["issue"] for f in findings if f["severity"] == "error"]
    warnings = [f["issue"] for f in findings if f["severity"] == "warning"]
    schema_n = results.get("schema", {}).get("item_count", 0)
    return gate_result(
        "verify dhf", not errors,
        f"{schema_n} item(s) checked; {len(errors)} error(s), {len(warnings)} warning(s).",
        errors=errors, warnings=warnings, results=results, findings=findings,
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


_ITEM_ID_RE = re.compile(r"^([A-Z]+-\d+)")


def structural_findings(results: dict, dhf_path: Path, strict: bool) -> list[dict]:
    """Every structural finding once: what it is, whether it blocks, and how to fix it.

    ``{kind, severity, field, issue, fix}``. The gate's ``errors`` and ``warnings``,
    the lines `verify dhf` prints and the fix pass of `build plan` are all read from
    this list, so a finding added here reaches all of them. ``fix`` is a command with the
    real ``--dhf`` path where one exists.
    """
    update = f"medharness --dhf {dhf_path} item update"
    found: list[dict] = []

    def add(kind: str, severity: str, field: str, issue: str, fix: str) -> None:
        found.append({"kind": kind, "severity": severity, "field": field, "issue": issue, "fix": fix})

    for err in (results.get("schema") or {}).get("errors") or []:
        match = _ITEM_ID_RE.match(str(err))
        add("schema", "error", "schema", str(err),
            f"{update} {match.group(1)} --data '{{\"<field>\": \"<value>\"}}'" if match
            else "Correct the file the message names, then run `medharness verify dhf`.")

    trace = results.get("traceability") or {}
    for failure in (trace.get("required") or {}).get("failures", []):
        target = failure.get("target_type")
        add("required", "error", f"traceability.required.{failure.get('field') or 'links'}",
            f"{failure.get('id')}: {failure.get('issue')}",
            f"{update} {failure['id']} --data '{{\"{failure['field']}\": [\"<{target} id>\"]}}'"
            if failure.get("direction") == "upstream"
            else f"create a {target} item that links to {failure.get('id')}.")
    for d in trace.get("dangling", []):
        add("dangling", "error", f"traceability.dangling.{d['field']}", dangling_message(d),
            "correct the ID in the source item, or create the target. The link exists but resolves to nothing.")
    for m in trace.get("mistyped", []):
        add("link-type", "error", f"traceability.mistyped.{m['field']}", mistyped_message(m),
            "link to an item of a type the field accepts, or move the link to the field that takes that type.")
    for cycle in trace.get("cycles", []):
        add("cycle", "error", "traceability.cycle", cycle_message(cycle),
            "the V-model is directed. Remove whichever link reverses the chain so each item has an origin.")

    # Uncovered items block only under --strict; anywhere else they
    # are a gap in design still to be written, not a broken reference.
    for gap in results.get("coverage_gaps", []):
        uncovered = gap.get("uncovered") or []
        add("coverage", "error" if strict else "warning", f"traceability.coverage.{gap['parent_type']}",
            f"{gap['parent_type']}->{gap['child_type']}: {len(uncovered)} uncovered",
            f"link a {gap['child_type']} item to each uncovered {gap['parent_type']} "
            f"({', '.join(uncovered[:20])}{', ...' if len(uncovered) > 20 else ''}).")
    for gap in results.get("verification_gaps", []):
        add("verification", "warning", f"{gap['id']}.verification_criteria", f"{gap['id']}: {gap['issue']}",
            f"{update} {gap['id']} --data '{{\"verification_criteria\": \"<how this is verified>\"}}'")
    # A status that is no state of its type is a broken record, like a broken link.
    for bad in results.get("invalid_statuses", []):
        add("status", "error", f"{bad['id']}.status",
            f"{bad['id']}: status '{bad['status']}' is not a state of {bad['type']} (one of {', '.join(bad['allowed'])})",
            f"{update} {bad['id']} --data '{{\"status\": \"{bad['allowed'][0]}\"}}'")
    # Content that still says nothing is design to be written, like an uncovered
    # item: it advises, and blocks under --strict.
    for p in results.get("placeholders", []):
        add("placeholder", "error" if strict else "warning", f"{p['id']}.{p['fields'][0]}",
            f"{p['id']}: placeholder text in {', '.join(p['fields'])}",
            f"{update} {p['id']} --data '{{\"{p['fields'][0]}\": \"<the real text>\"}}'")
    # A check that could not run is an error, not silence: reporting zero gaps
    # because the items would not load is the same output as a clean DHF.
    for key in ("verification_gaps_error", "traceability_error"):
        if results.get(key):
            add("unchecked", "error", key, results[key],
                "run `medharness verify dhf` and read what it reports.")
    return found


def dangling_message(d: dict) -> str:
    return f"{d['source']}.{d['field']} → {d['target']}: target does not exist"


def mistyped_message(m: dict) -> str:
    return f"{m['source']}.{m['field']} → {m['target']}: {m['found']} is not one of {', '.join(m['expected'])}"


def cycle_message(cycle: list[str]) -> str:
    path = " → ".join(cycle + [cycle[0]]) if len(cycle) > 1 else f"{cycle[0]} → itself"
    return f"Traceability cycle: {path}"
