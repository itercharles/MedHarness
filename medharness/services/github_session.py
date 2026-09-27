"""Claude session ID storage via GitHub PR comments.

Stores and retrieves session IDs for iterative Claude Code agent runs in CI
workflows.
"""

from __future__ import annotations

from medharness.services.gh import gh

_MARKER_START = "<!-- claude-session:"
_MARKER_END = "-->"


def put_session(pr_number: int | str, session_id: str, *, token: str = "") -> str:
    """Store a Claude session ID as a PR comment marker.

    Returns the URL of the comment (or empty string on failure).
    """
    body = f"{_MARKER_START} {session_id} {_MARKER_END}"
    rc, out = gh(["pr", "comment", str(pr_number), "--body", body], token=token, timeout=15)
    return out if rc == 0 else ""


def get_session(pr_number: int | str, *, token: str = "") -> str:
    """Retrieve the last stored Claude session ID from PR comments.

    Returns the session ID string (empty if not found).
    """
    rc, out = gh(
        [
            "pr", "view", str(pr_number),
            "--json", "comments",
            "--jq",
            f'[.comments[].body | select(startswith("{_MARKER_START}"))] | last // empty | ltrimstr("{_MARKER_START} ") | rtrimstr(" {_MARKER_END}")',
        ],
        token=token, timeout=15,
    )
    return out if rc == 0 and out != "null" else ""
