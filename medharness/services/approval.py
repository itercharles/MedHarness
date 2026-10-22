"""Signed approvals: content hashes, keys, and which items the approvals on file cover.

Shared by `verify approval`, which judges them, and `item approve`, which writes one.
An approval is an APPROVAL item whose file is signed with `ssh-keygen -Y sign`; the
signature sits beside it as `<file>.sig` and covers the file's bytes.
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dhfkit.approvers import Approver, load_approvers
from dhfkit.store import DHFStore, open_store

NAMESPACE = "medharness-approval"
#: The `id` an approval's `items` entry uses for the approvers list.
APPROVERS_ID = "approvers"
APPROVAL_TYPE = "APPROVAL"


class ApprovalError(Exception):
    """Approvals cannot be read or made: ssh-keygen is missing, or a key is unusable."""


def content_hash(path: Path) -> str:
    """What an approval binds to: the bytes of the file, so any edit leaves it behind."""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def ssh_keygen(*args: str, data: bytes | None = None) -> tuple[int, str, str]:
    try:
        done = subprocess.run(["ssh-keygen", *args], input=data, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ApprovalError("ssh-keygen (OpenSSH 8.0 or later) is needed for approvals and is not installed") from exc
    return done.returncode, done.stdout.decode(errors="replace"), done.stderr.decode(errors="replace")


def fingerprint(public_key: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        key_file = Path(tmp) / "key.pub"
        key_file.write_text(public_key.strip() + "\n", encoding="utf-8")
        code, out, _ = ssh_keygen("-l", "-f", str(key_file))
    if code != 0 or len(out.split()) < 2:
        raise ApprovalError(f"not an OpenSSH public key: {public_key.strip()[:60]!r}")
    return out.split()[1]


class Roster:
    """The approvers, looked up by the fingerprint of the key that signed."""

    def __init__(self, approvers: list[Approver]):
        self.approvers = approvers
        self.by_fingerprint = {fingerprint(k): (a, k) for a in approvers for k in a.keys}

    def holding(self, roles: list[str]) -> list[Approver]:
        return [a for a in self.approvers if set(a.roles) & set(roles)]


@dataclass(frozen=True)
class Approval:
    id: str
    roles: tuple[str, ...]
    hashes: dict[str, str]
    approver: Approver


def check_signature(record: dict, path: Path, roster: Roster) -> tuple[Approver | None, str | None]:
    """Who signed the file at *path*, and what is wrong with it, if anything."""
    uid = record["id"]
    roles = record.get("roles")
    if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
        return None, f"{uid} has no list of roles it was signed for"
    entry = roster.by_fingerprint.get(record.get("key"))
    if entry is None:
        return None, f"{uid} was signed with key {record.get('key')}, which is not on the approvers list"
    approver, key_line = entry
    foreign = [r for r in roles if r not in approver.roles]
    if foreign:
        return approver, f"{uid} claims role(s) {', '.join(foreign)}, which {approver.name} does not hold"
    if record.get("signer") != approver.name:
        return approver, f"{uid} names {record.get('signer')!r} as signer, but its key belongs to {approver.name}"
    sig = path.with_name(path.name + ".sig")
    if not sig.is_file():
        return approver, f"{uid} has no signature file ({sig.name}); it counts for nothing until it is signed"
    with tempfile.TemporaryDirectory() as tmp:
        allowed = Path(tmp) / "allowed_signers"
        # OpenSSH rejects a `no-touch-required` option in allowed_signers, so presence is reported, not configured.
        allowed.write_text(f"{approver.principal} {key_line}\n", encoding="utf-8")
        code, _, err = ssh_keygen("-Y", "verify", "-f", str(allowed), "-I", approver.principal,
                                  "-n", NAMESPACE, "-s", str(sig), data=path.read_bytes())
    if code != 0:
        return approver, (f"{uid}'s signature does not verify: the file changed after it was signed, "
                          f"or the key differs ({err.strip() or 'ssh-keygen refused it'})")
    return approver, None


def _hashes(record: dict) -> dict[str, str] | None:
    entries = record.get("items")
    if not isinstance(entries, list):
        return None
    hashes: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not isinstance(entry.get("hash"), str):
            return None
        hashes[entry["id"]] = entry["hash"]
    return hashes


def evaluate(items: dict[str, dict], roster: Roster) -> tuple[list[Approval], list[str]]:
    """The approvals that stand, and a finding for each APPROVAL item that does not."""
    valid: list[Approval] = []
    problems: list[str] = []
    for uid, record in sorted(items.items()):
        if record["type"] != APPROVAL_TYPE:
            continue
        approver, problem = check_signature(record, Path(record["file_path"]), roster)
        hashes = _hashes(record)
        if problem is None and hashes is None:
            problem = f"{uid} does not list its items as {{id, hash}} entries"
        if problem is not None or approver is None or hashes is None:
            problems.append(f"{problem}. It counts for nothing; an approver records a new approval with `medharness item approve`.")
            continue
        valid.append(Approval(uid, tuple(record["roles"]), hashes, approver))
    return valid, problems


@dataclass(frozen=True)
class Gap:
    """An item whose current content no approval from its role covers."""
    id: str
    type: str
    roles: tuple[str, ...]
    hash: str


def gaps(items: dict[str, dict], scope: list[str], approvals: list[Approval], approval_roles: dict[str, list[str]]) -> list[Gap]:
    found = []
    for uid in sorted(set(scope)):
        record = items.get(uid)
        if record is None or record["type"] == APPROVAL_TYPE or not approval_roles.get(record["type"]):
            continue
        needed = approval_roles[record["type"]]
        now = content_hash(Path(record["file_path"]))
        if not any(a.hashes.get(uid) == now and set(a.roles) & set(needed) for a in approvals):
            found.append(Gap(uid, record["type"], tuple(needed), now))
    return found


@dataclass
class Standing:
    """The approvals on file for a DHF whose project keeps an approvers list."""
    store: DHFStore
    approvers: list[Approver]
    roster: Roster
    items: dict[str, dict]
    approvals: list[Approval]
    problems: list[str]


def read_standing(dhf_path: Path) -> Standing | None:
    """None when the project keeps no approvers list: approvals are off."""
    approvers = load_approvers(dhf_path)
    if approvers is None:
        return None
    store = open_store(dhf_path)
    roster = Roster(approvers)
    items = {item["id"]: item for item in store.list_items()}
    approvals, problems = evaluate(items, roster)
    return Standing(store, approvers, roster, items, approvals, problems)
