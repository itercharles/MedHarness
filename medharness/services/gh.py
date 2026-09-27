"""The one way this package runs the GitHub CLI."""

from __future__ import annotations

import os
import subprocess


def gh(args: list[str], *, token: str = "", timeout: int = 30) -> tuple[int, str]:
    """Run ``gh *args``: ``(0, stdout)``, or on failure ``(returncode, gh's reason)``.

    The reason is gh's stderr, or why gh could not start.

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
    if result.returncode != 0:
        return result.returncode, (result.stderr or result.stdout).strip()
    return 0, result.stdout.strip()
