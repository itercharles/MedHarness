"""GitHub PR operations — comment posting and label management via gh CLI."""

from __future__ import annotations

import os
import subprocess
import urllib.parse


def _env(token: str = "") -> dict:
    gh_token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    env = {**os.environ}
    if gh_token:
        env["GH_TOKEN"] = gh_token
        env["GITHUB_TOKEN"] = gh_token
    return env


def post_pr_comment(pr_number: int | str, body: str, *, token: str = "") -> str:
    """Post a comment on a PR. Returns the comment URL or empty string on failure."""
    try:
        result = subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--body", body],
            capture_output=True, text=True, env=_env(token), timeout=15,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def remove_label(number: int | str, label: str, *, token: str = "") -> bool:
    """Remove a label from a PR or issue. Returns True on success (ignores 404)."""
    encoded = urllib.parse.quote(label, safe="")
    try:
        result = subprocess.run(
            ["gh", "api", "-X", "DELETE",
             f"repos/{{owner}}/{{repo}}/issues/{number}/labels/{encoded}"],
            capture_output=True, text=True, env=_env(token), timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False


def add_label(number: int | str, label: str, *, token: str = "") -> bool:
    """Add a label to a PR or issue. Returns True on success."""
    try:
        result = subprocess.run(
            ["gh", "api", "-X", "POST",
             f"repos/{{owner}}/{{repo}}/issues/{number}/labels",
             "-f", f"labels[]={label}"],
            capture_output=True, text=True, env=_env(token), timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False
