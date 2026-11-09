"""`verify impact`: whether a CR's record of its impact holds for the branch that carries it.

`build plan` writes `impact_analysis`, `reviewed_items` and `affected_risk_items` onto the CR and checks them
before it finishes; this runs the same judgement on whatever is on the machine, so an agent that wrote them
itself, or a person, finds out before CI does. It also holds the branch to the CR's `affected_items`, both ways,
which `build plan` cannot: it writes that list from the branch afterwards.
"""

from __future__ import annotations

from pathlib import Path

from dhfkit.store import open_store
from medharness.services import design_validation, git
from medharness.services.envelope import envelope_from


def _failed(cr_id: str, since_ref: str, summary: str, field: str, issue: str, fix: str) -> dict:
    return envelope_from("verify impact", {
        "cr_id": cr_id, "since_ref": since_ref, "passed": False, "summary": summary,
        "errors": [f"{field}: {issue}"], "findings": [{"field": field, "issue": issue, "fix": fix}],
    })


def judge_branch(
    cr_id: str,
    cr_item: dict,
    dhf_item_changes: dict[str, list[str]],
    code_changes: dict[str, list[str]],
    *,
    since_ref: str,
    code_paths: tuple[str, ...] = (),
) -> list[dict]:
    """What the branch does that the CR's `affected_items` does not say, and the reverse.

    The two change sets are ``{created, updated, deleted}``: item ids and file paths. The CR itself
    is exempt from listing itself. With ``code_paths``, at least one file under them must have changed.
    """
    findings: list[dict] = []
    if code_paths and not any(code_changes[bucket] for bucket in ("created", "updated", "deleted")):
        findings.append({
            "field": "code_branch",
            "issue": f"No product code changes found under {', '.join(code_paths)} since {since_ref}.",
            "fix": "Add the implementation changes on the same branch before opening a PR.",
        })

    changed = {uid for bucket in ("created", "updated", "deleted") for uid in dhf_item_changes[bucket]}
    promised = set(cr_item.get("affected_items") or [])
    if unchanged := sorted(promised - changed):
        findings.append({
            "field": "dhf_branch",
            "issue": f"{cr_id} lists {', '.join(unchanged)} in affected_items, "
                     f"but the branch does not change them since {since_ref}.",
            "fix": "Make the change the CR proposed, or update affected_items to match what this CR actually touches.",
        })
    elif not promised and not changed:
        findings.append({
            "field": "dhf_branch",
            "issue": f"No DHF item YAML changes found on the branch since {since_ref}, "
                     f"and {cr_id} lists no affected_items to check against.",
            "fix": "Run `build plan` so the CR records what it affects.",
        })
    if unlisted := sorted(changed - promised - {cr_id}):
        findings.append({
            "field": "dhf_branch",
            "issue": f"The branch changes {', '.join(unlisted)} since {since_ref}, "
                     f"but {cr_id} does not list them in affected_items.",
            "fix": f"Add them: medharness item update {cr_id} --data '{{\"affected_items\": [...]}}' "
                   f"— or revert the changes this CR should not make.",
        })
    return findings


def verify_impact(repo_root: Path, dhf_path: Path, cr_id: str, *, since_ref: str | None = None,
                  code_paths: tuple[str, ...] = ()) -> dict:
    since_ref = git.resolve_since_ref(repo_root, since_ref)
    store = open_store(dhf_path)
    if not store.tracks_files:
        return envelope_from("verify impact", {
            "cr_id": cr_id, "since_ref": since_ref, "passed": False,
            "summary": f"{cr_id}: the items are not files in Git, so there is no diff to check.",
            "errors": [git.FILES_IN_GIT.format(command="verify impact", store=store.store_type)],
        })
    cr_item = store.get_item(cr_id)
    if cr_item is None:
        return _failed(cr_id, since_ref, f"{cr_id}: not in the DHF.", "cr_item",
                       f"CR item '{cr_id}' is not in the DHF.", f"Create {cr_id}, or name the CR the branch is for.")
    try:
        changed = git.collect_dhf_item_changes(repo_root, since_ref, dhf_path)
        code_changed = git.collect_code_changes(repo_root, since_ref, dhf_path)
        code_changes = git.collect_path_changes(repo_root, since_ref, *code_paths) if code_paths else {
            "created": [], "updated": [], "deleted": [],
        }
    except git.DiffUnavailable as exc:
        return _failed(
            cr_id, since_ref, f"{cr_id}: could not read the diff against {since_ref}.", "diff_unavailable",
            f"Could not diff against {since_ref}: {exc}.",
            f"Fetch it (`git fetch origin main`), or pass --since-ref with a ref that exists here. "
            f"A shallow clone or a repo with no remote has no {since_ref}.",
        )

    findings = [
        *([] if design_validation.triage_rejected(cr_item)
          else judge_branch(cr_id, cr_item, changed, code_changes, since_ref=since_ref, code_paths=code_paths)),
        *design_validation.impact_findings(dhf_path, cr_id, changed, code_changed),
    ]
    warnings = [
        *design_validation.check_verification_quality(dhf_path, changed),
        *design_validation.check_near_duplicates(dhf_path, changed),
        *design_validation.check_large_edits(repo_root, since_ref, dhf_path, cr_id),
        *design_validation.check_test_points_follow_requirements(repo_root, dhf_path, since_ref),
    ]
    return envelope_from("verify impact", {
        "cr_id": cr_id,
        "since_ref": since_ref,
        "passed": not findings,
        "summary": f"{cr_id}: {len(findings)} finding(s) in its impact record since {since_ref}.",
        "errors": [f"{f['field']}: {f['issue']}" for f in findings],
        "warnings": [f"{w['code']}: {w['message']}" for w in warnings],
        "findings": findings,
    })
