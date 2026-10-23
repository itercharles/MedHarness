"""`verify approval`: whether every item in scope carries a current, signed approval from its role.

Off until the project keeps `DHF/config/approvers.yaml`. The list guards itself: a change to
it must be approved by someone on the list as it was where the branch left the base.
"""

from __future__ import annotations

import os
from pathlib import Path

from dhfkit.approvers import approvers_path, parse_approvers
from dhfkit.exceptions import DHFDataError
from medharness.services import git
from medharness.services.approval import (
    APPROVALS_DIR, APPROVERS_ID, ApprovalError, Roster, content_hash, evaluate, gaps, read_standing,
)
from medharness.services.envelope import gate_result

GATE = "verify approval"


def _who_may_approve(roles: tuple[str, ...], roster: Roster) -> str:
    names = [a.name for a in roster.holding(list(roles))]
    return ", ".join(names) if names else "no one on approvers.yaml holds it yet"


def changed_scope(repo_root: Path, dhf_path: Path, since_ref: str) -> list[str]:
    changes = git.collect_dhf_item_changes(repo_root, since_ref, dhf_path)
    return changes["created"] + changes["updated"]


def approval_gate(dhf_path: Path, *, since_ref: str | None = None, all_items: bool = False) -> dict:
    repo_root = dhf_path.resolve().parent
    since_ref = git.resolve_since_ref(repo_root, since_ref)
    try:
        return _judge(repo_root, dhf_path, since_ref, all_items)
    except (ApprovalError, DHFDataError) as exc:
        return gate_result(GATE, False, "Approvals could not be checked.", errors=[str(exc)])
    except git.DiffUnavailable as exc:
        return gate_result(GATE, False, f"Could not diff against {since_ref}.", errors=[
            f"Could not diff against {since_ref}: {exc}. Fetch it (`git fetch origin main`), or pass "
            f"--since-ref with a ref that exists here."])


def _judge(repo_root: Path, dhf_path: Path, since_ref: str, all_items: bool) -> dict:
    standing = read_standing(dhf_path)
    list_path = approvers_path(dhf_path)
    rel_list = os.path.relpath(list_path.resolve(), repo_root.resolve())
    if standing is None:
        if _existed_at(repo_root, since_ref, rel_list):
            return gate_result(GATE, False, "The approvers list is gone.", errors=[
                f"{rel_list} existed at {since_ref} and is deleted: removing it would switch approvals off. "
                f"Restore it."])
        return gate_result(GATE, True, "Approvals are not configured (no approvers.yaml): nothing checked.")
    if not standing.store.tracks_files:
        raise ApprovalError(git.FILES_IN_GIT.format(command=GATE, store=standing.store.store_type))

    config = standing.store.config
    errors = list(standing.problems)
    warnings = [f"{a.id} was signed with a key marked no_touch_required: made without proven presence."
                for a in standing.approvals if a.approver.no_touch_required]

    scope = list(standing.items) if all_items else changed_scope(repo_root, dhf_path, since_ref)
    missing = gaps(standing.items, scope, standing.approvals, config.approval_roles)
    checked = {u for u in scope if u in standing.items and config.approval_roles.get(standing.items[u]["type"])}
    for gap in missing:
        errors.append(
            f"{gap.id} ({gap.type}) has no current approval. It needs one from {' or '.join(gap.roles)}: "
            f"{_who_may_approve(gap.roles, standing.roster)}. They run `medharness item approve --key <KEY>`.")

    errors += _append_only(repo_root, dhf_path, since_ref)

    list_errors, list_warnings = _approvers_list(repo_root, dhf_path, since_ref, rel_list)
    errors += list_errors
    warnings += list_warnings

    return gate_result(
        GATE, not errors,
        f"{len(checked)} item(s) checked; {len(missing)} missing approval(s)",
        errors=errors, warnings=warnings,
    )


def _existed_at(repo_root: Path, since_ref: str, rel_path: str) -> bool:
    try:
        return git.file_at_branch_point(repo_root, since_ref, rel_path) is not None
    except git.DiffUnavailable:
        return False


def _append_only(repo_root: Path, dhf_path: Path, since_ref: str) -> list[str]:
    log_dir = os.path.relpath(dhf_path.resolve(), repo_root.resolve()) + f"/{APPROVALS_DIR}/"
    changes = git.collect_path_changes(repo_root, since_ref, log_dir)
    found = []
    for bucket, verb in (("updated", "modified"), ("deleted", "deleted")):
        for path in changes[bucket]:
            if path.endswith((".yaml", ".yaml.sig")):
                found.append(f"{path} was {verb} since {since_ref}: approvals are append-only. "
                             f"Restore it from {since_ref} and record a new approval instead.")
    return found


def _approvers_list(repo_root: Path, dhf_path: Path, since_ref: str, rel_path: str) -> tuple[list[str], list[str]]:
    """Findings and warnings about a change to the approvers list since the ref."""
    path = approvers_path(dhf_path)
    before = git.file_at_branch_point(repo_root, since_ref, rel_path)
    now = path.read_text(encoding="utf-8")
    if before == now:
        return [], []
    if before is None:
        return [], [f"{rel_path} is new since {since_ref}: it is the root of trust, accepted without an earlier signer."]
    old_roster = Roster(parse_approvers(before, f"{rel_path} at {since_ref}"))
    approvals, _ = evaluate(dhf_path, old_roster)
    wanted = content_hash(path)
    if any(a.hashes.get(APPROVERS_ID) == wanted for a in approvals):
        return [], []
    names = ", ".join(a.name for a in old_roster.approvers)
    return [f"{rel_path} changed since {since_ref} without an approval from someone on the list as it was then "
            f"({names}). One of them runs `medharness item approve --approvers --key <KEY>`."], []
