"""Deterministic post-implementation validation.

Checks that the test artifacts the spec promised are actually present in
the diff. Project-specific lint rules (TypeScript strict, Tailwind-only,
no inline styles, etc.) are enforced by the project's own CI; this
validator stays project-agnostic and focuses on what only the spec can tell us.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from medharness.services.spec_validation import parse_spec_frontmatter


def validate_code(
    cr_id: str,
    dhf_path: Path,
    spec_path: Path,
    since_ref: str = "origin/main",
) -> list[dict]:
    """Validate post-implementation diff against the spec test plan.

    Args:
        cr_id: CR identifier (e.g., "CR-042"). Currently unused, reserved.
        dhf_path: Path to the DHF root directory; its parent is the repo root.
        spec_path: Path to the approved spec markdown file.
        since_ref: Git ref to diff against (default ``origin/main``).

    Returns:
        List of error dicts with keys ``field``, ``issue``, ``fix``.
    """
    errors: list[dict] = []

    fm = parse_spec_frontmatter(spec_path)
    if not fm:
        return errors  # cannot validate without spec front-matter

    test_plan = fm.get("test_plan") or {}
    needs_new_tc = test_plan.get("needs_new_tc")
    if not isinstance(needs_new_tc, list) or not needs_new_tc:
        return errors

    repo_root = dhf_path.resolve().parent
    diff_text = _git_diff(repo_root, since_ref, "apps/", "packages/")
    added = "\n".join(
        line[1:]
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )

    for uid in needs_new_tc:
        if not _annotation_present(added, str(uid)):
            errors.append({
                "field": "test_plan.needs_new_tc",
                "issue": (
                    f"No newly added `@links:{uid}` annotation found in "
                    f"apps/ or packages/ since {since_ref}."
                ),
                "fix": (
                    f"Add a colocated `*.test.ts(x)` test that exercises {uid} "
                    f"and includes `@links:{uid}` in its describe/it title or a "
                    f"leading comment."
                ),
            })

    return errors


def _git_diff(repo_root: Path, since_ref: str, *paths: str) -> str:
    """Return git diff output, or empty string if git is unavailable / ref missing."""
    try:
        result = subprocess.run(
            ["git", "diff", since_ref, "--", *paths],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            check=False,
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout or ""


_ANNOTATION_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _annotation_present(text: str, uid: str) -> bool:
    """Return True if `@links:` followed (anywhere on the same line) by ``uid``.

    Matches both single-id (``@links:SRS-001``) and grouped
    (``@links:SRS-001,SRS-002``) annotations.
    """
    pat = _ANNOTATION_PATTERN_CACHE.get(uid)
    if pat is None:
        pat = re.compile(rf"@links:[^\n]*\b{re.escape(uid)}\b")
        _ANNOTATION_PATTERN_CACHE[uid] = pat
    return pat.search(text) is not None
