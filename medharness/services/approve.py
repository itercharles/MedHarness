"""`item approve`: record and sign one approval covering the release documents the signer's roles own."""

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
    APPROVERS_ID, NAMESPACE, RELEASE_ID, UNSCOPED, ApprovalError, Standing, approvals_dir, check_signature,
    content_hash, fingerprint, new_ulid, read_standing, release_folder, ssh_keygen,
)
from medharness.services.release_manifest import changes_for, load_manifest, manifest_path, roles_for


@dataclass
class Plan:
    standing: Standing
    approver: Approver
    fingerprint: str
    roles: list[str]
    release: str | None
    documents: list[dict]


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


def _identify(dhf_path: Path, private_key: Path) -> tuple[Standing, Approver, str] | None:
    """Who the key belongs to, or None when approvals are not configured."""
    standing = read_standing(dhf_path)
    if standing is None:
        return None
    if not standing.store.tracks_files:
        raise ApprovalError(git.FILES_IN_GIT.format(command="item approve", store=standing.store.store_type))
    key_fp = fingerprint(_public_key(private_key))
    entry = standing.roster.by_fingerprint.get(key_fp)
    if entry is None:
        raise ApprovalError(f"{private_key} (key {key_fp}) is not on the approvers list, so it cannot approve")
    return standing, entry[0], key_fp


def prepare_release(dhf_path: Path, private_key: Path, version: str) -> Plan | None:
    """The documents of release *version* this key's owner would sign, or None when approvals are not configured."""
    who = _identify(dhf_path, private_key)
    if who is None:
        return None
    standing, approver, key_fp = who
    manifest, problem = load_manifest(dhf_path, version)
    if manifest is None:
        raise ApprovalError(problem)
    config = standing.store.config
    held = set(approver.roles)
    owned = [{"id": code, "hash": entry["hash"]} for code, entry in manifest["documents"].items()
             if held & set(roles_for(config, code))]
    if held & set(roles_for(config, RELEASE_ID)):
        owned.append({"id": RELEASE_ID, "hash": content_hash(manifest_path(dhf_path, version))})
    pending = [d for d in owned
               if not any(a.release == version and a.approver.name == approver.name and a.hashes.get(d["id"]) == d["hash"]
                          for a in standing.approvals)]
    used = sorted({r for d in pending for r in roles_for(config, d["id"]) if r in held})
    return Plan(standing, approver, key_fp, used, version, pending)


def prepare_approvers(dhf_path: Path, private_key: Path) -> Plan | None:
    """The approvers list, as the key's owner would sign it, or None when approvals are not configured."""
    who = _identify(dhf_path, private_key)
    if who is None:
        return None
    standing, approver, key_fp = who
    return Plan(standing, approver, key_fp, sorted(approver.roles), None,
                [{"id": APPROVERS_ID, "hash": content_hash(approvers_path(dhf_path))}])


def describe(dhf_path: Path, plan: Plan, doc_id: str) -> str:
    """What the signer is asked to read before signing one document."""
    if doc_id == APPROVERS_ID:
        return "the approvers list as it is now"
    if doc_id == RELEASE_ID:
        return f"the release manifest of {plan.release}, and with it every document in it"
    return changes_for(dhf_path, plan.release, doc_id) or "no change report for this document"


def sign(dhf_path: Path, private_key: Path, plan: Plan, statement: str) -> dict:
    """Write the record into the log and sign its file; the file is not written again afterwards."""
    uid = new_ulid()
    record = {
        "id": uid,
        **({"release": plan.release} if plan.release else {}),
        "signer": plan.approver.name,
        "roles": plan.roles,
        "signed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "statement": statement,
        "documents": plan.documents,
        "key": plan.fingerprint,
    }
    folder = approvals_dir(dhf_path) / (release_folder(plan.release) if plan.release else UNSCOPED)
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
