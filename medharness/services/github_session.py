"""Claude session ID storage via GitHub PR comments.

Wraps the ``gh`` CLI to store and retrieve session IDs for iterative
Claude Code agent runs in CI workflows.
"""

from __future__ import annotations

import os
import subprocess

_MARKER_START = "<!-- claude-session:"
_MARKER_END = "-->"


def put_session(pr_number: int | str, session_id: str, *, token: str = "") -> str:
    """Store a Claude session ID as a PR comment marker.

    Returns the URL of the comment (or empty string on failure).
    """
    gh_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    body = f"{_MARKER_START} {session_id} {_MARKER_END}"
    env = {**os.environ}
    if gh_token:
        env["GH_TOKEN"] = gh_token
        env["GITHUB_TOKEN"] = gh_token
    try:
        result = subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--body", body],
            capture_output=True, text=True, env=env, timeout=15,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def get_session(pr_number: int | str, *, token: str = "") -> str:
    """Retrieve the last stored Claude session ID from PR comments.

    Returns the session ID string (empty if not found).
    """
    gh_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    env = {**os.environ}
    if gh_token:
        env["GH_TOKEN"] = gh_token
        env["GITHUB_TOKEN"] = gh_token
    try:
        result = subprocess.run(
            [
                "gh", "pr", "view", str(pr_number),
                "--json", "comments",
                "--jq",
                f'[.comments[].body | select(startswith("{_MARKER_START}"))] | last | ltrimstr("{_MARKER_START} ") | rtrimstr(" {_MARKER_END}")',
            ],
            capture_output=True, text=True, env=env, timeout=15,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""
