"""Deterministic post-design validation.

Runs structural checks against the DHF state, returning a list of structured
error dicts suitable for assembling a fix-only LLM prompt.

Checks:
- Schema validity of all DHF items
- Required traceability rules, coverage gaps
- verification_criteria present on verifiable items touched by `build plan`
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from dhfkit.exceptions import ValidationError
from dhfkit.store import open_store
from medharness.services.traceability import analyse



def _verifiable_types(dhf_path: Path) -> frozenset[str]:
    return frozenset(open_store(dhf_path).config.requirement_types())

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


def _validate_schema_and_traceability(dhf_path: Path) -> list[dict]:
    errors: list[dict] = []

    try:
        schema_result = open_store(dhf_path).validate_schema()
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


def _list_items(dhf_path: Path, field: str) -> tuple[list[dict], list[dict]]:
    try:
        return open_store(dhf_path).list_items(), []
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
    return _validate_schema_and_traceability(dhf_path)


def _check_cr_workflow_fields(dhf_path: Path, cr_id: str) -> list[dict]:
    """The triage decision `build plan` is supposed to leave behind.

    Nothing but the prompt writes it, so a run that skipped a step reported
    success and the omission only surfaced at the closure gate, releases later.
    Reported here so the fix pass can correct it in the same run.
    """
    try:
        cr_item = open_store(dhf_path).get_item(cr_id) or {}
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

    # A rejected CR stops at Step 2 and produces no cascade, so the check does not apply.
    if str(cr_item.get("status") or "") == "rejected":
        return []

    errors: list[dict] = []
    triage = cr_item.get("triage_result")
    if not isinstance(triage, dict) or triage.get("verdict") != "approved":
        errors.append({
            "field": "triage_result",
            "issue": (
                f"{cr_id} has no approved `triage_result`; Step 2 records the "
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
    errors = _validate_schema_and_traceability(dhf_path)
    errors.extend(_check_cr_workflow_fields(dhf_path, cr_id))

    listed_items, item_errors = _list_items(dhf_path, "changed_items")
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

    errors.extend(_validate_cascade_completeness(created_ids, by_id, open_store(dhf_path).config))
    errors.extend(_unreviewed_impact(dhf_path, cr_id, changed_items))
    errors.extend(_check_impact_analysis(by_id.get(cr_id), listed_items, open_store(dhf_path).config, changed_items))
    return errors


def _unreviewed_impact(dhf_path: Path, cr_id: str, changed_items: dict[str, list[str]]) -> list[dict]:
    """The same dependents `verify changes` will fail on, found while the model can still fix them."""
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
    try:
        listed = open_store(dhf_path).list_items()
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


DIMENSIONS = ("product", "requirements", "architecture", "risk", "soup",
              "test", "regulatory", "security", "usability")
VERDICTS = ("required", "not_required", "follow_up")
_IA_KEYS = ("assumptions", "anchors", "unchanged", "created", "dimensions")
_IA_FIX = ("medharness --dhf DHF item update {cr} --data "
           "'{{\"impact_analysis\": {{\"assumptions\": [], \"anchors\": [], \"unchanged\": [], "
           "\"created\": [], \"dimensions\": [...]}}}}' (shape in the `build plan` prompt)")


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _entries(ia: dict, key: str) -> list[dict]:
    value = ia.get(key)
    return [e for e in value if isinstance(e, dict)] if isinstance(value, list) else []


def impact_analysis_shape_errors(cr_id: str, ia) -> list[dict]:
    """What is wrong with the form of a CR's `impact_analysis`, without reading the DHF."""
    fix = _IA_FIX.format(cr=cr_id)
    if not isinstance(ia, dict):
        return [{"field": "impact_analysis",
                 "issue": f"{cr_id} has no `impact_analysis` mapping; Steps 1-5 record it and it was not written.",
                 "fix": fix}]
    errors = []

    def err(field: str, issue: str) -> None:
        errors.append({"field": f"impact_analysis.{field}", "issue": f"{cr_id}: {issue}", "fix": fix})

    for key in _IA_KEYS:
        if key not in ia:
            err(key, f"`impact_analysis.{key}` is missing (use [] when there is nothing to say).")
        elif not isinstance(ia[key], list):
            err(key, f"`impact_analysis.{key}` must be a list.")
    for i, text in enumerate(ia.get("assumptions") if isinstance(ia.get("assumptions"), list) else []):
        if not _text(text):
            err(f"assumptions[{i}]", f"assumptions[{i}] must be a non-empty string.")
    for key in ("anchors", "unchanged", "created"):
        for i, entry in enumerate(ia.get(key) if isinstance(ia.get(key), list) else []):
            if not isinstance(entry, dict) or not _text(entry.get("id")):
                err(f"{key}[{i}]", f"{key}[{i}] must be a mapping with an `id`.")

    seen: dict[str, int] = {}
    for i, entry in enumerate(ia.get("dimensions") if isinstance(ia.get("dimensions"), list) else []):
        if not isinstance(entry, dict):
            err(f"dimensions[{i}]", f"dimensions[{i}] must be a mapping.")
            continue
        name = entry.get("dimension")
        if name not in DIMENSIONS:
            err(f"dimensions[{i}]", f"dimensions[{i}] names '{name}'; it must be one of {', '.join(DIMENSIONS)}.")
            continue
        seen[name] = seen.get(name, 0) + 1
        if entry.get("verdict") not in VERDICTS:
            err(f"dimensions[{i}]", f"'{name}' has verdict '{entry.get('verdict')}'; use {', '.join(VERDICTS)}.")
        if not _text(entry.get("reason")):
            err(f"dimensions[{i}]", f"'{name}' has no `reason`.")
        if not isinstance(entry.get("items", []), list):
            err(f"dimensions[{i}]", f"'{name}' `items` must be a list of IDs.")
    if isinstance(ia.get("dimensions"), list):
        for name in DIMENSIONS:
            if seen.get(name, 0) != 1:
                err("dimensions", f"dimension '{name}' appears {seen.get(name, 0)} times; each of the nine must appear exactly once.")
    return errors


def impact_analysis_closure_errors(cr_item: dict, items: list[dict], config,
                                   changed_items: dict[str, list[str]]) -> list[dict]:
    """What a well-formed `impact_analysis` still leaves unsaid about the items this run changed."""
    from medharness.services.impact import parents

    cr_id = cr_item["id"]
    ia = cr_item["impact_analysis"]
    by_id = {it["id"]: it for it in items}
    changed = [uid for bucket in ("created", "updated") for uid in changed_items.get(bucket, []) if uid != cr_id]
    created = [uid for uid in changed_items.get("created", []) if uid != cr_id]
    affected = set(cr_item.get("affected_items") or []) | set(changed)
    reviewed = set(cr_item.get("reviewed_items") or [])
    risk_items = set(cr_item.get("affected_risk_items") or [])
    errors = []

    def err(field: str, issue: str, fix: str) -> None:
        errors.append({"field": f"impact_analysis.{field}", "issue": f"{cr_id}: {issue}", "fix": fix})

    def update(**fields) -> str:
        return f"medharness --dhf DHF item update {cr_id} --data '{json.dumps(fields)}'"

    anchors, unchanged = _entries(ia, "anchors"), _entries(ia, "unchanged")
    created_entries = _entries(ia, "created")
    dimensions = _entries(ia, "dimensions")

    named = [e["id"] for e in (*anchors, *unchanged, *created_entries)]
    named += [i for d in dimensions for i in (d.get("items") or []) if isinstance(i, str)]
    for uid in sorted(set(named) - set(by_id)):
        err("ids", f"`impact_analysis` names {uid}, which is not in the DHF.",
            f"Correct or remove {uid} in `impact_analysis` of {cr_id}.")

    for entry in anchors:
        uid = entry["id"]
        if uid not in affected | reviewed:
            err("anchors", f"anchor {uid} is neither changed nor in `reviewed_items`.",
                f"Change {uid}, or list it in `reviewed_items` with an `unchanged` entry, or drop the anchor.")
        if not _text(entry.get("evidence")):
            err("anchors", f"anchor {uid} has no `evidence`.",
                f"Say what found {uid}: a test file and tag, item text, or the search.")

    created_reasons = {e["id"]: e.get("reason") for e in created_entries}
    for uid in created:
        if not _text(created_reasons.get(uid)):
            err("created", f"{uid} was created but has no `created` entry with a reason.",
                f"Add {{\"id\": \"{uid}\", \"reason\": \"why no existing item could be updated\"}} to `impact_analysis.created`.")

    unchanged_reasons = {e["id"]: e.get("reason") for e in unchanged}
    for uid in sorted(reviewed):
        if not _text(unchanged_reasons.get(uid)):
            err("unchanged", f"{uid} is in `reviewed_items` but has no `unchanged` entry with a reason.",
                f"Add {{\"id\": \"{uid}\", \"reason\": \"why it still holds\"}} to `impact_analysis.unchanged`.")

    for entry in dimensions:
        for uid in entry.get("items") or []:
            if uid in by_id and uid not in affected | reviewed | risk_items:
                err("dimensions", f"dimension '{entry['dimension']}' touches {uid}, which is not changed, "
                    f"reviewed or in `affected_risk_items`.",
                    f"Drop {uid} from the dimension, or review it ({update(reviewed_items=['...', uid])}).")

    def role(uid: str) -> str:
        doc_type = config.doc_type_of(uid)
        return (doc_type.role if doc_type else None) or ""

    # Only a changed requirement can stop its parent holding; a design item does not
    # change the requirements it designs.
    up = parents(items, config)
    requirement_types = set(config.requirement_types())
    for uid in changed:
        doc_type = config.doc_type_of(uid)
        if doc_type is None or doc_type.code not in requirement_types:
            continue
        for parent in up.get(uid, []):
            if parent in by_id and parent not in affected | reviewed:
                err("parents", f"{uid} changed but its parent {parent} is neither changed nor in `reviewed_items`.",
                    f"Update {parent} to follow the change, or list it in `reviewed_items` with an `unchanged` entry.")

    missing_risk: dict[str, str] = {}
    for uid in changed:
        if role(uid) in ("risk", "risk_control") and uid not in risk_items:
            missing_risk[uid] = f"{uid} is a changed risk item"
        for control in items:
            if role(control["id"]) != "risk_control" or uid not in (control.get("all_linked_uids") or []):
                continue
            if control["id"] not in risk_items:
                missing_risk.setdefault(control["id"], f"{control['id']} controls {uid}, which changed")
            for linked in control.get("all_linked_uids") or []:
                if role(linked) == "risk" and linked not in risk_items:
                    missing_risk.setdefault(linked, f"{linked} is mitigated by {control['id']}, which controls {uid}")
    for uid, why in sorted(missing_risk.items()):
        err("risk", f"{why}, but {uid} is not in `affected_risk_items`.",
            update(affected_risk_items=sorted(risk_items | {uid})))
    return errors


def _check_impact_analysis(cr_item: dict | None, items: list[dict], config,
                           changed_items: dict[str, list[str]]) -> list[dict]:
    # A rejected CR stops at Step 2; a missing one is `_check_cr_workflow_fields`'s to report.
    if cr_item is None or str(cr_item.get("status") or "") == "rejected":
        return []
    errors = impact_analysis_shape_errors(cr_item["id"], cr_item.get("impact_analysis"))
    return errors or impact_analysis_closure_errors(cr_item, items, config, changed_items)


WITHDRAWN_STATES = {"cancelled", "rejected"}


def check_near_duplicates(dhf_path: Path, changed_items: dict[str, list[str]]) -> list[dict]:
    """Warnings for created items that read like an existing item of the same type.

    The CR being planned is created by intake, not by the model, and a withdrawn item is
    not something to update instead, so neither is compared.
    """
    from medharness.services.impact import NEAR_DUPLICATE_RATIO, closest_same_type

    try:
        items = open_store(dhf_path).list_items()
    except Exception:
        return []
    by_id = {it["id"]: it for it in items}
    created = set(changed_items.get("created", []))
    withdrawn = {it["id"] for it in items if str(it.get("status") or "") in WITHDRAWN_STATES}
    warnings = []
    for uid in sorted(created):
        if uid not in by_id or by_id[uid].get("type") == "CR":
            continue
        closest = closest_same_type(by_id[uid], items, created | withdrawn)
        if closest and closest[1] >= NEAR_DUPLICATE_RATIO:
            warnings.append({
                "code": "possible_duplicate",
                "field": uid,
                "message": f"{uid} reads like {closest[0]} (similarity {closest[1]:.2f}); "
                           f"update {closest[0]} instead if it is the same requirement.",
            })
    return warnings


LARGE_EDIT_LINES = 40


def check_large_edits(repo_root: Path, since_ref: str) -> list[dict]:
    """Warnings for existing items that gained more than ``LARGE_EDIT_LINES`` lines.

    A change to one behaviour is a line or two; a large addition usually means the item
    absorbed a second behaviour that deserves its own.
    """
    from medharness.services import git

    try:
        updated = git.collect_path_changes(repo_root, since_ref, "DHF/items/")["updated"]
        added = git.added_line_counts(repo_root, since_ref, *updated) if updated else {}
    except git.DiffUnavailable:
        return []
    return [
        {
            "code": "large_edit",
            "field": Path(path).stem,
            "message": f"{Path(path).stem} gained {count} lines; a change to one behaviour is usually a line or two. "
                       f"Check it has not taken on a second behaviour that needs its own item.",
        }
        for path, count in sorted(added.items()) if count > LARGE_EDIT_LINES
    ]


def check_test_points_follow_requirements(repo_root: Path, dhf_path: Path, since_ref: str) -> list[dict]:
    """Warnings for requirements whose statement or criteria changed while `testing` did not.

    A changed expectation edits its test point, and a new case adds one; leaving
    `testing` alone means the tests are still held to the old behaviour.
    """
    import yaml

    from medharness.services import git

    try:
        requirement_types = _verifiable_types(dhf_path)
        by_id = {it["id"]: it for it in open_store(dhf_path).list_items()}
        updated = git.collect_path_changes(repo_root, since_ref, "DHF/items/")["updated"]
    except Exception:
        return []
    warnings = []
    for path in sorted(updated):
        uid = Path(path).stem
        if by_id.get(uid, {}).get("type") not in requirement_types:
            continue
        try:
            before = yaml.safe_load(git.file_at_branch_point(repo_root, since_ref, path) or "") or {}
            after = yaml.safe_load((repo_root / path).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError, git.DiffUnavailable):
            continue
        said_more = any(before.get(f) != after.get(f) for f in ("content", "verification_criteria"))
        if said_more and before.get("testing") == after.get("testing"):
            warnings.append({
                "code": "test_points_unchanged",
                "field": uid,
                "message": f"{uid} changed what it requires but its `testing` points did not. "
                           f"Edit the point whose expectation changed, or add the next `T<n>` for a new case.",
            })
    return warnings
