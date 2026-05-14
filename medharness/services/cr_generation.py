"""CR lifecycle AI generation orchestration."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from medharness.services import code_validation, design_validation, git
from medharness.services.cr_impact import (
    _build_design_impact_notes,
    _record_design_impact_in_cr,
    _replace_managed_block,
)
from medharness.services.prompt_assembly import (
    MAX_DIFF_CHARS,
    _append_skills,
    _assemble_analyze_prompt,
    _assemble_design_prompt,
    _assemble_design_prompt_with_spec_json,
    _assemble_develop_prompt,
    _assemble_generate_dhf_prompt,
    _assemble_review_code_prompt,
    _assemble_review_design_prompt,
    _assemble_review_spec_prompt,
    _build_dhf_context_block,
    _load_prompt,
    _load_skill,
)
from medharness.services.spec_validation import (
    extract_structured_analysis,
    parse_spec_frontmatter,
    validate_spec,
    write_spec_json,
)

__all__ = [
    "generate_code",
    "generate_design",
    "generate_dhf",
    "generate_spec",
]

# Default source paths scanned by develop-cr for diff injection and artifact
# collection. Override via the MEDHARNESS_CODE_PATHS environment variable
# (comma-separated, e.g. "src/,lib/") or by assigning a tuple before calling
# generate_code(). Projects using different layouts should set this once in
# their CI configuration or product repo entry point.
_DEFAULT_CODE_PATHS: tuple[str, ...] = tuple(
    p.strip()
    for p in os.environ.get("MEDHARNESS_CODE_PATHS", "apps/,packages/").split(",")
    if p.strip()
)


# ── GitHub PR feedback ────────────────────────────────────────────────────────

def _get_pr_feedback(pr_number: int) -> str:
    token = os.environ.get("GH_TOKEN", "") or os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    diagnostics = {
        "attempted": True,
        "pr_number": pr_number,
        "repo_env_present": bool(repo),
        "token_env_present": bool(token),
    }
    if not repo or not token:
        return {
            "prompt_text": "(PR feedback unavailable — GH_TOKEN and GITHUB_REPOSITORY not set)",
            "diagnostics": {
                **diagnostics,
                "comments_status": "skipped",
                "reviews_status": "skipped",
            },
            "warnings": [
                _warning(
                    "github_feedback_env_missing",
                    "PR feedback unavailable because GH_TOKEN/GITHUB_TOKEN or GITHUB_REPOSITORY is missing.",
                ),
            ],
        }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "medharness",
    }

    def _fetch(kind: str, url: str) -> dict[str, object]:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return {"status": "ok", "data": json.loads(resp.read()), "error": None}
        except urllib.error.HTTPError as exc:
            message = f"HTTP {exc.code}: {exc.reason}"
            return {
                "status": "http_error",
                "data": [{"error": message}],
                "error": message,
                "warning": _warning(f"github_{kind}_http_error", f"GitHub {kind} fetch failed: {message}."),
            }
        except (urllib.error.URLError, OSError) as exc:
            message = str(exc)
            return {
                "status": "transport_error",
                "data": [{"error": message}],
                "error": message,
                "warning": _warning(f"github_{kind}_transport_error", f"GitHub {kind} fetch failed: {message}."),
            }
        except json.JSONDecodeError as exc:
            message = str(exc)
            return {
                "status": "decode_error",
                "data": [{"error": message}],
                "error": message,
                "warning": _warning(f"github_{kind}_decode_error", f"GitHub {kind} response could not be decoded: {message}."),
            }

    base = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    comments = _fetch("comments", f"{base}/comments")
    reviews = _fetch("reviews", f"{base}/reviews")
    warnings = [
        warning
        for warning in (comments.get("warning"), reviews.get("warning"))
        if isinstance(warning, dict)
    ]
    return {
        "prompt_text": json.dumps(
            {"comments": comments["data"], "reviews": reviews["data"]},
            indent=2,
        ),
        "diagnostics": {
            **diagnostics,
            "comments_status": comments["status"],
            "comments_error": comments["error"],
            "reviews_status": reviews["status"],
            "reviews_error": reviews["error"],
            "comments_count": len(comments["data"]) if isinstance(comments["data"], list) else 0,
            "reviews_count": len(reviews["data"]) if isinstance(reviews["data"], list) else 0,
        },
        "warnings": warnings,
    }


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _warning(code: str, message: str, details: dict | None = None) -> dict:
    warning = {"code": code, "message": message}
    if details:
        warning["details"] = details
    return warning


def _error_code(field: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", field).strip("_").lower()
    return normalized or "validation_error"


def _normalize_errors(errors: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for error in errors:
        item = dict(error)
        item.setdefault("code", _error_code(str(item.get("field", ""))))
        normalized.append(item)
    return normalized


def _begin_step(name: str, details: dict | None = None) -> tuple[dict, float]:
    return {
        "name": name,
        "started_at": _now_iso(),
        "details": dict(details or {}),
    }, time.perf_counter()


def _finish_step(step: dict, started_perf: float, outcome: str, details: dict | None = None) -> dict:
    merged = dict(step.get("details") or {})
    if details:
        merged.update(details)
    step["outcome"] = outcome
    step["elapsed_ms"] = int((time.perf_counter() - started_perf) * 1000)
    step["details"] = merged
    return step


def _truncate(text: str, limit: int = 300) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[:limit].rstrip() + "..."


def _run_claude_step(
    *,
    name: str,
    prompt: str,
    steps: list[dict],
    warnings: list[dict],
    critical: bool,
) -> tuple[int, str]:
    step, step_perf = _begin_step(name, {"tool": "claude"})
    rc, output = _run_claude(prompt)
    cli_found = "claude CLI not found" not in output
    outcome = "ok" if rc == 0 else ("failed" if critical else "warning")
    details = {"exit_code": rc, "cli_found": cli_found}
    if output.strip():
        details["output_excerpt"] = _truncate(output)
    steps.append(_finish_step(step, step_perf, outcome, details))
    if rc != 0:
        warnings.append(
            _warning(
                "claude_cli_missing" if not cli_found else "claude_step_failed",
                f"Claude step `{name}` exited with code {rc}.",
                {"step": name, "exit_code": rc},
            )
        )
    return rc, output


def _final_progress(steps: list[dict]) -> dict:
    return {
        "current_step": None,
        "completed_steps": len(steps),
        "total_steps": len(steps),
    }


def _determine_outcome(
    *,
    errors: list[dict],
    fix_attempted: bool,
    critical_step_failed: bool,
) -> str:
    if critical_step_failed:
        return "tool_error"
    if errors:
        return "completed_with_errors"
    if fix_attempted:
        return "corrected"
    return "ok"


def _build_summary(
    *,
    stage: str,
    outcome: str,
    errors: list[dict],
    fix_attempted: bool,
    warnings: list[dict],
) -> str:
    stage_label = {
        "spec": "Spec",
        "design": "Design generation",
        "develop": "Implementation generation",
        "generate_dhf": "DHF cascade generation",
    }.get(stage, stage.capitalize())
    if outcome == "tool_error":
        if warnings:
            return f"{stage_label} hit a tool or environment error: {warnings[0]['message']}"
        return f"{stage_label} hit a tool or environment error."
    if outcome == "completed_with_errors":
        suffix = " after one fix attempt" if fix_attempted else ""
        return (
            f"{stage_label} completed, but deterministic validation still found "
            f"{len(errors)} error(s){suffix}."
        )
    if outcome == "corrected":
        return f"{stage_label} completed after one successful fix pass."
    return f"{stage_label} completed successfully."


def _build_response(
    *,
    cr_id: str,
    stage: str,
    started_at: str,
    started_perf: float,
    inputs: dict,
    steps: list[dict],
    artifacts: dict,
    diagnostics: dict,
    warnings: list[dict],
    errors: list[dict],
    critical_step_failed: bool,
) -> dict:
    normalized_errors = _normalize_errors(errors)
    fix_attempted = bool(diagnostics.get("fix_attempted"))
    outcome = _determine_outcome(
        errors=normalized_errors,
        fix_attempted=fix_attempted,
        critical_step_failed=critical_step_failed,
    )
    return {
        "cr_id": cr_id,
        "stage": stage,
        "outcome": outcome,
        "summary": _build_summary(
            stage=stage,
            outcome=outcome,
            errors=normalized_errors,
            fix_attempted=fix_attempted,
            warnings=warnings,
        ),
        "timing": {
            "started_at": started_at,
            "elapsed_ms": int((time.perf_counter() - started_perf) * 1000),
        },
        "inputs": inputs,
        "progress": _final_progress(steps),
        "steps": steps,
        "artifacts": artifacts,
        "diagnostics": diagnostics,
        "warnings": warnings,
        "errors": normalized_errors,
    }


def generate_spec(cr_id: str, dhf_path: Path, pr_number: int | None = None) -> dict:
    """Generate or revise the CR spec. Writes docs/cr-specs/<cr_id>-Spec.md."""
    started_at = _now_iso()
    started_perf = time.perf_counter()

    repo_root = dhf_path.resolve().parent
    spec_path = repo_root / "docs" / "cr-specs" / f"{cr_id}-Spec.md"
    steps: list[dict] = []
    warnings: list[dict] = []
    critical_step_failed = False
    diagnostics = {
        "anthropic_model": os.environ.get("ANTHROPIC_MODEL") or None,
        "github_feedback": {"attempted": False},
        "fix_attempted": False,
        "initial_error_count": 0,
        "final_error_count": 0,
    }
    inputs = {
        "dhf_path": str(dhf_path),
        "repo_root": str(repo_root),
        "spec_path": str(spec_path),
        "pr_number": pr_number,
        "revision_mode": pr_number is not None,
    }

    if pr_number:
        feedback_step, feedback_perf = _begin_step("fetch_pr_feedback")
        feedback = _get_pr_feedback(pr_number)
        diagnostics["github_feedback"] = feedback["diagnostics"]
        warnings.extend(feedback["warnings"])
        feedback_outcome = "warning" if feedback["warnings"] else "ok"
        steps.append(_finish_step(feedback_step, feedback_perf, feedback_outcome, feedback["diagnostics"]))
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "spec_revision", "used_pr_feedback": True},
        )
        prompt = (
            f"Read {spec_path} (the current spec on this branch), "
            f"then revise it based on the following pull request review feedback. "
            f"Update docs/cr-specs/ only if changes are warranted.\n\n"
            f"Review feedback:\n{feedback['prompt_text']}"
        )
        steps.append(_finish_step(prompt_step, prompt_perf, "ok"))
    else:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "spec_generation", "used_pr_feedback": False},
        )
        prompt = _assemble_analyze_prompt(cr_id, dhf_path)
        steps.append(_finish_step(prompt_step, prompt_perf, "ok"))

    spec_path.parent.mkdir(parents=True, exist_ok=True)
    rc, _ = _run_claude_step(
        name="run_initial_generation",
        prompt=prompt,
        steps=steps,
        warnings=warnings,
        critical=True,
    )
    critical_step_failed = critical_step_failed or rc != 0

    analysis: dict | None = None
    errors: list[dict] = []
    if spec_path.exists():
        validate_step, validate_perf = _begin_step("validate_initial", {"validator": "spec_validation"})
        errors = validate_spec(spec_path, cr_id, dhf_path)
        diagnostics["initial_error_count"] = len(errors)
        diagnostics["final_error_count"] = len(errors)
        steps.append(
            _finish_step(
                validate_step,
                validate_perf,
                "failed" if errors else "ok",
                {"error_count": len(errors)},
            )
        )
        if errors:
            diagnostics["fix_attempted"] = True
            fix_prompt = (
                f"The spec at {spec_path} failed validation.\n"
                f"{_format_error_lines(errors)}\n\n"
                f"Fix only the front-matter fields that caused errors. "
                f"Do not change the markdown content."
            )
            rc, _ = _run_claude_step(
                name="run_fix_generation",
                prompt=fix_prompt,
                steps=steps,
                warnings=warnings,
                critical=True,
            )
            critical_step_failed = critical_step_failed or rc != 0
            validate_fix_step, validate_fix_perf = _begin_step("validate_after_fix", {"validator": "spec_validation"})
            errors = validate_spec(spec_path, cr_id, dhf_path)
            diagnostics["final_error_count"] = len(errors)
            steps.append(
                _finish_step(
                    validate_fix_step,
                    validate_fix_perf,
                    "failed" if errors else "ok",
                    {"error_count": len(errors)},
                )
            )
        analysis = extract_structured_analysis(spec_path)
    else:
        warnings.append(
            _warning(
                "spec_file_missing",
                f"Expected generated spec file was not found at {spec_path}.",
            )
        )
        missing_step, missing_perf = _begin_step("validate_initial", {"validator": "spec_validation"})
        steps.append(
            _finish_step(
                missing_step,
                missing_perf,
                "warning",
                {"skipped": True, "reason": "spec_file_missing"},
            )
        )

    spec_json_path: str | None = None
    write_json_step, write_json_perf = _begin_step("write_spec_json")
    if spec_path.exists():
        fm = parse_spec_frontmatter(spec_path)
        if fm is not None:
            spec_json_path = str(write_spec_json(spec_path, fm))
    steps.append(
        _finish_step(
            write_json_step,
            write_json_perf,
            "ok" if spec_json_path else "warning",
            {"spec_json_path": spec_json_path},
        )
    )

    review_prompt = _augment_review_prompt(_assemble_review_spec_prompt(cr_id), errors)
    _run_claude_step(
        name="run_review",
        prompt=review_prompt,
        steps=steps,
        warnings=warnings,
        critical=False,
    )

    return _build_response(
        cr_id=cr_id,
        stage="spec",
        started_at=started_at,
        started_perf=started_perf,
        inputs=inputs,
        steps=steps,
        artifacts={
            "spec_path": str(spec_path),
            "spec_json_path": spec_json_path,
            "analysis": analysis,
        },
        diagnostics=diagnostics,
        warnings=warnings,
        errors=errors,
        critical_step_failed=critical_step_failed,
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
    steps: list[dict] = []
    warnings: list[dict] = []
    critical_step_failed = False
    diagnostics = {
        "anthropic_model": os.environ.get("ANTHROPIC_MODEL") or None,
        "github_feedback": {"attempted": False},
        "fix_attempted": False,
        "initial_error_count": 0,
        "final_error_count": 0,
    }
    inputs = {
        "dhf_path": str(dhf_path),
        "repo_root": str(repo_root),
        "spec_path": str(spec_path),
        "pr_number": pr_number,
        "revision_mode": pr_number is not None,
        "since_ref": "origin/main",
    }

    if pr_number:
        feedback_step, feedback_perf = _begin_step("fetch_pr_feedback")
        feedback = _get_pr_feedback(pr_number)
        diagnostics["github_feedback"] = feedback["diagnostics"]
        warnings.extend(feedback["warnings"])
        steps.append(
            _finish_step(
                feedback_step,
                feedback_perf,
                "warning" if feedback["warnings"] else "ok",
                feedback["diagnostics"],
            )
        )
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "design_revision", "used_pr_feedback": True},
        )
        prompt = (
            f"Read the DHF design items in DHF/ related to {cr_id}, "
            f"then revise them based on the following pull request review feedback.\n\n"
            f"Review feedback:\n{feedback['prompt_text']}"
        )
        steps.append(_finish_step(prompt_step, prompt_perf, "ok"))
    else:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "design_generation", "used_pr_feedback": False},
        )
        prompt = _assemble_design_prompt_with_spec_json(cr_id, spec_path, dhf_path)
        steps.append(
            _finish_step(
                prompt_step,
                prompt_perf,
                "ok",
                {"used_spec_json": spec_path.with_suffix(".json").exists()},
            )
        )

    rc, _ = _run_claude_step(
        name="run_initial_generation",
        prompt=prompt,
        steps=steps,
        warnings=warnings,
        critical=True,
    )
    critical_step_failed = critical_step_failed or rc != 0

    validate_step, validate_perf = _begin_step("validate_initial", {"validator": "design_validation"})
    errors = design_validation.validate_design(cr_id, dhf_path, spec_path)
    diagnostics["initial_error_count"] = len(errors)
    diagnostics["final_error_count"] = len(errors)
    steps.append(
        _finish_step(
            validate_step,
            validate_perf,
            "failed" if errors else "ok",
            {"error_count": len(errors)},
        )
    )
    if errors:
        diagnostics["fix_attempted"] = True
        fix_prompt = (
            f"The DHF design for {cr_id} failed deterministic validation:\n"
            f"{_format_error_lines(errors)}\n\n"
            f"Fix only the items needed to clear these errors via the medharness "
            f"CLI (`dhf item create` / `dhf item update`). Do not introduce other "
            f"changes."
        )
        rc, _ = _run_claude_step(
            name="run_fix_generation",
            prompt=fix_prompt,
            steps=steps,
            warnings=warnings,
            critical=True,
        )
        critical_step_failed = critical_step_failed or rc != 0
        validate_fix_step, validate_fix_perf = _begin_step("validate_after_fix", {"validator": "design_validation"})
        errors = design_validation.validate_design(cr_id, dhf_path, spec_path)
        diagnostics["final_error_count"] = len(errors)
        steps.append(
            _finish_step(
                validate_fix_step,
                validate_fix_perf,
                "failed" if errors else "ok",
                {"error_count": len(errors)},
            )
        )

    review_prompt = _augment_review_prompt(_assemble_review_design_prompt(cr_id), errors)
    _run_claude_step(
        name="run_review",
        prompt=review_prompt,
        steps=steps,
        warnings=warnings,
        critical=False,
    )

    artifact_step, artifact_perf = _begin_step("collect_artifacts", {"kind": "dhf_items_changed"})
    items_changed = git.collect_dhf_item_changes(repo_root, "origin/main")
    steps.append(_finish_step(artifact_step, artifact_perf, "ok", {"items_changed": items_changed}))
    design_impact = {"recorded": False, "reason": "skipped_due_to_validation_errors"}
    if not errors:
        impact_step, impact_perf = _begin_step("record_design_impact")
        design_impact = _record_design_impact_in_cr(cr_id, dhf_path, spec_path, items_changed)
        steps.append(
            _finish_step(
                impact_step,
                impact_perf,
                "ok" if design_impact.get("recorded") else "warning",
                design_impact,
            )
        )

    return _build_response(
        cr_id=cr_id,
        stage="design",
        started_at=started_at,
        started_perf=started_perf,
        inputs=inputs,
        steps=steps,
        artifacts={
            "spec_path": str(spec_path),
            "items_changed": items_changed,
            "design_impact": design_impact,
        },
        diagnostics=diagnostics,
        warnings=warnings,
        errors=errors,
        critical_step_failed=critical_step_failed,
    )


def generate_dhf(cr_id: str, dhf_path: Path, pr_number: int | None = None) -> dict:
    """Generate the complete DHF item cascade for a CR in a single LLM session.

    The V-model (CR→CRS→SYS→{SYSARCH,RISK,RCM}→SRS→SWDD) is the reasoning
    framework embedded in the prompt. The LLM writes items via the medharness
    CLI and validates traceability inline before returning.

    Python-side validation runs as a safety net. If errors remain after the
    LLM's inline self-correction, one deterministic fix pass is attempted.
    No spec file is produced; this command replaces analyze-cr + design-cr.
    """
    started_at = _now_iso()
    started_perf = time.perf_counter()

    repo_root = dhf_path.resolve().parent
    steps: list[dict] = []
    warnings: list[dict] = []
    critical_step_failed = False
    diagnostics: dict = {
        "anthropic_model": os.environ.get("ANTHROPIC_MODEL") or None,
        "github_feedback": {"attempted": False},
        "fix_attempted": False,
        "initial_error_count": 0,
        "final_error_count": 0,
    }
    inputs = {
        "dhf_path": str(dhf_path),
        "repo_root": str(repo_root),
        "pr_number": pr_number,
        "revision_mode": pr_number is not None,
        "since_ref": "origin/main",
    }

    if pr_number:
        feedback_step, feedback_perf = _begin_step("fetch_pr_feedback")
        feedback = _get_pr_feedback(pr_number)
        diagnostics["github_feedback"] = feedback["diagnostics"]
        warnings.extend(feedback["warnings"])
        steps.append(
            _finish_step(
                feedback_step,
                feedback_perf,
                "warning" if feedback["warnings"] else "ok",
                feedback["diagnostics"],
            )
        )
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "generate_dhf_revision", "used_pr_feedback": True},
        )
        prompt = (
            f"Read the DHF items in DHF/ related to {cr_id}, "
            f"then revise them based on the following pull request review feedback. "
            f"Continue using the CLI (`dhf item create` / `dhf item update`) only. "
            f"After making changes, re-run:\n"
            f"  python -m medharness --dhf DHF dhf validate schema\n"
            f"  python -m medharness --dhf DHF dhf validate traceability\n\n"
            f"Review feedback:\n{feedback['prompt_text']}"
        )
        block = _build_dhf_context_block(dhf_path)
        if block:
            prompt += "\n\n" + block
        steps.append(_finish_step(prompt_step, prompt_perf, "ok"))
    else:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "generate_dhf_generation", "used_pr_feedback": False},
        )
        prompt = _assemble_generate_dhf_prompt(cr_id, dhf_path)
        steps.append(_finish_step(prompt_step, prompt_perf, "ok"))

    rc, _ = _run_claude_step(
        name="run_initial_generation",
        prompt=prompt,
        steps=steps,
        warnings=warnings,
        critical=True,
    )
    critical_step_failed = critical_step_failed or rc != 0

    items_changed = git.collect_dhf_item_changes(repo_root, "origin/main")
    validate_step, validate_perf = _begin_step(
        "validate_initial", {"validator": "validate_generate_dhf"}
    )
    errors: list[dict] = design_validation.validate_generate_dhf(
        cr_id, dhf_path, items_changed
    )
    diagnostics["initial_error_count"] = len(errors)
    diagnostics["final_error_count"] = len(errors)
    steps.append(
        _finish_step(
            validate_step,
            validate_perf,
            "failed" if errors else "ok",
            {"error_count": len(errors)},
        )
    )

    if errors:
        diagnostics["fix_attempted"] = True
        fix_prompt = (
            f"The DHF cascade for {cr_id} failed deterministic validation:\n"
            f"{_format_error_lines(errors)}\n\n"
            f"Fix only the items needed to clear these errors via the medharness "
            f"CLI (`dhf item create` / `dhf item update`). Do not introduce other "
            f"changes. After fixing, re-run:\n"
            f"  python -m medharness --dhf DHF dhf validate schema\n"
            f"  python -m medharness --dhf DHF dhf validate traceability"
        )
        rc, _ = _run_claude_step(
            name="run_fix_generation",
            prompt=fix_prompt,
            steps=steps,
            warnings=warnings,
            critical=True,
        )
        critical_step_failed = critical_step_failed or rc != 0
        items_changed = git.collect_dhf_item_changes(repo_root, "origin/main")
        validate_fix_step, validate_fix_perf = _begin_step(
            "validate_after_fix", {"validator": "validate_generate_dhf"}
        )
        errors = design_validation.validate_generate_dhf(cr_id, dhf_path, items_changed)
        diagnostics["final_error_count"] = len(errors)
        steps.append(
            _finish_step(
                validate_fix_step,
                validate_fix_perf,
                "failed" if errors else "ok",
                {"error_count": len(errors)},
            )
        )

    artifact_step, artifact_perf = _begin_step(
        "collect_artifacts", {"kind": "dhf_items_changed"}
    )
    steps.append(
        _finish_step(artifact_step, artifact_perf, "ok", {"items_changed": items_changed})
    )

    design_impact: dict = {"recorded": False, "reason": "skipped_due_to_validation_errors"}
    if not errors:
        impact_step, impact_perf = _begin_step("record_design_impact")
        design_impact = _record_design_impact_in_cr(
            cr_id, dhf_path, repo_root / "docs" / "cr-specs" / f"{cr_id}-Spec.md", items_changed
        )
        steps.append(
            _finish_step(
                impact_step,
                impact_perf,
                "ok" if design_impact.get("recorded") else "warning",
                design_impact,
            )
        )

    return _build_response(
        cr_id=cr_id,
        stage="generate_dhf",
        started_at=started_at,
        started_perf=started_perf,
        inputs=inputs,
        steps=steps,
        artifacts={
            "items_changed": items_changed,
            "design_impact": design_impact,
        },
        diagnostics=diagnostics,
        warnings=warnings,
        errors=errors,
        critical_step_failed=critical_step_failed,
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
    steps: list[dict] = []
    warnings: list[dict] = []
    critical_step_failed = False
    diagnostics = {
        "anthropic_model": os.environ.get("ANTHROPIC_MODEL") or None,
        "github_feedback": {"attempted": False},
        "fix_attempted": False,
        "initial_error_count": 0,
        "final_error_count": 0,
    }
    inputs = {
        "dhf_path": str(dhf_path),
        "repo_root": str(repo_root),
        "spec_path": str(spec_path),
        "pr_number": pr_number,
        "revision_mode": pr_number is not None,
        "since_ref": "origin/main",
    }

    if pr_number:
        feedback_step, feedback_perf = _begin_step("fetch_pr_feedback")
        feedback = _get_pr_feedback(pr_number)
        diagnostics["github_feedback"] = feedback["diagnostics"]
        warnings.extend(feedback["warnings"])
        steps.append(
            _finish_step(
                feedback_step,
                feedback_perf,
                "warning" if feedback["warnings"] else "ok",
                feedback["diagnostics"],
            )
        )
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "develop_revision", "used_pr_feedback": True},
        )
        prompt = (
            f"Read the implementation on this branch related to {cr_id}, "
            f"then revise it based on the following pull request review feedback.\n\n"
            f"Review feedback:\n{feedback['prompt_text']}"
        )
        steps.append(_finish_step(prompt_step, prompt_perf, "ok"))
    else:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "develop_generation", "used_pr_feedback": False},
        )
        prompt = _assemble_develop_prompt(cr_id)
        diff = git.compute_diff(repo_root, "origin/main", *_DEFAULT_CODE_PATHS)
        if diff:
            truncated = len(diff) > MAX_DIFF_CHARS
            diff_body = diff[:MAX_DIFF_CHARS]
            prompt += (
                "\n\n## Existing Implementation (since origin/main)\n\n"
                "The following changes have already been made on this branch. "
                "Implement only what is still missing according to the spec "
                "— do not rewrite existing work.\n\n"
                f"```diff\n{diff_body}\n```\n"
            )
            if truncated:
                prompt += (
                    f"_(diff truncated at {MAX_DIFF_CHARS} chars — "
                    "remaining changes not shown)_\n"
                )
        steps.append(_finish_step(prompt_step, prompt_perf, "ok", {"diff_injected": bool(diff)}))

    rc, _ = _run_claude_step(
        name="run_initial_generation",
        prompt=prompt,
        steps=steps,
        warnings=warnings,
        critical=True,
    )
    critical_step_failed = critical_step_failed or rc != 0

    validate_step, validate_perf = _begin_step("validate_initial", {"validator": "code_validation"})
    errors = code_validation.validate_code(cr_id, dhf_path, spec_path)
    diagnostics["initial_error_count"] = len(errors)
    diagnostics["final_error_count"] = len(errors)
    steps.append(
        _finish_step(
            validate_step,
            validate_perf,
            "failed" if errors else "ok",
            {"error_count": len(errors)},
        )
    )
    if errors:
        diagnostics["fix_attempted"] = True
        fix_prompt = (
            f"The implementation for {cr_id} is missing required test annotations:\n"
            f"{_format_error_lines(errors)}\n\n"
            f"Add only the missing colocated tests with `@links:` annotations. "
            f"Do not introduce other changes."
        )
        rc, _ = _run_claude_step(
            name="run_fix_generation",
            prompt=fix_prompt,
            steps=steps,
            warnings=warnings,
            critical=True,
        )
        critical_step_failed = critical_step_failed or rc != 0
        validate_fix_step, validate_fix_perf = _begin_step("validate_after_fix", {"validator": "code_validation"})
        errors = code_validation.validate_code(cr_id, dhf_path, spec_path)
        diagnostics["final_error_count"] = len(errors)
        steps.append(
            _finish_step(
                validate_fix_step,
                validate_fix_perf,
                "failed" if errors else "ok",
                {"error_count": len(errors)},
            )
        )

    review_prompt = _augment_review_prompt(_assemble_review_code_prompt(cr_id), errors)
    _run_claude_step(
        name="run_review",
        prompt=review_prompt,
        steps=steps,
        warnings=warnings,
        critical=False,
    )

    artifact_step, artifact_perf = _begin_step("collect_artifacts", {"kind": "files_changed"})
    files_changed = git.collect_path_changes(repo_root, "origin/main", *_DEFAULT_CODE_PATHS)
    steps.append(_finish_step(artifact_step, artifact_perf, "ok", {"files_changed": files_changed}))

    return _build_response(
        cr_id=cr_id,
        stage="develop",
        started_at=started_at,
        started_perf=started_perf,
        inputs=inputs,
        steps=steps,
        artifacts={
            "spec_path": str(spec_path),
            "files_changed": files_changed,
        },
        diagnostics=diagnostics,
        warnings=warnings,
        errors=errors,
        critical_step_failed=critical_step_failed,
    )
