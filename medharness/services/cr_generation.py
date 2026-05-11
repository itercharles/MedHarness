"""CR lifecycle AI generation — assemble prompt, run claude, self-correct."""

import importlib.resources
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


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


def _assemble_review_spec_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_spec.md").replace("{{cr_id}}", cr_id)


def _assemble_review_design_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_design.md").replace("{{cr_id}}", cr_id)


def _assemble_review_code_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_code.md").replace("{{cr_id}}", cr_id)


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
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    except FileNotFoundError:
        return 1, "claude CLI not found — install @anthropic-ai/claude-code"
    combined = result.stdout
    if result.stderr:
        combined += "\n" + result.stderr
    return result.returncode, combined


# ── Public API ────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _build_response(
    *,
    cr_id: str,
    stage: str,
    started_at: str,
    started_perf: float,
    corrections: int,
    errors: list[dict],
    extra: dict | None = None,
) -> dict:
    """Compose the standard generate-* response payload.

    Shape (all keys always present):
        cr_id, stage, status, corrections, validation, errors,
        started_at, elapsed_ms, plus any caller-supplied ``extra``.

    ``status`` is ``"ok"`` when no residual errors remain, else
    ``"completed_with_errors"``. ``validation`` is the finer-grained label
    used historically (``"passed"`` / ``"corrected"`` for spec,
    ``"passed"`` / ``"residual_errors"`` for design/develop).
    """
    elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
    if stage == "spec":
        validation = "passed" if corrections == 0 else "corrected"
    else:
        validation = "passed" if not errors else "residual_errors"
    response = {
        "cr_id": cr_id,
        "stage": stage,
        "status": "ok" if not errors else "completed_with_errors",
        "corrections": corrections,
        "validation": validation,
        "errors": list(errors),
        "started_at": started_at,
        "elapsed_ms": elapsed_ms,
    }
    if extra:
        response.update(extra)
    return response


def generate_spec(cr_id: str, dhf_path: Path, pr_number: int | None = None) -> dict:
    """Generate or revise the CR spec. Writes docs/cr-specs/<cr_id>-Spec.md."""
    started_at = _now_iso()
    started_perf = time.perf_counter()

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

    analysis: dict | None = None
    corrections = 0
    errors: list[dict] = []
    if spec_path.exists():
        from medharness.services.spec_validation import (  # noqa: PLC0415
            extract_structured_analysis,
            validate_spec,
        )
        errors = validate_spec(spec_path, cr_id, dhf_path)
        if errors:
            corrections += 1
            fix_prompt = (
                f"The spec at {spec_path} failed validation.\n"
                f"{_format_error_lines(errors)}\n\n"
                f"Fix only the front-matter fields that caused errors. "
                f"Do not change the markdown content."
            )
            _run_claude(fix_prompt)
            errors = validate_spec(spec_path, cr_id, dhf_path)
        analysis = extract_structured_analysis(spec_path)

    # Write JSON companion regardless of residual errors.
    spec_json_path: str | None = None
    if spec_path.exists():
        from medharness.services.spec_validation import (  # noqa: PLC0415
            parse_spec_frontmatter,
            write_spec_json,
        )
        fm = parse_spec_frontmatter(spec_path)
        if fm is not None:
            spec_json_path = str(write_spec_json(spec_path, fm))

    review_prompt = _augment_review_prompt(_assemble_review_spec_prompt(cr_id), errors)
    _run_claude(review_prompt)

    return _build_response(
        cr_id=cr_id,
        stage="spec",
        started_at=started_at,
        started_perf=started_perf,
        corrections=corrections,
        errors=errors,
        extra={
            "spec_path": str(spec_path),
            "analysis": analysis,
            "spec_json_path": spec_json_path,
        },
    )


def _format_error_lines(errors: list[dict]) -> str:
    return "\n".join(
        f"- {e.get('field', '?')}: {e.get('issue', '')} (fix: {e.get('fix', '')})"
        for e in errors
    )


def _augment_review_prompt(base: str, errors: list[dict]) -> str:
    """Attach a 'Deterministic Checks' note to a soft-review prompt.

    When deterministic checks pass we tell the reviewer not to re-derive them;
    when residual issues remain we surface them so the review captures the gap.
    """
    if not errors:
        return base + (
            "\n\n## Deterministic Checks (already passed)\n\n"
            "Schema, traceability, and the presence of all spec `affected_items` "
            "(or required `@links:` test annotations) have been verified "
            "mechanically. Do not re-derive them — focus on judgment questions "
            "that a script cannot answer."
        )
    residual = "\n".join(f"- {e.get('field', '?')}: {e.get('issue', '')}" for e in errors)
    return base + (
        "\n\n## Deterministic Checks (residual issues)\n\n"
        f"The following deterministic-check failures remain after one fix attempt:\n"
        f"{residual}\n\nNote these in the review output."
    )


def generate_design(cr_id: str, dhf_path: Path, pr_number: int | None = None) -> dict:
    """Generate or revise DHF design items for a CR.

    Pipeline: design pass → deterministic validation → fix-only pass on
    errors → trimmed soft-review pass. Mechanical checks (schema,
    traceability, presence of spec `affected_items`) live in
    :mod:`medharness.services.design_validation`; the soft review focuses
    on intent, completeness, and clarity.
    """
    started_at = _now_iso()
    started_perf = time.perf_counter()

    repo_root = dhf_path.resolve().parent
    spec_path = repo_root / "docs" / "cr-specs" / f"{cr_id}-Spec.md"

    if pr_number:
        feedback = _get_pr_feedback(pr_number)
        prompt = (
            f"Read the DHF design items in DHF/ related to {cr_id}, "
            f"then revise them based on the following pull request review feedback.\n\n"
            f"Review feedback:\n{feedback}"
        )
    else:
        prompt = _assemble_design_prompt(cr_id)
        from medharness.services.spec_validation import read_spec_json  # noqa: PLC0415
        spec_json = read_spec_json(spec_path)
        if spec_json:
            prompt = prompt + (
                f"\n\n## Pre-computed Spec Summary (from {cr_id}-Spec.json)\n"
                "The following structured data was extracted from the approved spec. "
                "Use it directly — do not re-read or re-interpret the Markdown spec.\n"
                f"```json\n{json.dumps(spec_json, indent=2)}\n```\n"
            )

    _run_claude(prompt)

    from medharness.services.design_validation import validate_design  # noqa: PLC0415
    errors = validate_design(cr_id, dhf_path, spec_path)
    corrections = 0
    if errors:
        corrections += 1
        fix_prompt = (
            f"The DHF design for {cr_id} failed deterministic validation:\n"
            f"{_format_error_lines(errors)}\n\n"
            f"Fix only the items needed to clear these errors via the medharness "
            f"CLI (`dhf item create` / `dhf item update`). Do not introduce other "
            f"changes."
        )
        _run_claude(fix_prompt)
        errors = validate_design(cr_id, dhf_path, spec_path)

    review_prompt = _augment_review_prompt(_assemble_review_design_prompt(cr_id), errors)
    _run_claude(review_prompt)

    from medharness.services.git import collect_dhf_item_changes  # noqa: PLC0415
    items_changed = collect_dhf_item_changes(repo_root, "origin/main")

    return _build_response(
        cr_id=cr_id,
        stage="design",
        started_at=started_at,
        started_perf=started_perf,
        corrections=corrections,
        errors=errors,
        extra={"items_changed": items_changed},
    )


def generate_code(cr_id: str, dhf_path: Path, pr_number: int | None = None) -> dict:
    """Generate or revise implementation code for a CR.

    Pipeline: develop pass → deterministic validation (test annotations vs.
    spec `test_plan.needs_new_tc`) → fix-only pass on errors → trimmed
    soft-review pass.
    """
    started_at = _now_iso()
    started_perf = time.perf_counter()

    repo_root = dhf_path.resolve().parent
    spec_path = repo_root / "docs" / "cr-specs" / f"{cr_id}-Spec.md"

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

    from medharness.services.code_validation import validate_code  # noqa: PLC0415
    errors = validate_code(cr_id, dhf_path, spec_path)
    corrections = 0
    if errors:
        corrections += 1
        fix_prompt = (
            f"The implementation for {cr_id} is missing required test annotations:\n"
            f"{_format_error_lines(errors)}\n\n"
            f"Add only the missing colocated tests with `@links:` annotations. "
            f"Do not introduce other changes."
        )
        _run_claude(fix_prompt)
        errors = validate_code(cr_id, dhf_path, spec_path)

    review_prompt = _augment_review_prompt(_assemble_review_code_prompt(cr_id), errors)
    _run_claude(review_prompt)

    from medharness.services.git import collect_path_changes  # noqa: PLC0415
    files_changed = collect_path_changes(repo_root, "origin/main", "apps/", "packages/")

    return _build_response(
        cr_id=cr_id,
        stage="develop",
        started_at=started_at,
        started_perf=started_perf,
        corrections=corrections,
        errors=errors,
        extra={"files_changed": files_changed},
    )
