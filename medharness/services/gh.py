"""The one way this package runs the GitHub CLI."""

from __future__ import annotations

import os
import subprocess


def gh(args: list[str], *, token: str = "", timeout: int = 30) -> tuple[int, str]:
    """Run ``gh *args``: ``(returncode, stdout)``, or ``(1, reason)`` if it cannot start.

    The token is *token*, else ``$GH_TOKEN``, else ``$GITHUB_TOKEN`` — the order
    gh itself uses — and is passed to gh under both names.
    """
    env = {**os.environ}
    gh_token = token or env.get("GH_TOKEN", "") or env.get("GITHUB_TOKEN", "")
    if gh_token:
        env["GH_TOKEN"] = gh_token
        env["GITHUB_TOKEN"] = gh_token
    try:
        result = subprocess.run(  # noqa: S603
            ["gh", *args], capture_output=True, text=True, env=env, timeout=timeout,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return 1, str(exc)
    return result.returncode, result.stdout.strip()
