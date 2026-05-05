"""Git helpers for CI workflows — commit and push DHF item changes."""

from __future__ import annotations

import subprocess
from pathlib import Path


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
