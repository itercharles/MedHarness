"""Git: what a branch changed, committing and pushing a run's work, and where a branch left its base."""

from __future__ import annotations

import subprocess
from pathlib import Path

DEFAULT_SINCE_REF = "origin/main"


class DiffUnavailable(Exception):
    """git could not produce the diff — not the same answer as an empty one."""


def _branch_point(repo_root: Path, since_ref: str) -> str:
    """Where the branch left ``since_ref``, so work that landed on it since is not the branch's.

    Raises DiffUnavailable when git is missing or there is no common ancestor — an
    unfetched ref, or a shallow clone too short to reach the fork.
    """
    try:
        result = subprocess.run(
            ["git", "merge-base", since_ref, "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root), check=False,
        )
    except FileNotFoundError as exc:
        raise DiffUnavailable("git is not installed") from exc
    if result.returncode != 0:
        reason = (result.stderr or "").strip().splitlines()
        raise DiffUnavailable(reason[0] if reason else f"no common ancestor of {since_ref} and HEAD")
    return result.stdout.strip()


def resolve_since_ref(repo_root: Path, explicit: str | None = None) -> str:
    """What the branch is compared against: what the caller named, else the branch
    ``origin``'s HEAD points at, else ``origin/main``."""
    if explicit:
        return explicit
    try:
        done = subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
                              capture_output=True, text=True, cwd=str(repo_root), check=False)
    except FileNotFoundError:
        return DEFAULT_SINCE_REF
    ref = done.stdout.strip()
    return ref if done.returncode == 0 and ref else DEFAULT_SINCE_REF


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
        base = _branch_point(repo_root, since_ref)
        result = subprocess.run(
            ["git", "diff", base, "--", *paths],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            check=False,
        )
    except (FileNotFoundError, DiffUnavailable):
        return None
    if result.returncode != 0:
        return None
    return result.stdout or ""


def head(repo_root: Path) -> str | None:
    """The commit HEAD names, or None outside a repository."""
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True, cwd=str(repo_root), check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def uncommit_since(repo_root: Path, start: str | None) -> list[str]:
    """Undo commits made after ``start``, keeping their changes staged.

    Returns the commits undone, oldest first.
    """
    if not start:
        return []
    listed = subprocess.run(["git", "rev-list", "--reverse", f"{start}..HEAD"],
                            capture_output=True, text=True, cwd=str(repo_root), check=False)
    commits = listed.stdout.split() if listed.returncode == 0 else []
    if commits:
        subprocess.run(["git", "reset", "--soft", start], cwd=str(repo_root),
                       capture_output=True, check=True)
    return commits


def commit_and_push(repo_root: Path, message: str, branch: str) -> str | None:
    """Stage everything, commit it if anything changed, push to ``branch``.

    Returns why it failed, or None.
    """
    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              cwd=str(repo_root), check=False)

    run("add", "-A")
    if run("diff", "--cached", "--quiet").returncode != 0:
        committed = run("commit", "-m", message)
        if committed.returncode != 0:
            return (committed.stderr or committed.stdout).strip()
    pushed = run("push", "origin", f"HEAD:{branch}")
    return None if pushed.returncode == 0 else (pushed.stderr or pushed.stdout).strip()


def collect_path_changes(
    repo_root: Path,
    since_ref: str,
    *paths: str,
) -> dict[str, list[str]]:
    """Return ``{created, updated, deleted}`` lists of file paths the branch changed since it left ``since_ref``.

    Paths are returned exactly as git reports them (relative to ``repo_root``).
    Raises DiffUnavailable when git is missing or the diff fails — an unfetched
    ref in a shallow clone, or no remote at all — with git's own reason.
    """
    base = _branch_point(repo_root, since_ref)
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", base, "--", *paths],
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
    # `git diff` compares tracked files only; a file an agent created and left
    # uncommitted is a change too.
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *paths],
        capture_output=True, text=True, cwd=str(repo_root), check=False,
    )
    created.extend(line for line in (untracked.stdout or "").splitlines() if line)
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


def added_line_counts(repo_root: Path, since_ref: str, *paths: str) -> dict[str, int]:
    """Lines each tracked file gained since the branch left ``since_ref``, working tree included."""
    base = _branch_point(repo_root, since_ref)
    result = subprocess.run(
        ["git", "diff", "--numstat", base, "--", *paths],
        capture_output=True, text=True, cwd=str(repo_root), check=False,
    )
    if result.returncode != 0:
        raise DiffUnavailable((result.stderr or "").strip().splitlines()[0] if result.stderr else "git diff failed")
    counts: dict[str, int] = {}
    for line in result.stdout.splitlines():
        added, _, path = line.split("\t", 2)
        if added.isdigit():
            counts[path] = int(added)
    return counts


def file_at_branch_point(repo_root: Path, since_ref: str, path: str) -> str | None:
    """A file as it was where the branch left ``since_ref``; None when it did not exist there."""
    base = _branch_point(repo_root, since_ref)
    result = subprocess.run(["git", "show", f"{base}:{path}"], capture_output=True, text=True,
                            cwd=str(repo_root), check=False)
    return result.stdout if result.returncode == 0 else None


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


#: Said by every command that answers from the repository's diff.
FILES_IN_GIT = (
    "`{command}` compares files in Git, and this DHF keeps its items in the "
    "'{store}' store. Use a DHF whose store is 'yaml' for it."
)
