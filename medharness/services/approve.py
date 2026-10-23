"""`item approve`: record and sign one approval for every pending item the signer's roles cover."""

from __future__ import annotations

import contextlib
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from dhfkit.approvers import Approver, approvers_path
from medharness.services import git
from medharness.services.approval import (
    APPROVERS_ID, NAMESPACE, UNSCOPED, ApprovalError, Gap, Standing, approvals_dir, check_signature,
    content_hash, fingerprint, gaps, new_ulid, read_standing, ssh_keygen,
)
from medharness.services.verify_approval import changed_scope


@dataclass
class Plan:
    standing: Standing
    approver: Approver
    fingerprint: str
    roles: list[str]
    cr_id: str | None
    gaps: list[Gap]
    entries: list[dict]


def _public_key(private_key: Path) -> str:
    # A public key here would make ssh-keygen sign through ssh-agent, which holds keys
    # that are already unlocked; the signer names the private key and touches it.
    if not private_key.read_text(encoding="utf-8", errors="replace").startswith("-----BEGIN"):
        raise ApprovalError(f"{private_key} is not a private key file; --key takes the private key, never ssh-agent")
    pub = private_key.with_name(private_key.name + ".pub")
    if pub.is_file():
        return pub.read_text(encoding="utf-8")
    code, out, err = ssh_keygen("-y", "-f", str(private_key))
    if code != 0:
        raise ApprovalError(f"cannot read the public key of {private_key}: {err.strip()}")
    return out


def prepare(
    dhf_path: Path, private_key: Path, *, roles: tuple[str, ...], cr_id: str | None,
    since_ref: str | None, all_items: bool, approvers_list: bool,
) -> Plan | None:
    """What the key's owner would sign, or None when approvals are not configured."""
    standing = read_standing(dhf_path)
    if standing is None:
        return None
    if not standing.store.tracks_files:
        raise ApprovalError(git.FILES_IN_GIT.format(command="item approve", store=standing.store.store_type))
    key_fp = fingerprint(_public_key(private_key))
    entry = standing.roster.by_fingerprint.get(key_fp)
    if entry is None:
        raise ApprovalError(f"{private_key} (key {key_fp}) is not on the approvers list, so it cannot approve")
    approver = entry[0]
    foreign = [r for r in roles if r not in approver.roles]
    if foreign:
        raise ApprovalError(f"{approver.name} does not hold role(s) {', '.join(foreign)}; holds {', '.join(approver.roles)}")
    chosen = list(roles) or list(approver.roles)

    repo_root = dhf_path.resolve().parent
    if all_items:
        scope = list(standing.items)
    else:
        scope = changed_scope(repo_root, dhf_path, git.resolve_since_ref(repo_root, since_ref))
        if cr_id is not None:
            cr = standing.items.get(cr_id)
            if cr is None or cr["type"] != "CR":
                raise ApprovalError(f"{cr_id} is not a CR in this DHF")
            scope = [u for u in scope if u in (cr.get("affected_items") or [])] + [cr_id]
    config = standing.store.config
    pending = [g for g in gaps(standing.items, scope, standing.approvals, config.approval_roles)
               if set(g.roles) & set(chosen)]

    entries = []
    for gap in pending:
        row = {"id": gap.id, "hash": gap.hash}
        if gap.type == "CR":
            row["meaning"] = standing.items[gap.id].get("status", "")
        entries.append(row)
    used = sorted({r for g in pending for r in g.roles if r in chosen})
    if approvers_list:
        entries.append({"id": APPROVERS_ID, "hash": content_hash(approvers_path(dhf_path))})
        used = used or sorted(chosen)
    return Plan(standing, approver, key_fp, used, cr_id, pending, entries)


def sign(dhf_path: Path, private_key: Path, plan: Plan, statement: str) -> dict:
    """Write the record into the log and sign its file; the file is not written again afterwards."""
    uid = new_ulid()
    record = {
        "id": uid,
        "cr": plan.cr_id,
        "signer": plan.approver.name,
        "roles": plan.roles,
        "signed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "statement": statement,
        "items": plan.entries,
        "key": plan.fingerprint,
    }
    folder = approvals_dir(dhf_path) / (plan.cr_id or UNSCOPED)
    path = folder / f"{uid}.yaml"
    signature = path.with_name(path.name + ".sig")
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True), encoding="utf-8")
        # stderr stays attached so a passphrase or "confirm user presence" prompt reaches the signer.
        done = subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(private_key), "-n", NAMESPACE, str(path)],
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)
        problem = f"ssh-keygen could not sign (exit {done.returncode})" if done.returncode else None
        if problem is None:
            _, problem = check_signature(record, path, plan.standing.roster)
        if problem is not None:
            raise ApprovalError(f"{uid} was not recorded: {problem}")
    except BaseException:
        path.unlink(missing_ok=True)
        signature.unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            folder.rmdir()
        raise
    return {**record, "path": str(path)}
