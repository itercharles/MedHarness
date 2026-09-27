"""Git helpers for CI workflows — commit, push, and inspect DHF / repo changes."""

from __future__ import annotations

import subprocess
from medharness.services.ci import envelope_from
from pathlib import Path


def compute_diff(
    repo_root: Path,
    since_ref: str,
    *paths: str,
) -> str | None:
    """Return git diff output.

    Returns:
        ``""`` for a legitimate empty diff (git ran, no changes since ``since_ref``).
        ``None`` for an environment failure (git missing, ref unfetched, etc.) —
        callers should treat this as un-checkable rather than as "no changes".
        Otherwise the diff text.
    """
    try:
        result = subprocess.run(
            ["git", "diff", since_ref, "--", *paths],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout or ""


class DiffUnavailable(Exception):
    """git could not produce the diff — not the same answer as an empty one."""


def collect_path_changes(
    repo_root: Path,
    since_ref: str,
    *paths: str,
) -> dict[str, list[str]]:
    """Return ``{created, updated, deleted}`` lists of file paths changed since ``since_ref``.

    Paths are returned exactly as git reports them (relative to ``repo_root``).
    Raises DiffUnavailable when git is missing or the diff fails — an unfetched
    ref in a shallow clone, or no remote at all — with git's own reason.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", since_ref, "--", *paths],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            check=False,
        )
    except FileNotFoundError as exc:
        raise DiffUnavailable("git is not installed") from exc
    if result.returncode != 0:
        reason = (result.stderr or "").strip().splitlines()
        raise DiffUnavailable(reason[0] if reason else f"git diff {since_ref} exited {result.returncode}")

    created: list[str] = []
    updated: list[str] = []
    deleted: list[str] = []
    for line in (result.stdout or "").splitlines():
        if not line:
            continue
        # Lines: "A\tpath", "M\tpath", "D\tpath", "R100\told\tnew" (rename).
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status_code = parts[0]
        if status_code.startswith("A"):
            created.append(parts[1])
        elif status_code.startswith("M"):
            updated.append(parts[1])
        elif status_code.startswith("D"):
            deleted.append(parts[1])
        elif status_code.startswith("R") and len(parts) >= 3:
            # Rename — count as an update on the new path.
            updated.append(parts[2])
    return {"created": created, "updated": updated, "deleted": deleted}


def collect_dhf_item_changes(repo_root: Path, since_ref: str) -> dict[str, list[str]]:
    """Return ``{created, updated, deleted}`` lists of DHF item IDs changed since ``since_ref``.

    Item IDs are extracted as the file stem (e.g. ``DHF/items/01_sys/SYS-001.yaml``
    becomes ``"SYS-001"``). Non-YAML files under ``DHF/items/`` are skipped.
    """
    raw = collect_path_changes(repo_root, since_ref, "DHF/items/")
    out: dict[str, list[str]] = {"created": [], "updated": [], "deleted": []}
    for bucket in out:
        for path in raw[bucket]:
            p = Path(path)
            if p.suffix.lower() != ".yaml":
                continue
            out[bucket].append(p.stem)
    return out


def validate_atomic_branch(
    repo_root: Path,
    dhf_path: Path,
    cr_id: str,
    *,
    since_ref: str = "origin/main",
    code_paths: tuple[str, ...] = (),
) -> dict:
    """Read the branch's diff and the CR, then ``judge_branch`` them."""
    try:
        dhf_item_changes = collect_dhf_item_changes(repo_root, since_ref)
        code_changes = collect_path_changes(repo_root, since_ref, *code_paths) if code_paths else {
            "created": [], "updated": [], "deleted": [],
        }
    except DiffUnavailable as exc:
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
        return envelope_from("workflow check-changes", {
            "cr_id": cr_id,
            "since_ref": since_ref,
            "passed": False,
            "summary": f"{cr_id}: could not read the diff against {since_ref}.",
            "errors": [f"{finding['field']}: {finding['issue']}"],
            "findings": [finding],
        })

    from dhfkit.local_adapter import LocalDHFAdapter

    # A DHF that will not load must stop the gate: skipping the promise check
    # passed a branch that broke one. A CR that does not exist is not applicable.
    cr_item = LocalDHFAdapter(dhf_path).get_item(cr_id)
    return judge_branch(
        cr_id,
        cr_item,
        dhf_item_changes,
        code_changes,
        since_ref=since_ref,
        code_paths=code_paths,
    )


def judge_branch(
    cr_id: str,
    cr_item: dict | None,
    dhf_item_changes: dict[str, list[str]],
    code_changes: dict[str, list[str]],
    *,
    since_ref: str = "origin/main",
    code_paths: tuple[str, ...] = (),
) -> dict:
    """Whether a branch carries the coupled change set a CR expects.

    *cr_item* is the CR as stored, or None when the DHF has no such CR. The two
    change sets are ``{created, updated, deleted}`` — item IDs and file paths.

    DHF item changes are always required — `build plan` must run on every CR
    branch. When ``code_paths`` is non-empty, at least one file under those
    paths must also have changed.
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

    return envelope_from("workflow check-changes", {
        "cr_id": cr_id,
        "since_ref": since_ref,
        "passed": not errors,
        "summary": f"{cr_id}: {len(errors)} branch finding(s) since {since_ref}.",
        # Envelope messages are strings a caller can print; the structured form
        # of the same findings stays in details.
        "errors": [f"{e['field']}: {e['issue']}" for e in errors],
        "findings": errors,
        "promised_but_unchanged": unchanged_promised,
        "cr_found": cr_item is not None,
        "dhf_item_changes": dhf_item_changes,
        "code_changes": code_changes,
    })
