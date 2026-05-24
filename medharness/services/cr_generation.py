"""CR lifecycle AI generation orchestration."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from medharness.services import code_validation, design_validation, git
from medharness.services.cr_impact import _record_design_impact_in_cr
from medharness.services.github_session import get_session, put_session
from medharness.services.github_pr import post_pr_comment
from medharness.services.prompt_assembly import (
    MAX_DIFF_CHARS,
    _append_skills,
    _assemble_develop_prompt,
    _assemble_generate_dhf_prompt,
    _assemble_review_code_prompt,
    _assemble_review_design_prompt,
    _build_dhf_context_block,
)

__all__ = [
    "generate_code",
    "generate_dhf",
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

_MAX_DESIGN_REVIEW_CYCLES = 3
_MAX_CODE_REVIEW_CYCLES = 3


# ── Multi-provider LLM config ─────────────────────────────────────────────────

@dataclass
class LLMConfig:
    provider: str = "anthropic"  # "anthropic" | "openai" | "deepseek"
    model: str = ""
    api_key: str = ""
    base_url: str = ""


_PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
}

_PROVIDER_API_KEY_ENVS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def _resolve_stage_llm(stage: str) -> LLMConfig:
    """Resolve LLM config for a workflow stage.

    Reads MEDHARNESS_{DESIGN|DEVELOP|REVIEW}_MODEL env var.
    Format: "provider:model" (e.g. "deepseek:deepseek-chat", "openai:gpt-4o").
    Falls back to anthropic + ANTHROPIC_MODEL if not set.
    """
    raw = os.environ.get(f"MEDHARNESS_{stage.upper()}_MODEL", "")
    if raw:
        provider, _, model = raw.partition(":")
        if not model:
            provider, model = "anthropic", raw
    else:
        provider = "anthropic"
        model = os.environ.get("ANTHROPIC_MODEL", "")

    if provider == "anthropic":
        return LLMConfig(provider=provider, model=model)

    api_key_env = _PROVIDER_API_KEY_ENVS.get(provider, "")
    api_key = os.environ.get(api_key_env, "") if api_key_env else ""
    base_url = _PROVIDER_BASE_URLS.get(provider, "")
    return LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)


def _model_label(config: LLMConfig) -> str:
    if config.model:
        return f"{config.provider}:{config.model}"
    return config.provider


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

def _run_claude(prompt: str, *, resume_session: str = "", model: str = "") -> tuple[int, str, str]:
    """Invoke claude -p. Returns (exit_code, text_output, session_id).

    Uses --output-format json so the session_id is always captured from the
    structured response envelope. Falls back gracefully if JSON cannot be parsed.
    """
    effective_model = model or os.environ.get("ANTHROPIC_MODEL", "")
    cmd = ["claude", "-p", "--dangerously-skip-permissions", "--output-format", "json"]
    if effective_model:
        cmd += ["--model", effective_model]
    if resume_session:
        cmd += ["--resume", resume_session]
    cmd.append(prompt)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    except FileNotFoundError:
        return 1, "claude CLI not found — install @anthropic-ai/claude-code", ""
    session_id = ""
    text_output = result.stdout
    if result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            result_val = data.get("result")
            text_output = result_val if result_val is not None else result.stdout
            session_id = data.get("session_id") or ""
        except (json.JSONDecodeError, AttributeError):
            pass
    if result.stderr:
        text_output += "\n" + result.stderr
    return result.returncode, text_output, session_id


def _run_openai_compatible(
    prompt: str,
    *,
    model: str,
    api_key: str,
    base_url: str,
    max_turns: int = 100,
) -> tuple[int, str, str]:
    """Run an agentic loop against an OpenAI-compatible chat completions API.

    Exposes a single `bash` function tool. Loops until the model stops calling
    tools or max_turns is reached. Returns (exit_code, text_output, session_id).
    Session IDs are not supported by OpenAI-compatible APIs; always returns "".
    """
    if not api_key:
        return 1, f"API key not configured for provider at {base_url}", ""

    bash_tool = {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run."},
                },
                "required": ["command"],
            },
        },
    }

    messages: list[dict] = [{"role": "user", "content": prompt}]
    output_parts: list[str] = []

    for _ in range(max_turns):
        payload = json.dumps({"model": model, "tools": [bash_tool], "messages": messages}).encode()
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return 1, f"HTTP {exc.code}: {exc.reason}", ""
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            return 1, f"API error: {exc}", ""

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message", {})
        messages.append(message)

        content = message.get("content") or ""
        if content:
            output_parts.append(content)

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            break

        tool_results: list[dict] = []
        for tc in tool_calls:
            tc_id = tc.get("id", "")
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
                command = args.get("command", "")
                proc = subprocess.run(  # noqa: S603 S602
                    command, shell=True, capture_output=True, text=True, timeout=120
                )
                tc_output = proc.stdout + (("\n" + proc.stderr) if proc.stderr else "")
            except subprocess.TimeoutExpired:
                tc_output = "Command timed out."
            except Exception as exc:  # noqa: BLE001
                tc_output = f"Error: {exc}"
            tool_results.append({"role": "tool", "tool_call_id": tc_id, "content": tc_output})
        messages.extend(tool_results)

    return 0, "\n".join(output_parts), ""


def _run_llm(
    prompt: str,
    *,
    config: LLMConfig,
    resume_session: str = "",
) -> tuple[int, str, str]:
    """Dispatch to the appropriate LLM runner based on config.provider."""
    if config.provider == "anthropic":
        return _run_claude(prompt, resume_session=resume_session, model=config.model)
    return _run_openai_compatible(
        prompt,
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )


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
    resume_session: str = "",
    llm_config: LLMConfig | None = None,
) -> tuple[int, str, str]:
    """Run an LLM step. Returns (exit_code, output, session_id)."""
    config = llm_config or LLMConfig()
    is_anthropic = config.provider == "anthropic"
    tool_label = "claude" if is_anthropic else _model_label(config)
    step, step_perf = _begin_step(name, {"tool": tool_label})
    rc, output, session_id = _run_llm(prompt, config=config, resume_session=resume_session)
    cli_found = "claude CLI not found" not in output if is_anthropic else True
    outcome = "ok" if rc == 0 else ("failed" if critical else "warning")
    details: dict[str, object] = {"exit_code": rc, "cli_found": cli_found}
    if session_id:
        details["session_id"] = session_id
    if resume_session:
        details["resumed_session_id"] = resume_session
    if output.strip():
        details["output_excerpt"] = _truncate(output)
    steps.append(_finish_step(step, step_perf, outcome, details))
    if rc != 0:
        warnings.append(
            _warning(
                "claude_cli_missing" if (is_anthropic and not cli_found) else "claude_step_failed",
                f"Step `{name}` exited with code {rc}.",
                {"step": name, "exit_code": rc},
            )
        )
    return rc, output, session_id


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




def _format_ci_failures_for_prompt(ci_failures: dict) -> str:
    """Render structured CI failure JSON as a concise prompt block."""
    lines: list[str] = []
    summary = ci_failures.get("summary") or ""
    if summary:
        lines.append(f"**Summary:** {summary}\n")
    for category in ("missing_method", "unverified_test", "manual_review_required",
                      "uncovered", "errors", "failures"):
        items = ci_failures.get(category) or []
        if not items:
            continue
        lines.append(f"**{category.replace('_', ' ').title()}:**")
        for item in items[:20]:
            if isinstance(item, dict):
                uid = item.get("id") or item.get("item_id") or ""
                desc = item.get("issue") or item.get("title") or item.get("fix") or ""
                lines.append(f"  - {uid}: {desc}" if uid else f"  - {desc}")
            else:
                lines.append(f"  - {item}")
    return "\n".join(lines) if lines else str(ci_failures)


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


def _parse_review_data(text: str) -> dict:
    """Parse a review response into verdict and issue list.

    Returns {"verdict": "approved"|"needs_revision"|"unknown", "issues": [str, ...]}.
    Issues are extracted from Markdown task-list lines starting with "- [ ]".
    """
    verdict = "unknown"
    issues: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("**Verdict:**"):
            lower = stripped.lower()
            if "approved" in lower:
                verdict = "approved"
            elif "needs revision" in lower:
                verdict = "needs_revision"
        elif stripped.startswith("- [ ]"):
            issues.append(stripped[5:].strip())
    return {"verdict": verdict, "issues": issues}


def _read_design_review_data(repo_root: Path, cr_id: str) -> dict:
    """Read and parse the design review file.

    Returns {"verdict": ..., "issues": [...]} or {"verdict": "unknown", "issues": []}
    if the file is absent or unparseable.
    """
    review_file = repo_root / "docs" / "reviews" / f"{cr_id}-Design-Review.md"
    try:
        content = review_file.read_text()
    except OSError:
        return {"verdict": "unknown", "issues": []}
    return _parse_review_data(content)


def _build_review_result(stage_label: str, log: list[dict]) -> dict:
    """Build the client-facing review summary from per-cycle log entries.

    Returns {"cycles": [...], "narrative": [str, ...]}.
    """
    narrative = [f"{stage_label} completed."]
    for entry in log:
        cycle = entry["cycle"]
        verdict = entry["verdict"]
        issues = entry.get("issues") or []
        prefix = "Review" if cycle == 1 else f"Re-review (cycle {cycle})"
        if verdict == "needs_revision":
            n = len(issues)
            issue_str = f"{n} issue{'s' if n != 1 else ''}" if n else "issues"
            narrative.append(f"{prefix}: {issue_str} found — fix pass triggered.")
        elif verdict == "approved":
            msg = f"{prefix}: approved." if cycle == 1 else f"{prefix}: all issues resolved, approved."
            narrative.append(msg)
        else:
            narrative.append(f"{prefix}: completed (verdict unknown).")
    return {
        "cycles": [
            {"cycle": e["cycle"], "verdict": e["verdict"], "issues": e.get("issues") or []}
            for e in log
        ],
        "narrative": narrative,
    }


def _auto_post_pr_feedback(pr_number: int, cr_id: str, result: dict, *, token: str = "") -> list[str]:
    """Post warning and error comments to the PR. Returns list of posted comment URLs."""
    comments: list[str] = []

    warnings = result.get("warnings") or []
    if warnings:
        lines = "\n".join(
            f"- `{w.get('code', '?')}`: {w.get('message', '')}" for w in warnings
        )
        url = post_pr_comment(pr_number, f"⚠️ **Warnings for {cr_id}:**\n\n{lines}", token=token)
        if url:
            comments.append(url)

    errors = result.get("errors") or []
    if result.get("outcome") == "completed_with_errors" and errors:
        lines = "\n".join(
            f"- **{e.get('field', '?')}**: {e.get('issue', '')}\n  _Fix:_ {e.get('fix', '')}"
            for e in errors
        )
        url = post_pr_comment(
            pr_number,
            f"⚠️ **Validation errors for {cr_id}:**\n\n{lines}",
            token=token,
        )
        if url:
            comments.append(url)

    return comments


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
    design_llm = _resolve_stage_llm("design")
    review_llm = _resolve_stage_llm("design_review")
    diagnostics: dict = {
        "design_model": _model_label(design_llm),
        "design_review_model": _model_label(review_llm),
        "github_feedback": {"attempted": False},
        "fix_attempted": False,
        "initial_error_count": 0,
        "final_error_count": 0,
        "design_review_verdict": None,
        "design_review_cycles": 0,
        "session_id": None,
        "resumed_session_id": None,
    }
    inputs = {
        "dhf_path": str(dhf_path),
        "repo_root": str(repo_root),
        "pr_number": pr_number,
        "revision_mode": pr_number is not None,
        "since_ref": "origin/main",
    }

    prior_session = get_session(pr_number) if pr_number else ""
    if prior_session:
        diagnostics["resumed_session_id"] = prior_session

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
            f"Continue using the CLI (`dhfkit item create` / `dhfkit item update`) only. "
            f"After making changes, re-run:\n"
            f"  python -m dhfkit --dhf DHF validate schema\n"
            f"  python -m dhfkit --dhf DHF validate traceability\n\n"
            f"Review feedback:\n{feedback['prompt_text']}"
        )
        block = _build_dhf_context_block(dhf_path)
        if block:
            prompt += "\n\n" + block
        prompt = _append_skills(prompt)
        steps.append(_finish_step(prompt_step, prompt_perf, "ok"))
    else:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "generate_dhf_generation", "used_pr_feedback": False},
        )
        prompt = _assemble_generate_dhf_prompt(cr_id, dhf_path)
        steps.append(_finish_step(prompt_step, prompt_perf, "ok"))

    rc, _, session_id = _run_claude_step(
        name="run_initial_generation",
        prompt=prompt,
        steps=steps,
        warnings=warnings,
        critical=True,
        resume_session=prior_session,
        llm_config=design_llm,
    )
    critical_step_failed = critical_step_failed or rc != 0
    if session_id:
        diagnostics["session_id"] = session_id

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
            f"Fix only the items needed to clear these errors via the dhfkit "
            f"CLI (`dhfkit item create` / `dhfkit item update`). Do not introduce other "
            f"changes. After fixing, re-run:\n"
            f"  python -m dhfkit --dhf DHF validate schema\n"
            f"  python -m dhfkit --dhf DHF validate traceability"
        )
        rc, _, fix_session_id = _run_claude_step(
            name="run_fix_generation",
            prompt=fix_prompt,
            steps=steps,
            warnings=warnings,
            critical=True,
            resume_session=session_id,
            llm_config=design_llm,
        )
        critical_step_failed = critical_step_failed or rc != 0
        if fix_session_id:
            session_id = fix_session_id
            diagnostics["session_id"] = session_id
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

    design_review_log: list[dict] = []
    design_review_verdict = "unknown"
    for review_cycle in range(1, _MAX_DESIGN_REVIEW_CYCLES + 1):
        review_step_name = "run_design_review" if review_cycle == 1 else f"run_design_review_{review_cycle}"
        review_prompt = _augment_review_prompt(_assemble_review_design_prompt(cr_id), errors)
        _, _, review_session_id = _run_claude_step(
            name=review_step_name,
            prompt=review_prompt,
            steps=steps,
            warnings=warnings,
            critical=False,
            resume_session=session_id,
            llm_config=review_llm,
        )
        if review_session_id:
            session_id = review_session_id
            diagnostics["session_id"] = session_id

        review_data = _read_design_review_data(repo_root, cr_id)
        design_review_verdict = review_data["verdict"]
        design_review_log.append({"cycle": review_cycle, **review_data})

        if design_review_verdict != "needs_revision" or review_cycle >= _MAX_DESIGN_REVIEW_CYCLES:
            break

        fix_review_prompt = (
            f"The design review for {cr_id} found issues. "
            f"Read the review at docs/reviews/{cr_id}-Design-Review.md for the specific issues, "
            f"then fix each item via the dhfkit CLI (dhfkit item create / dhfkit item update). "
            f"After making changes, re-run:\n"
            f"  python -m dhfkit --dhf DHF validate schema\n"
            f"  python -m dhfkit --dhf DHF validate traceability\n"
            f"Do not modify the review file itself."
        )
        _, _, fix_session_id = _run_claude_step(
            name=f"run_design_fix_{review_cycle}",
            prompt=fix_review_prompt,
            steps=steps,
            warnings=warnings,
            critical=False,
            resume_session=session_id,
            llm_config=design_llm,
        )
        if fix_session_id:
            session_id = fix_session_id
            diagnostics["session_id"] = session_id

        items_changed = git.collect_dhf_item_changes(repo_root, "origin/main")
        validate_review_fix_step, validate_review_fix_perf = _begin_step(
            f"validate_after_review_fix_{review_cycle}", {"validator": "validate_generate_dhf"}
        )
        errors = design_validation.validate_generate_dhf(cr_id, dhf_path, items_changed)
        diagnostics["final_error_count"] = len(errors)
        steps.append(
            _finish_step(
                validate_review_fix_step,
                validate_review_fix_perf,
                "failed" if errors else "ok",
                {"error_count": len(errors)},
            )
        )

    diagnostics["design_review_verdict"] = design_review_verdict
    diagnostics["design_review_cycles"] = review_cycle

    items_changed = git.collect_dhf_item_changes(repo_root, "origin/main")
    artifact_step, artifact_perf = _begin_step(
        "collect_artifacts", {"kind": "dhf_items_changed", "snapshot_only": True}
    )
    steps.append(
        _finish_step(artifact_step, artifact_perf, "ok", {"items_changed": items_changed})
    )

    design_impact: dict = {"recorded": False, "reason": "skipped_due_to_validation_errors"}
    if not errors:
        impact_step, impact_perf = _begin_step("record_design_impact")
        design_impact = _record_design_impact_in_cr(cr_id, dhf_path, items_changed)
        steps.append(
            _finish_step(
                impact_step,
                impact_perf,
                "ok" if design_impact.get("recorded") else "warning",
                design_impact,
            )
        )

    if session_id and pr_number:
        put_session(pr_number, session_id)

    result = _build_response(
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
    result["design_review"] = _build_review_result("Design", design_review_log)
    if pr_number:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        result["pr_comments"] = _auto_post_pr_feedback(pr_number, cr_id, result, token=token)
    return result


def generate_code(
    cr_id: str,
    dhf_path: Path,
    pr_number: int | None = None,
    ci_failures: dict | None = None,
) -> dict:
    """Generate or revise implementation code for a CR."""
    started_at = _now_iso()
    started_perf = time.perf_counter()

    repo_root = dhf_path.resolve().parent
    steps: list[dict] = []
    warnings: list[dict] = []
    critical_step_failed = False
    develop_llm = _resolve_stage_llm("develop")
    review_llm = _resolve_stage_llm("code_review")
    diagnostics = {
        "develop_model": _model_label(develop_llm),
        "code_review_model": _model_label(review_llm),
        "github_feedback": {"attempted": False},
        "ci_failures_injected": ci_failures is not None,
        "preflight_errors": 0,
        "fix_attempted": False,
        "initial_error_count": 0,
        "final_error_count": 0,
        "code_review_verdict": None,
        "code_review_cycles": 0,
        "session_id": None,
        "resumed_session_id": None,
    }
    inputs = {
        "dhf_path": str(dhf_path),
        "repo_root": str(repo_root),
        "pr_number": pr_number,
        "revision_mode": pr_number is not None,
        "since_ref": "origin/main",
    }

    prior_session = get_session(pr_number) if pr_number else ""
    if prior_session:
        diagnostics["resumed_session_id"] = prior_session

    # Pre-flight DHF traceability check — catch structural gaps before the LLM runs
    # so the prompt can include specific fixes rather than the LLM discovering them later.
    # Uses validate_dhf_structure (schema + traceability only) to avoid false positives
    # from reconciliation checks that require a non-empty created_ids list.
    if not pr_number and ci_failures is None:
        preflight_step, preflight_perf = _begin_step("preflight_traceability")
        try:
            preflight_errors = design_validation.validate_dhf_structure(dhf_path)
        except Exception:
            preflight_errors = []
        diagnostics["preflight_errors"] = len(preflight_errors)
        steps.append(_finish_step(
            preflight_step, preflight_perf,
            "warning" if preflight_errors else "ok",
            {"error_count": len(preflight_errors)},
        ))
        if preflight_errors:
            for e in preflight_errors:
                warnings.append({"source": "preflight_traceability", **e})

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
    elif ci_failures is not None:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "develop_ci_correction", "ci_failures_injected": True},
        )
        failure_lines = _format_ci_failures_for_prompt(ci_failures)
        prompt = (
            f"Read the implementation on this branch related to {cr_id}, "
            f"then fix the following CI failures.\n\n"
            f"## CI Failures\n\n{failure_lines}\n\n"
            f"Address each failure specifically. Do not introduce unrelated changes."
        )
        steps.append(_finish_step(prompt_step, prompt_perf, "ok"))
    else:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "develop_generation", "used_pr_feedback": False},
        )
        prompt = _assemble_develop_prompt(cr_id, dhf_path=dhf_path)
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

    rc, _, session_id = _run_claude_step(
        name="run_initial_generation",
        prompt=prompt,
        steps=steps,
        warnings=warnings,
        critical=True,
        resume_session=prior_session,
        llm_config=develop_llm,
    )
    critical_step_failed = critical_step_failed or rc != 0
    if session_id:
        diagnostics["session_id"] = session_id

    validate_step, validate_perf = _begin_step("validate_initial", {"validator": "code_validation"})
    errors = code_validation.validate_code(cr_id, dhf_path)
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
        rc, _, fix_session_id = _run_claude_step(
            name="run_fix_generation",
            prompt=fix_prompt,
            steps=steps,
            warnings=warnings,
            critical=True,
            resume_session=session_id,
            llm_config=develop_llm,
        )
        critical_step_failed = critical_step_failed or rc != 0
        if fix_session_id:
            session_id = fix_session_id
            diagnostics["session_id"] = session_id
        validate_fix_step, validate_fix_perf = _begin_step("validate_after_fix", {"validator": "code_validation"})
        errors = code_validation.validate_code(cr_id, dhf_path)
        diagnostics["final_error_count"] = len(errors)
        steps.append(
            _finish_step(
                validate_fix_step,
                validate_fix_perf,
                "failed" if errors else "ok",
                {"error_count": len(errors)},
            )
        )

    code_review_log: list[dict] = []
    code_review_verdict = "unknown"
    for review_cycle in range(1, _MAX_CODE_REVIEW_CYCLES + 1):
        review_step_name = "run_review" if review_cycle == 1 else f"run_review_{review_cycle}"
        review_prompt = _augment_review_prompt(_assemble_review_code_prompt(cr_id), errors)
        _, review_output, review_session_id = _run_claude_step(
            name=review_step_name,
            prompt=review_prompt,
            steps=steps,
            warnings=warnings,
            critical=False,
            resume_session=session_id,
            llm_config=review_llm,
        )
        if review_session_id:
            session_id = review_session_id
            diagnostics["session_id"] = session_id

        review_data = _parse_review_data(review_output)
        code_review_verdict = review_data["verdict"]
        code_review_log.append({"cycle": review_cycle, **review_data})

        if code_review_verdict != "needs_revision" or review_cycle >= _MAX_CODE_REVIEW_CYCLES:
            break

        fix_review_prompt = (
            f"The code review for {cr_id} found issues. "
            f"Fix each issue flagged in the review above — modify only the affected files. "
            f"Do not make unrelated changes."
        )
        _, _, fix_session_id = _run_claude_step(
            name=f"run_code_fix_{review_cycle}",
            prompt=fix_review_prompt,
            steps=steps,
            warnings=warnings,
            critical=False,
            resume_session=session_id,
            llm_config=develop_llm,
        )
        if fix_session_id:
            session_id = fix_session_id
            diagnostics["session_id"] = session_id

        validate_review_fix_step, validate_review_fix_perf = _begin_step(
            f"validate_after_review_fix_{review_cycle}", {"validator": "code_validation"}
        )
        errors = code_validation.validate_code(cr_id, dhf_path)
        diagnostics["final_error_count"] = len(errors)
        steps.append(
            _finish_step(
                validate_review_fix_step,
                validate_review_fix_perf,
                "failed" if errors else "ok",
                {"error_count": len(errors)},
            )
        )

    diagnostics["code_review_verdict"] = code_review_verdict
    diagnostics["code_review_cycles"] = review_cycle

    if session_id and pr_number:
        put_session(pr_number, session_id)

    artifact_step, artifact_perf = _begin_step("collect_artifacts", {"kind": "files_changed"})
    files_changed = git.collect_path_changes(repo_root, "origin/main", *_DEFAULT_CODE_PATHS)
    steps.append(_finish_step(artifact_step, artifact_perf, "ok", {"files_changed": files_changed}))

    result = _build_response(
        cr_id=cr_id,
        stage="develop",
        started_at=started_at,
        started_perf=started_perf,
        inputs=inputs,
        steps=steps,
        artifacts={
            "files_changed": files_changed,
        },
        diagnostics=diagnostics,
        warnings=warnings,
        errors=errors,
        critical_step_failed=critical_step_failed,
    )
    result["code_review"] = _build_review_result("Implementation", code_review_log)
    if pr_number:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        result["pr_comments"] = _auto_post_pr_feedback(pr_number, cr_id, result, token=token)
    return result
