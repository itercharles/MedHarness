"""Git helpers for CI workflows — commit, push, and inspect DHF / repo changes."""

from __future__ import annotations

import subprocess
from pathlib import Path

from medharness.services.spec_validation import parse_spec_frontmatter, read_spec_json


def collect_path_changes(
    repo_root: Path,
    since_ref: str,
    *paths: str,
) -> dict[str, list[str]]:
    """Return ``{created, updated, deleted}`` lists of file paths changed since ``since_ref``.

    Paths are returned exactly as git reports them (relative to ``repo_root``).
    On environment failure (git missing, ref unfetched, non-zero exit) all
    three lists are empty; callers that need to distinguish "no changes" from
    "could not check" should run the diff themselves.
    """
    empty: dict[str, list[str]] = {"created": [], "updated": [], "deleted": []}
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", since_ref, "--", *paths],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            check=False,
        )
    except FileNotFoundError:
        return empty
    if result.returncode != 0:
        return empty

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
    code_paths: tuple[str, ...] = ("apps/", "packages/"),
    spec_path: Path | None = None,
) -> dict:
    """Validate that a branch carries the coupled change set a CR expects.

    This is a deterministic branch-level contract for single-repo product
    setups: implementation branches should carry product code changes, DHF item
    changes when the approved spec expects them, and a readable approved spec
    file for the CR. The spec file may already be present on ``since_ref``.
    """
    resolved_spec = spec_path or (repo_root / "docs" / "cr-specs" / f"{cr_id}-Spec.md")
    spec_changed = collect_path_changes(repo_root, since_ref, str(resolved_spec.relative_to(repo_root)))
    dhf_item_changes = collect_dhf_item_changes(repo_root, since_ref)
    code_changes = collect_path_changes(repo_root, since_ref, *code_paths)

    fm = read_spec_json(resolved_spec) or parse_spec_frontmatter(resolved_spec) or {}
    affected = fm.get("affected_items") if isinstance(fm.get("affected_items"), list) else []
    proposed = fm.get("proposed_new_items") if isinstance(fm.get("proposed_new_items"), list) else []

    errors: list[dict] = []
    code_change_count = sum(len(code_changes[b]) for b in ("created", "updated", "deleted"))
    dhf_change_count = sum(len(dhf_item_changes[b]) for b in ("created", "updated", "deleted"))

    if not resolved_spec.exists():
        errors.append({
            "field": "spec_path",
            "issue": f"Missing approved spec at {resolved_spec.relative_to(repo_root)}.",
            "fix": "Merge or generate the approved spec for this CR before validating the implementation branch.",
        })

    if code_change_count == 0:
        errors.append({
            "field": "code_branch",
            "issue": f"No product code changes found under {', '.join(code_paths)} since {since_ref}.",
            "fix": "Add the implementation changes on the same branch before opening a PR.",
        })

    if affected or proposed:
        if dhf_change_count == 0:
            errors.append({
                "field": "dhf_branch",
                "issue": "The spec expects DHF item impact, but no DHF item YAML changes were found on the branch.",
                "fix": "Include the required DHF item create/update changes on the same branch as the implementation.",
            })

    return {
        "cr_id": cr_id,
        "since_ref": since_ref,
        "passed": not errors,
        "spec_path": str(resolved_spec),
        "expected_dhf_changes": bool(affected or proposed),
        "spec_changes": spec_changed,
        "dhf_item_changes": dhf_item_changes,
        "code_changes": code_changes,
        "errors": errors,
    }


def commit_dhf_item(
    dhf_path: Path,
    item_id: str,
    message: str,
    *,
    push: bool = False,
) -> dict[str, bool]:
    """Stage, commit, and optionally push a DHF item file.

    Finds the item YAML file via glob, then runs git add/commit/push
    in the DHF root directory. Returns a dict with ``staged``, ``committed``,
    ``pushed`` booleans.
    """
    matches = list(dhf_path.rglob(f"{item_id}.yaml"))
    if not matches:
        raise FileNotFoundError(f"No YAML file found for {item_id} under {dhf_path}")

    cwd = dhf_path.parent if dhf_path.name == "DHF" else dhf_path
    item_path = matches[0].relative_to(cwd)

    def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True, text=True, check=False,
        )

    _git(["config", "user.name", "GitHub Actions [bot]"])
    _git(["config", "user.email", "github-actions[bot]@users.noreply.github.com"])

    _git(["add", str(item_path)])
    staged = _git(["diff", "--staged", "--quiet"]).returncode != 0

    if not staged:
        return {"staged": False, "committed": False, "pushed": False}

    _git(["commit", "-m", message])
    committed = True

    pushed = False
    if push:
        result = _git(["push"])
        pushed = result.returncode == 0

    return {"staged": True, "committed": committed, "pushed": pushed}
