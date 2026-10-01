"""Deterministic post-design validation.

Runs structural checks against the DHF state, returning a list of structured
error dicts suitable for assembling a fix-only LLM prompt.

Checks:
- Schema validity of all DHF items
- Required traceability rules, coverage gaps
- verification_criteria present on verifiable items touched by `build plan`
"""

from __future__ import annotations

from pathlib import Path

import yaml

from dhfkit.exceptions import ValidationError
from medharness.services.traceability import analyse



def _verifiable_types(dhf_path: Path) -> frozenset[str]:
    import dhfkit.api as api

    return frozenset(api.get_config(dhf_path).requirement_types())

_VAGUE_VC_PHRASES: frozenset[str] = frozenset({
    "works correctly",
    "behaves as expected",
    "behaves correctly",
    "functions properly",
    "functions correctly",
    "operates correctly",
    "operates as expected",
    "as expected",
    "should work",
    "is correct",
    "properly implemented",
    "implemented correctly",
})

def cascade_children(config) -> dict[str, list[str]]:
    """Parent type code → the child type codes a parent `build plan` creates must get.

    Read from the project's `traceability_matrices`. A type is a parent when it sits
    below the head of some chain: the head is where requirements enter, written by
    people, so a head with nothing under it yet is not a gap `build plan` left.
    """
    from medharness.services.traceability import coverage_matrices

    chains = [m.path for m in coverage_matrices(config)]
    below = {code for chain in chains for code in chain[1:]}
    children: dict[str, list[str]] = {}
    for chain in chains:
        for parent, child in zip(chain, chain[1:]):
            if parent in below and child not in children.setdefault(parent, []):
                children[parent].append(child)
    return children


def _load_api():
    try:
        import dhfkit.api as _api
    except ImportError as exc:
        return None, [{
            "field": "environment",
            "issue": f"Could not import dhfkit.api: {exc}",
            "fix": "Ensure medharness is installed and dhfkit is on the Python path.",
        }]
    return _api, []


def _validate_schema_and_traceability(_api, dhf_path: Path) -> list[dict]:
    errors: list[dict] = []

    try:
        schema_result = _api.validate_schema(dhf_path)
    except (FileNotFoundError, ValidationError, ValueError, yaml.YAMLError) as exc:
        errors.append({
            "field": "schema",
            "issue": f"Schema validation raised: {exc}",
            "fix": "Inspect DHF/items/ for malformed YAML and fix the offending file.",
        })
        schema_result = {"valid": False, "errors": []}

    if not schema_result.get("valid"):
        for msg in schema_result.get("errors", []) or [
            "Schema validation failed without a specific message."
        ]:
            errors.append({
                "field": "schema",
                "issue": str(msg),
                "fix": "Fix the offending DHF item via "
                       "`medharness --dhf DHF item update <ITEM_ID> --data '<JSON>'`.",
            })

    try:
        from dhfkit.store import open_store
        trace_result = analyse(open_store(dhf_path))
    except (FileNotFoundError, ValidationError, ValueError, yaml.YAMLError) as exc:
        errors.append({
            "field": "traceability",
            "issue": f"Traceability validation raised: {exc}",
            "fix": "Run `medharness --dhf DHF verify dhf` locally to reproduce.",
        })
        trace_result = {"passed": True}

    # Broken references, unlike coverage gaps, are never "still to be written":
    # `verify dhf` fails on them, so a run that reports ok here fails in CI.
    for d in trace_result.get("dangling", []):
        errors.append({
            "field": f"traceability.dangling.{d['field']}",
            "issue": f"{d['source']}.{d['field']} → {d['target']}: target does not exist",
            "fix": (
                f"Point {d['source']}'s `{d['field']}` at an item that exists, "
                f"or create {d['target']}."
            ),
        })
    for cycle in trace_result.get("cycles", []):
        path = " → ".join(cycle + [cycle[0]]) if len(cycle) > 1 else f"{cycle[0]} → itself"
        errors.append({
            "field": "traceability.cycle",
            "issue": f"Traceability cycle: {path}",
            "fix": "Remove one of the links so the chain points up the V-model only.",
        })

    if not trace_result.get("passed", True):
        required = trace_result.get("required") or {}
        for failure in required.get("failures", []):
            errors.append({
                "field": f"traceability.required.{failure.get('field', 'links')}",
                "issue": (
                    f"{failure.get('id')}: "
                    f"{failure.get('issue', 'required traceability missing')}"
                ),
                "fix": (
                    f"Update {failure.get('id')} so its `{failure.get('field')}` "
                    f"references a {failure.get('target_type')} item "
                    f"(need at least {failure.get('min_count', 1)})."
                ),
            })

        for coverage in trace_result.get("coverage", []):
            if coverage.get("passed"):
                continue
            for uncovered in coverage.get("uncovered", []):
                errors.append({
                    "field": f"traceability.coverage.{coverage.get('parent_type')}",
                    "issue": (
                        f"{uncovered} ({coverage.get('parent_type')}) has no covering "
                        f"{coverage.get('child_type')} child."
                    ),
                    "fix": (
                        f"Create a {coverage.get('child_type')} item linked to "
                        f"{uncovered}, or remove {uncovered} if it should not exist."
                    ),
                })

    return errors


def _list_items(_api, dhf_path: Path, field: str) -> tuple[list[dict], list[dict]]:
    try:
        return _api.list_items(dhf_path), []
    except (FileNotFoundError, ValidationError, ValueError, yaml.YAMLError) as exc:
        return [], [{
            "field": field,
            "issue": f"Could not enumerate DHF items to verify expectations: {exc}",
            "fix": "Run `medharness --dhf DHF item list` locally to debug.",
        }]


def _item_has_verification_criteria(item: dict | None) -> bool:
    return bool(str((item or {}).get("verification_criteria") or "").strip())


def _validate_cascade_completeness(
    created_ids: list[str],
    by_id: dict[str, dict],
    config,
) -> list[dict]:
    """Check that newly created parent-tier items have at least one child-tier
    item anywhere in the current DHF that links back to them.

    Searches by_id (the full post-`build plan` DHF state) rather than only the
    items touched in this run, so that child items created or updated in the same
    `build plan` pass are found regardless of how the caller bucketed them.
    """
    from medharness.services.traceability import link_targets

    errors: list[dict] = []
    cascade = cascade_children(config)

    for uid in created_ids:
        doc_type = config.doc_type_of(uid)
        child_codes = cascade.get(doc_type.code) if doc_type else None
        if not child_codes or by_id.get(uid) is None:
            continue
        parent_type = doc_type.code
        child_prefixes = tuple(dt.prefix for dt in (config.get_doc_type(c) for c in child_codes) if dt)

        covered = any(
            cid.startswith(child_prefixes) and uid in link_targets(item, config, parent_type)
            for cid, item in by_id.items()
        )
        if not covered:
            errors.append({
                "field": f"cascade.{uid}",
                "issue": (
                    f"'{uid}' ({parent_type}) was created by `build plan` but no "
                    f"{' or '.join(child_codes)} item in the DHF links back to it."
                ),
                "fix": (
                    f"Create a {' or '.join(child_codes)} item that links to '{uid}', "
                    "or confirm this tier is explicitly out of scope for this CR."
                ),
            })
    return errors


def validate_dhf_structure(dhf_path: Path) -> list[dict]:
    """Run schema and traceability checks only — no item-level or reconciliation logic.

    Used as a pre-flight inside `build code` to surface structural DHF gaps
    before the LLM runs, without triggering false positives from reconciliation
    checks that require a non-empty created_ids list.
    """
    _api, errors = _load_api()
    if _api is None:
        return errors
    errors.extend(_validate_schema_and_traceability(_api, dhf_path))
    return errors


def _check_cr_workflow_fields(_api, dhf_path: Path, cr_id: str) -> list[dict]:
    """The triage decision `build plan` is supposed to leave behind.

    Nothing but the prompt writes it, so a run that skipped a step reported
    success and the omission only surfaced at the closure gate, releases later.
    Reported here so the fix pass can correct it in the same run.
    """
    try:
        cr_item = _api.get_item(dhf_path, cr_id) or {}
    except Exception as exc:  # noqa: BLE001 — reported, not swallowed
        return [{
            "field": "cr_item",
            "issue": f"CR item '{cr_id}' could not be read: {exc}",
            "fix": f"Check that {cr_id} exists in the DHF.",
        }]

    if not cr_item:
        return [{
            "field": "cr_item",
            "issue": f"CR item '{cr_id}' is not in the DHF.",
            "fix": f"Create {cr_id} before running `build plan`.",
        }]

    # A rejected CR stops at Step 1 and produces no cascade, so the check does not apply.
    if str(cr_item.get("status") or "") == "rejected":
        return []

    errors: list[dict] = []
    triage = cr_item.get("triage_result")
    if not isinstance(triage, dict) or triage.get("verdict") != "approved":
        errors.append({
            "field": "triage_result",
            "issue": (
                f"{cr_id} has no approved `triage_result`; Step 1 records the "
                f"triage decision and it was not written."
            ),
            "fix": (
                f"medharness --dhf DHF item update {cr_id} --data "
                f"'{{\"triage_result\": {{\"verdict\": \"approved\", "
                f"\"complexity\": \"<small|medium|large>\", "
                f"\"affected_subsystems\": [\"<name>\"], \"related_crs\": [], "
                f"\"notes\": \"<why approved and the key constraint>\"}}}}'"
            ),
        })

    return errors


def validate_generate_dhf(
    cr_id: str,
    dhf_path: Path,
    changed_items: dict[str, list[str]],
) -> list[dict]:
    """Validate `build plan` output without relying on a spec artifact."""
    _api, errors = _load_api()
    if _api is None:
        return errors

    errors.extend(_validate_schema_and_traceability(_api, dhf_path))
    errors.extend(_check_cr_workflow_fields(_api, dhf_path, cr_id))

    listed_items, item_errors = _list_items(_api, dhf_path, "changed_items")
    errors.extend(item_errors)
    by_id = {item["id"]: item for item in listed_items}

    created_ids: list[str] = []
    seen_created: set[str] = set()
    for uid in changed_items.get("created", []):
        if uid not in seen_created:
            seen_created.add(uid)
            created_ids.append(uid)

    seen: set[str] = set()
    ordered_changed_ids: list[str] = []
    for bucket in ("created", "updated"):
        for uid in changed_items.get(bucket, []):
            if uid in seen:
                continue
            seen.add(uid)
            ordered_changed_ids.append(uid)

    verifiable = _verifiable_types(dhf_path)
    for idx, uid in enumerate(ordered_changed_ids):
        item = by_id.get(uid)
        if item is None:
            errors.append({
                "field": f"changed_items[{idx}]",
                "issue": (
                    f"`build plan` reported changed item '{uid}', "
                    "but it is not present in the current DHF item list."
                ),
                "fix": (
                    f"Recreate or restore '{uid}', or remove the partial change so the "
                    "branch and DHF state match."
                ),
            })
            continue

        if item.get("type") in verifiable and not _item_has_verification_criteria(item):
            errors.append({
                "field": f"changed_items[{idx}].verification_criteria",
                "issue": (
                    f"`build plan` changed verifiable item '{uid}', "
                    "but the DHF item has no `verification_criteria`."
                ),
                "fix": (
                    f"Update '{uid}' and add a `verification_criteria` field "
                    "with a measurable pass/fail criterion."
                ),
            })

    errors.extend(_validate_cascade_completeness(created_ids, by_id, _api.get_config(dhf_path)))
    errors.extend(_unreviewed_impact(dhf_path, cr_id, changed_items))
    return errors


def _unreviewed_impact(dhf_path: Path, cr_id: str, changed_items: dict[str, list[str]]) -> list[dict]:
    """The same dependents `verify changes` will fail on, found while the model can still fix them."""
    from dhfkit.store import open_store
    from medharness.services.impact import unreviewed_dependents

    store = open_store(dhf_path)
    unreviewed = unreviewed_dependents(store, store.get_item(cr_id), {
        "created": changed_items.get("created", []), "updated": changed_items.get("updated", []),
        "deleted": changed_items.get("deleted", []),
    })
    return [{
        "field": f"impact.{dependent}",
        "issue": f"{dependent} depends on {', '.join(origins)}, which `build plan` changed, "
                 f"but {dependent} is neither changed nor listed in {cr_id}'s reviewed_items.",
        "fix": f"Update {dependent} to follow the change, or if it needs none run "
               f"`medharness item update {cr_id} --data '{{\"reviewed_items\": [..., \"{dependent}\"]}}'`.",
    } for dependent, origins in unreviewed.items()]


def check_verification_quality(
    dhf_path: Path,
    changed_items: dict[str, list[str]],
) -> list[dict]:
    """Return warning-level quality issues about verification_criteria content.

    Detects vague, non-measurable criteria on changed verifiable items (CRS, SYS, SRS).
    Does not trigger fix passes — caller surfaces these as warnings only.
    """
    _api, _ = _load_api()
    if _api is None:
        return []

    try:
        listed = _api.list_items(dhf_path)
    except Exception:
        return []

    by_id = {item["id"]: item for item in listed}
    seen: set[str] = set()
    warnings: list[dict] = []

    verifiable = _verifiable_types(dhf_path)
    for uid in (*changed_items.get("created", []), *changed_items.get("updated", [])):
        if uid in seen:
            continue
        seen.add(uid)

        item = by_id.get(uid)
        if item is None or item.get("type") not in verifiable:
            continue

        vc = str((item.get("verification_criteria") or "")).strip()
        if not vc:
            continue  # absence is a hard error caught by validate_generate_dhf

        lower = vc.lower()
        matched = next((p for p in _VAGUE_VC_PHRASES if p in lower), None)
        if matched:
            excerpt = vc[:100] + ("..." if len(vc) > 100 else "")
            warnings.append({
                "code": "vague_verification_criteria",
                "field": f"{uid}.verification_criteria",
                "message": (
                    f"{uid}: verification_criteria may be vague (matched '{matched}'). "
                    f"State a measurable outcome, threshold, or pass/fail condition. "
                    f'Current: "{excerpt}"'
                ),
            })

    return warnings
