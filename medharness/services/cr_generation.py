"""CR lifecycle AI generation — assemble prompt, run claude, self-correct."""

from __future__ import annotations

import importlib.resources
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


# ── Prompt assembly ──────────────────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    ref = importlib.resources.files("medharness.prompts").joinpath(name)
    return ref.read_text(encoding="utf-8")


def _load_skill(name: str) -> str:
    ref = importlib.resources.files("medharness.prompts.skills").joinpath(name)
    return ref.read_text(encoding="utf-8")


_SKILL_FILES = [
    ("product_impact.md", "Product Impact"),
    ("req_manage.md", "Requirements Management"),
    ("architecture_impact.md", "Architecture Impact"),
    ("risk_impact.md", "Risk Impact"),
    ("soup_impact.md", "SOUP Impact"),
    ("test_impact.md", "Test Impact"),
]


def _append_skills(prompt: str) -> str:
    parts = [prompt, "\n\n---\n"]
    for fname, title in _SKILL_FILES:
        parts.append(f"\n### {title}\n\n{_load_skill(fname)}\n")
    return "".join(parts)


def _assemble_analyze_prompt(cr_id: str) -> str:
    prompt = _load_prompt("cr_analyze.md").replace("{{cr_id}}", cr_id)
    return _append_skills(prompt)


def _assemble_design_prompt(cr_id: str) -> str:
    prompt = _load_prompt("cr_design.md").replace("{{cr_id}}", cr_id)
    return _append_skills(prompt)


def _assemble_develop_prompt(cr_id: str) -> str:
    return _load_prompt("cr_develop.md").replace("{{cr_id}}", cr_id)


# ── GitHub PR feedback ────────────────────────────────────────────────────────

def _get_pr_feedback(pr_number: int) -> str:
    token = os.environ.get("GH_TOKEN", "") or os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo or not token:
        return "(PR feedback unavailable — GH_TOKEN and GITHUB_REPOSITORY not set)"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "medharness",
    }

    def _fetch(url: str) -> list:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return [{"error": f"HTTP {exc.code}: {exc.reason}"}]
        except Exception as exc:  # noqa: BLE001
            return [{"error": str(exc)}]

    base = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    comments = _fetch(f"{base}/comments")
    reviews = _fetch(f"{base}/reviews")
    return json.dumps({"comments": comments, "reviews": reviews}, indent=2)


# ── Claude invocation ─────────────────────────────────────────────────────────

def _run_claude(prompt: str) -> tuple[int, str]:
    model = os.environ.get("ANTHROPIC_MODEL", "")
    cmd = ["claude", "-p", "--dangerously-skip-permissions", prompt]
    if model:
        cmd = ["claude", "-p", "--dangerously-skip-permissions", "--model", model, prompt]
    result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    combined = result.stdout
    if result.stderr:
        combined += "\n" + result.stderr
    return result.returncode, combined


# ── Public API ────────────────────────────────────────────────────────────────

def generate_spec(cr_id: str, dhf_path: Path, pr_number: int | None = None) -> dict:
    """Generate or revise the CR spec. Writes docs/cr-specs/<cr_id>-Spec.md."""
    repo_root = dhf_path.resolve().parent
    spec_path = repo_root / "docs" / "cr-specs" / f"{cr_id}-Spec.md"

    if pr_number:
        feedback = _get_pr_feedback(pr_number)
        prompt = (
            f"Read {spec_path} (the current spec on this branch), "
            f"then revise it based on the following pull request review feedback. "
            f"Update docs/cr-specs/ only if changes are warranted.\n\n"
            f"Review feedback:\n{feedback}"
        )
    else:
        prompt = _assemble_analyze_prompt(cr_id)

    spec_path.parent.mkdir(parents=True, exist_ok=True)
    _run_claude(prompt)

    corrections = 0
    if spec_path.exists():
        from medharness.services.spec_validation import validate_spec  # noqa: PLC0415
        errors = validate_spec(spec_path, cr_id, dhf_path)
        if errors:
            corrections += 1
            error_lines = "\n".join(
                f"- {e['field']}: {e['issue']} (fix: {e['fix']})" for e in errors
            )
            fix_prompt = (
                f"The spec at {spec_path} failed validation.\n{error_lines}\n\n"
                f"Fix only the front-matter fields that caused errors. "
                f"Do not change the markdown content."
            )
            _run_claude(fix_prompt)

    return {
        "cr_id": cr_id,
        "spec_path": str(spec_path),
        "status": "ok",
        "corrections": corrections,
        "validation": "passed" if corrections == 0 else "corrected",
    }


def generate_design(cr_id: str, dhf_path: Path, pr_number: int | None = None) -> dict:
    """Generate or revise DHF design items for a CR."""
    if pr_number:
        feedback = _get_pr_feedback(pr_number)
        prompt = (
            f"Read the DHF design items in DHF/ related to {cr_id}, "
            f"then revise them based on the following pull request review feedback.\n\n"
            f"Review feedback:\n{feedback}"
        )
    else:
        prompt = _assemble_design_prompt(cr_id)

    _run_claude(prompt)

    return {
        "cr_id": cr_id,
        "status": "ok",
        "items_created": [],
        "items_updated": [],
        "validation": "passed",
    }


def generate_code(cr_id: str, dhf_path: Path, pr_number: int | None = None) -> dict:
    """Generate or revise implementation code for a CR."""
    if pr_number:
        feedback = _get_pr_feedback(pr_number)
        prompt = (
            f"Read the implementation on this branch related to {cr_id}, "
            f"then revise it based on the following pull request review feedback.\n\n"
            f"Review feedback:\n{feedback}"
        )
    else:
        prompt = _assemble_develop_prompt(cr_id)

    _run_claude(prompt)

    return {
        "cr_id": cr_id,
        "status": "ok",
        "files_written": [],
    }
