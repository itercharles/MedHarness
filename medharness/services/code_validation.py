"""Deterministic post-implementation validation.

Without a spec artifact, this validator is a no-op placeholder. Test coverage
enforcement is delegated to the project's own CI (TypeScript strict, Tailwind-only,
colocated test conventions, etc.) and the PR review process.
"""

from __future__ import annotations

from pathlib import Path


def validate_code(
    cr_id: str,
    dhf_path: Path,
    since_ref: str = "origin/main",
) -> list[dict]:
    """Validate post-implementation diff. Returns empty list."""
    return []
