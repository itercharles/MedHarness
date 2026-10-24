"""`build approvals`: who signed what in a release, laid out for a person to read.

The records under `DHF/approvals/` stay the only evidence; the sheet presents the ones
`verify approval --release` accepts and adds nothing of its own.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from medharness.services.approval import RELEASE_ID, Approval, Standing, content_hash, read_standing
from medharness.services.release_manifest import load_manifest, manifest_path, roles_for
from medharness.services.verify_approval import approval_gate, covering

SHEET = "approval-sheet"
TEMPLATE = "approval_sheet.md.j2"


def _text(value: str) -> str:
    """One line with no pipe, so it sits in a Markdown table cell or paragraph."""
    return " ".join(value.split()).replace("|", "\\|")


def _signature(approval: Approval) -> dict:
    return {
        "id": approval.id, "signer": _text(approval.approver.name), "roles": ", ".join(approval.roles),
        "signed_at": _text(approval.signed_at), "statement": _text(approval.statement), "key": approval.key,
        "unproven_presence": approval.approver.no_touch_required,
    }


def _documents(standing: Standing, dhf_path: Path, version: str, manifest: dict) -> list[dict]:
    config = standing.store.config
    pinned = [(code, entry["hash"], entry["file"], entry["file_hash"]) for code, entry in manifest["documents"].items()]
    # The release is the manifest file itself, so its hash is the file's.
    pinned.append((RELEASE_ID, content_hash(manifest_path(dhf_path, version)), f"releases/{version}/manifest.yaml", None))
    documents = []
    for code, hash_, file, file_hash in pinned:
        roles = roles_for(config, code)
        doc_type = config.get_doc_type(code)
        documents.append({
            "code": code, "name": "Release" if code == RELEASE_ID else (doc_type.name if doc_type else code),
            "file": file, "file_hash": file_hash, "hash": hash_, "roles": roles,
            "signatures": [_signature(a) for a in covering(standing.approvals, version, code, hash_, roles)],
        })
    return documents


def _approvers(standing: Standing) -> list[dict]:
    return [{
        "name": _text(a.name), "roles": ", ".join(a.roles), "no_touch_required": a.no_touch_required,
        "fingerprints": [fp for fp, (owner, _) in standing.roster.by_fingerprint.items() if owner.name == a.name],
    } for a in standing.roster.approvers]


def build_sheet(dhf_path: Path, version: str, out_dir: Path, *, doc_format: str = "html",
                since_ref: str | None = None) -> dict:
    """Write the sheet of release *version* when `verify approval --release` passes; otherwise write nothing."""
    gate = approval_gate(dhf_path, since_ref=since_ref, release=version)
    report = {"outcome": "completed_with_errors", "version": version, "path": None, "documents": 0,
              "signatures": 0, "errors": gate["errors"], "warnings": gate["warnings"]}
    if not gate["passed"]:
        return report

    standing = read_standing(dhf_path)
    manifest, _ = load_manifest(dhf_path, version)
    documents = _documents(standing, dhf_path, version, manifest)
    context = {
        "version": version, "project_name": standing.store.config.project_name,
        "generated": datetime.now().isoformat()[:10], "manifest_hash": content_hash(manifest_path(dhf_path, version)),
        "dhf_hash": manifest["dhf_hash"], "approvers_hash": manifest.get("approvers_hash"),
        "documents": documents, "approvers": _approvers(standing),
    }
    path = out_dir / f"{SHEET}.{doc_format}"
    try:
        standing.store.render_document(TEMPLATE, context, doc_format, path)
    except RuntimeError as exc:
        return {**report, "errors": [str(exc)]}
    signatures = {s["id"] for d in documents for s in d["signatures"]}
    return {**report, "outcome": "completed", "path": str(path), "documents": len(documents), "signatures": len(signatures)}
