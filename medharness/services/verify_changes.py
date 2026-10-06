"""`verify changes`: whether a branch changes exactly what its CR says it will.

`validate_atomic_branch` reads the branch's diff and the DHF; `judge_branch` takes them as plain
values and decides, so the decision can be tested without a repository.
"""

from __future__ import annotations

from pathlib import Path

from medharness.services import git
from medharness.services.envelope import envelope_from


def validate_atomic_branch(
    repo_root: Path,
    dhf_path: Path,
    cr_id: str,
    *,
    since_ref: str | None = None,
    code_paths: tuple[str, ...] = (),
) -> dict:
    """Read the branch's diff and the CR, then ``judge_branch`` them."""
    from dhfkit.store import open_store

    since_ref = git.resolve_since_ref(repo_root, since_ref)
    store = open_store(dhf_path)
    if not store.tracks_files:
        return envelope_from("verify changes", {
            "cr_id": cr_id,
            "since_ref": since_ref,
            "passed": False,
            "summary": f"{cr_id}: the items are not files in Git, so there is no diff to check.",
            "errors": [git.FILES_IN_GIT.format(command="verify changes", store=store.store_type)],
        })
    try:
        dhf_item_changes = git.collect_dhf_item_changes(repo_root, since_ref)
        code_changes = git.collect_path_changes(repo_root, since_ref, *code_paths) if code_paths else {
            "created": [], "updated": [], "deleted": [],
        }
    except git.DiffUnavailable as exc:
        # Nothing can be judged without the diff, and "no changes" would
        # accuse the CR of breaking a promise nobody checked.
        finding = {
            "field": "diff_unavailable",
            "issue": f"Could not diff against {since_ref}: {exc}.",
            "fix": (
                f"Fetch it (`git fetch origin main`), or pass --since-ref with a ref "
                f"that exists here. A shallow clone or a repo with no remote has no "
                f"{since_ref}."
            ),
        }
        return envelope_from("verify changes", {
            "cr_id": cr_id,
            "since_ref": since_ref,
            "passed": False,
            "summary": f"{cr_id}: could not read the diff against {since_ref}.",
            "errors": [f"{finding['field']}: {finding['issue']}"],
            "findings": [finding],
        })

    # A DHF that will not load must stop the gate: skipping the promise check
    # passed a branch that broke one. A CR that does not exist is not applicable.
    from medharness.services.impact import unreviewed_dependents

    cr_item = store.get_item(cr_id)
    return judge_branch(
        cr_id,
        cr_item,
        dhf_item_changes,
        code_changes,
        since_ref=since_ref,
        code_paths=code_paths,
        unreviewed=unreviewed_dependents(store, cr_item, dhf_item_changes),
    )


def judge_branch(
    cr_id: str,
    cr_item: dict | None,
    dhf_item_changes: dict[str, list[str]],
    code_changes: dict[str, list[str]],
    *,
    since_ref: str = git.DEFAULT_SINCE_REF,
    code_paths: tuple[str, ...] = (),
    unreviewed: dict[str, list[str]] | None = None,
) -> dict:
    """Whether a branch carries the coupled change set a CR expects.

    *cr_item* is the CR as stored, or None when the DHF has no such CR. The two
    change sets are ``{created, updated, deleted}`` — item IDs and file paths.

    The branch's DHF item changes and the CR's ``affected_items`` must match,
    both ways, apart from the CR itself. ``unreviewed`` maps an item that depends on
    a changed one to what it depends on; each is a finding unless the CR reviewed it.
    When ``code_paths`` is non-empty, at least one file under those paths must also have
    changed.
    """
    errors: list[dict] = []
    code_change_count = sum(len(code_changes[b]) for b in ("created", "updated", "deleted"))
    dhf_change_count = sum(len(dhf_item_changes[b]) for b in ("created", "updated", "deleted"))

    if code_paths and code_change_count == 0:
        errors.append({
            "field": "code_branch",
            "issue": (
                f"No product code changes found under {', '.join(code_paths)} "
                f"since {since_ref}. "
                f"(checked paths: {', '.join(code_paths)})"
            ),
            "fix": "Add the implementation changes on the same branch before opening a PR.",
        })

    changed_ids = set(
        dhf_item_changes["created"]
        + dhf_item_changes["updated"]
        + dhf_item_changes["deleted"]
    )

    unchanged_promised: list[str] = []
    # What the CR said it would touch is the thing to check. "Any DHF change at
    # all" passes a branch that edited something unrelated, and fails a PR that
    # has no CR — so the rule had to be carried in each adopter's workflow
    # conditions instead of here.
    promised = list((cr_item or {}).get("affected_items") or [])
    if promised:
        unchanged_promised = sorted(set(promised) - changed_ids)
        if unchanged_promised:
            errors.append({
                "field": "dhf_branch",
                "issue": (
                    f"{cr_id} lists {', '.join(unchanged_promised)} in affected_items, "
                    f"but the branch does not change them since {since_ref}."
                ),
                "fix": (
                    "Make the change the CR proposed, or update affected_items to "
                    "match what this CR actually touches."
                ),
            })
    elif cr_item is not None and dhf_change_count == 0:
        errors.append({
            "field": "dhf_branch",
            "issue": (
                f"No DHF item YAML changes found on the branch since {since_ref}, "
                f"and {cr_id} lists no affected_items to check against."
            ),
            "fix": "Run `build plan` so the CR records what it affects.",
        })

    # The other direction: an item the branch changes that the CR does not
    # list is a change nothing records, and `verify completion` never checks it.
    unlisted = sorted(changed_ids - set(promised) - {cr_id}) if cr_item is not None else []
    if unlisted:
        errors.append({
            "field": "dhf_branch",
            "issue": (
                f"The branch changes {', '.join(unlisted)} since {since_ref}, "
                f"but {cr_id} does not list them in affected_items."
            ),
            "fix": (
                f"Add them: medharness item update {cr_id} --data "
                f"'{{\"affected_items\": [...]}}' — or revert the changes this CR "
                f"should not make."
            ),
        })

    for dependent, origins in sorted((unreviewed or {}).items()):
        errors.append({
            "field": "impact",
            "issue": (
                f"{dependent} depends on {', '.join(origins)}, which this branch changes, "
                f"but {dependent} is neither changed nor listed in {cr_id}'s reviewed_items."
            ),
            "fix": (
                f"Update {dependent} to follow the change, or record that it was reviewed and "
                f"needs none: medharness item update {cr_id} --data '{{\"reviewed_items\": [\"{dependent}\"]}}'."
            ),
        })

    return envelope_from("verify changes", {
        "cr_id": cr_id,
        "since_ref": since_ref,
        "passed": not errors,
        "summary": f"{cr_id}: {len(errors)} branch finding(s) since {since_ref}.",
        # Envelope messages are strings a caller can print; the structured form
        # of the same findings stays in details.
        "errors": [f"{e['field']}: {e['issue']}" for e in errors],
        "findings": errors,
        "promised_but_unchanged": unchanged_promised,
        "unlisted_changes": unlisted,
        "cr_found": cr_item is not None,
        "dhf_item_changes": dhf_item_changes,
        "code_changes": code_changes,
    })
