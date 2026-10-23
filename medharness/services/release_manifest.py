"""The release manifest and change report: what a release's signatures cover, and what changed since the last one.

`build release --write` writes `DHF/releases/<version>/manifest.yaml` and `changes.md`. A document
is signed over the item hashes it lists, not over the rendered file, because rendering is not
byte-stable. Neither file is an item: the store never loads them.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import yaml

from dhfkit.approvers import approvers_path
from medharness.services.approval import RELEASE_ID, ApprovalError, content_hash

RELEASES_DIR = "releases"
MANIFEST = "manifest.yaml"
CHANGES = "changes.md"
_VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]*")


def release_dir(dhf_path: Path, version: str) -> Path:
    if not _VERSION.fullmatch(version):
        raise ApprovalError(f"{version!r} is not a release version")
    return Path(dhf_path) / RELEASES_DIR / version


def manifest_path(dhf_path: Path, version: str) -> Path:
    return release_dir(dhf_path, version) / MANIFEST


def roles_for(config, doc_id: str) -> list[str]:
    """The roles whose signature a manifest document needs; none for a type nobody owns."""
    return [config.release_role] if doc_id == RELEASE_ID else config.approval_roles.get(doc_id, [])


def digest(pairs: Iterable[tuple[str, str]]) -> str:
    lines = "\n".join(f"{uid}:{hash_}" for uid, hash_ in sorted(pairs))
    return "sha256:" + hashlib.sha256(lines.encode("utf-8")).hexdigest()


def documented(items: list[dict], config) -> list[dict]:
    """The items a release's documents and `dhf_hash` cover: all but the release records themselves."""
    # A REL moves through its states after its release is signed; it is the record of the release, not its content.
    release_types = {dt.code for dt in config.doc_types if dt.role == "release"}
    return [item for item in items if item["type"] not in release_types]


def item_hashes(items: list[dict]) -> dict[str, str]:
    return {item["id"]: content_hash(Path(item["file_path"])) for item in items}


def build_manifest(dhf_path: Path, version: str, items: list[dict], specs: list[dict], out_dir: Path) -> dict:
    hashes = item_hashes(items)
    documents = {}
    for spec in sorted(specs, key=lambda s: s["doc_type"]):
        code = spec["doc_type"]
        pairs = sorted((i["id"], hashes[i["id"]]) for i in items if i["type"] == code)
        rendered = Path(spec["path"])
        documents[code] = {
            "file": rendered.relative_to(out_dir).as_posix(),
            "file_hash": content_hash(rendered),
            "items": [{"id": uid, "hash": hash_} for uid, hash_ in pairs],
            "hash": digest(pairs),
        }
    approvers = approvers_path(dhf_path)
    return {
        "version": version,
        "dhf_hash": digest(hashes.items()),
        "approvers_hash": content_hash(approvers) if approvers.is_file() else None,
        "documents": documents,
    }


def load_manifest(dhf_path: Path, version: str) -> tuple[dict | None, str | None]:
    """The manifest of *version*, or what is wrong with it."""
    path = manifest_path(dhf_path, version)
    if not path.is_file():
        return None, (f"Release {version} has no manifest ({path.name} under {RELEASES_DIR}/{version}/). "
                      f"Run `medharness build release --version {version} --write`.")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        documents = data["documents"]
        ok = isinstance(data["dhf_hash"], str) and all(
            isinstance(entry["hash"], str) and all(isinstance(i["id"], str) and isinstance(i["hash"], str) for i in entry["items"])
            for entry in documents.values())
    except (yaml.YAMLError, UnicodeDecodeError, KeyError, TypeError, AttributeError):
        ok = False
    if not ok:
        return None, f"{RELEASES_DIR}/{version}/{MANIFEST} is not a release manifest."
    return data, None


def drift(manifest: dict, dhf_path: Path, items: list[dict]) -> list[str]:
    """What changed in the DHF since the manifest was written."""
    version = manifest.get("version")
    hashes = item_hashes(items)
    types = {item["id"]: item["type"] for item in items}
    rerun = f"Rerun `medharness build release --version {version} --write` so the documents are signed over the current content."
    found = []
    for code, entry in manifest["documents"].items():
        listed = {i["id"]: i["hash"] for i in entry["items"]}
        now = {uid: h for uid, h in hashes.items() if types[uid] == code}
        for uid in sorted(set(listed) | set(now)):
            if listed.get(uid) != now.get(uid):
                what = "was added" if uid not in listed else "was removed" if uid not in now else "was edited"
                found.append(f"{uid} ({code}) {what} after the manifest of release {version} was written. {rerun}")
    if not found and manifest["dhf_hash"] != digest(hashes.items()):
        found.append(f"The DHF changed after the manifest of release {version} was written, in an item no document lists. {rerun}")
    approvers = approvers_path(dhf_path)
    now_approvers = content_hash(approvers) if approvers.is_file() else None
    if manifest.get("approvers_hash") != now_approvers:
        found.append(f"The approvers list changed after the manifest of release {version} was written. {rerun}")
    return found


def _order(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version))


def previous_manifest(dhf_path: Path, version: str) -> dict | None:
    """The manifest of the latest release numbered below *version*; versions order by their numbers, 1.10.0 after 1.9.0."""
    here = _order(version)
    earlier = sorted(
        ((_order(p.parent.name), p.parent.name) for p in (Path(dhf_path) / RELEASES_DIR).glob(f"*/{MANIFEST}")
         if _order(p.parent.name) and _order(p.parent.name) < here))
    if not earlier:
        return None
    manifest, problem = load_manifest(dhf_path, earlier[-1][1])
    if problem:
        raise ApprovalError(problem)
    return manifest


def changes_markdown(manifest: dict, previous: dict | None, crs: dict[str, list[str]]) -> str:
    """Per document the items added, modified and removed since *previous*, each with the CRs that list it."""
    since = f"release {previous['version']}" if previous else "nothing: this is the first release, so every item is added"
    lines = [f"# Changes in release {manifest['version']}", "", f"Compared with {since}.", ""]
    for code, entry in manifest["documents"].items():
        old = {i["id"]: i["hash"] for i in previous["documents"].get(code, {}).get("items", [])} if previous else {}
        now = {i["id"]: i["hash"] for i in entry["items"]}
        groups = {
            "Added": sorted(set(now) - set(old)),
            "Modified": sorted(u for u in set(now) & set(old) if now[u] != old[u]),
            "Removed": sorted(set(old) - set(now)),
        }
        lines += [f"## {code}", ""]
        if not any(groups.values()):
            lines += ["No changes.", ""]
        for name, ids in groups.items():
            if ids:
                lines += [f"{name} ({len(ids)})", ""]
                lines += [f"- {uid}" + (f" ({', '.join(crs[uid])})" if crs.get(uid) else "") for uid in ids]
                lines.append("")
    return "\n".join(lines)


def write_release_files(dhf_path: Path, version: str, items: list[dict], specs: list[dict],
                        out_dir: Path, cr_ids: list[str], config) -> None:
    manifest = build_manifest(dhf_path, version, documented(items, config), specs, out_dir)
    crs: dict[str, list[str]] = defaultdict(list)
    for item in sorted(items, key=lambda i: i["id"]):
        if item["type"] == "CR" and item["id"] in cr_ids:
            for uid in item.get("affected_items") or []:
                crs[uid].append(item["id"])
    changes = changes_markdown(manifest, previous_manifest(dhf_path, version), crs)
    folder = release_dir(dhf_path, version)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / MANIFEST).write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    (folder / CHANGES).write_text(changes, encoding="utf-8")


def changes_for(dhf_path: Path, version: str, code: str) -> str:
    """The section of `changes.md` for one document, or an empty string."""
    path = release_dir(dhf_path, version) / CHANGES
    if not path.is_file():
        return ""
    section: list[str] = []
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line == f"## {code}"
        elif inside:
            section.append(line)
    return "\n".join(section).strip()
