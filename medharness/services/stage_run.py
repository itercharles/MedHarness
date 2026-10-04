"""What every AI stage shares: steps, warnings, the model call, and the answer's shape."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path

from medharness.services import git
from medharness.services.llm import LLMConfig, _model_label, _resume_unavailable, _run_llm


_MAX_DESIGN_REVIEW_CYCLES = 3


_MAX_CODE_REVIEW_CYCLES = 3


_MAX_CHECK_FIX_CYCLES = 2


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

    # A session lives on the machine that created it, so a CI runner can never
    # resume one. The prompt reads the branch and carries its feedback inline,
    # so the session is continuity, not a precondition.
    resume_dropped = False
    if rc != 0 and resume_session and _resume_unavailable(output):
        resume_dropped = True
        rc, output, session_id = _run_llm(prompt, config=config, resume_session="")

    cli_found = "claude CLI not found" not in output if is_anthropic else True
    outcome = "ok" if rc == 0 else ("failed" if critical else "warning")
    details: dict[str, object] = {"exit_code": rc, "cli_found": cli_found}
    if session_id:
        details["session_id"] = session_id
    if resume_session:
        details["resumed_session_id"] = resume_session
    if resume_dropped:
        details["resume_unavailable"] = True
    if output.strip():
        details["output_excerpt"] = _truncate(output)
    steps.append(_finish_step(step, step_perf, outcome, details))
    if resume_dropped:
        warnings.append(
            _warning(
                "resume_session_unavailable",
                f"Session `{resume_session}` is not on this machine; "
                f"step `{name}` ran without it.",
                {"step": name, "session_id": resume_session},
            )
        )
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
        content = review_file.read_text(encoding="utf-8")
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


def _leave_uncommitted(repo_root: Path, start_head: str | None, warnings: list[dict]) -> None:
    """The caller commits a stage's work. Commits the agent made are undone, staged."""
    undone = git.uncommit_since(repo_root, start_head)
    if undone:
        warnings.append(_warning(
            "agent_commits_undone",
            f"The agent committed {len(undone)} time(s); the commits were undone and "
            f"their changes left staged for the caller to commit: {', '.join(c[:7] for c in undone)}.",
        ))


def _items_changed(repo_root: Path, unreadable: list[str],
                   since_ref: str = git.DEFAULT_SINCE_REF) -> dict[str, list[str]]:
    """The DHF items this branch changed, noting in ``unreadable`` when git could not say."""
    try:
        return git.collect_dhf_item_changes(repo_root, since_ref)
    except git.DiffUnavailable as exc:
        unreadable.append(str(exc))
        return {"created": [], "updated": [], "deleted": []}


_FROM_RUN = object()


class Run:
    """What an AI stage carries from its first step to its answer."""

    def __init__(self, cr_id: str, dhf_path: Path, pr_number: int | None, since_ref: str,
                 llms: tuple[LLMConfig, ...], diagnostics: dict) -> None:
        self.cr_id = cr_id
        self.dhf_path = dhf_path
        self.pr_number = pr_number
        self.since_ref = since_ref
        self.llms = llms
        self.diagnostics = diagnostics
        self.started_at = _now_iso()
        self.started_perf = time.perf_counter()
        self.repo_root = dhf_path.resolve().parent
        self.start_head = git.head(self.repo_root)
        self.steps: list[dict] = []
        self.warnings: list[dict] = []
        self.unreadable: list[str] = []
        self.critical_failed = False
        self.session_id: str | None = None
        self.inputs = {
            "dhf_path": str(dhf_path),
            "repo_root": str(self.repo_root),
            "pr_number": pr_number,
            "revision_mode": False,
            "since_ref": since_ref,
        }

    def resume_from(self, prior_session: str) -> None:
        """Note the session a revision continues; only the Anthropic CLI can."""
        if prior_session:
            self.diagnostics["resumed_session_id"] = prior_session
        if self.pr_number and any(llm.provider != "anthropic" for llm in self.llms):
            self.warnings.append(_warning(
                "non_anthropic_provider_no_session",
                "Revision mode is active but one or more stages use a non-anthropic provider. "
                "Session continuity is not supported outside the Anthropic Claude CLI; "
                "this run cannot resume from or persist to a previous session.",
            ))

    def call(self, name: str, prompt: str, llm: LLMConfig, *, critical: bool,
             resume: str | None = _FROM_RUN) -> tuple[int, str]:
        """One model step. A critical one that fails fails the run; the session carries on."""
        rc, output, session_id = _run_claude_step(
            name=name,
            prompt=prompt,
            steps=self.steps,
            warnings=self.warnings,
            critical=critical,
            resume_session=self.session_id if resume is _FROM_RUN else resume,
            llm_config=llm,
        )
        self.critical_failed = self.critical_failed or (critical and rc != 0)
        if session_id:
            self.session_id = session_id
            self.diagnostics["session_id"] = session_id
        return rc, output

    def items_changed(self) -> dict[str, list[str]]:
        return _items_changed(self.repo_root, self.unreadable, self.since_ref)

    def warn(self, found: list[dict]) -> None:
        for w in found:
            self.warnings.append(_warning(w["code"], w["message"], {"field": w["field"]}))

    def leave_uncommitted(self) -> None:
        _leave_uncommitted(self.repo_root, self.start_head, self.warnings)

    def respond(self, stage: str, artifacts: dict, errors: list[dict]) -> dict:
        return _build_response(
            cr_id=self.cr_id,
            stage=stage,
            started_at=self.started_at,
            started_perf=self.started_perf,
            inputs=self.inputs,
            steps=self.steps,
            artifacts=artifacts,
            diagnostics=self.diagnostics,
            warnings=self.warnings,
            errors=errors,
            critical_step_failed=self.critical_failed,
        )
