"""CR lifecycle AI generation orchestration."""

from __future__ import annotations

import os
from pathlib import Path

from medharness.services import checks as check_runner
from medharness.services import design_validation, git
from medharness.services.cr_impact import _record_design_impact_in_cr
from medharness.services.github_session import get_session, put_session
from medharness.services.llm import _model_label, _resolve_stage_llm
from medharness.services.pr_feedback import _auto_post_pr_feedback, _pr_base, _pr_feedback, _push_to_pr
from medharness.services.prompt_assembly import (
    MAX_DIFF_CHARS,
    _assemble_develop_prompt,
    _assemble_generate_dhf_prompt,
    _assemble_review_code_prompt,
    _assemble_review_design_prompt,
    _enrich_with_plan_context,
    checks_section,
)
from medharness.services.stage_run import (
    Run,
    _MAX_CHECK_FIX_CYCLES,
    _MAX_CODE_REVIEW_CYCLES,
    _MAX_DESIGN_REVIEW_CYCLES,
    _augment_review_prompt,
    _begin_step,
    _build_review_result,
    _finish_step,
    _format_error_lines,
    _parse_review_data,
    _read_design_review_data,
    _warning,
)

__all__ = [
    "generate_code",
    "generate_dhf",
]


def _code_paths(dhf_path: Path, repo_root: Path) -> tuple[str, ...]:
    """Where `build code` looks for the code it wrote, for the diff it shows the model
    and for `files_changed`.

    MEDHARNESS_CODE_PATHS (comma-separated, e.g. "src/,lib/") narrows it; otherwise it
    is the whole repository except the DHF, which `items_changed` reports. A default
    of particular directories reported no changes, silently, for any project that
    did not lay its code out that way.
    """
    configured = tuple(p.strip() for p in os.environ.get("MEDHARNESS_CODE_PATHS", "").split(",") if p.strip())
    if configured:
        return configured
    dhf = os.path.relpath(dhf_path.resolve(), repo_root.resolve())
    return (".", f":(exclude){dhf}", ":(exclude)docs/reviews")


def _validate_design(run: Run, name: str, items_changed: dict) -> list[dict]:
    step, perf = _begin_step(name, {"validator": "validate_generate_dhf"})
    errors = design_validation.validate_generate_dhf(run.cr_id, run.dhf_path, items_changed)
    run.diagnostics["final_error_count"] = len(errors)
    run.steps.append(_finish_step(step, perf, "failed" if errors else "ok", {"error_count": len(errors)}))
    return errors


def generate_dhf(cr_id: str, dhf_path: Path, pr_number: int | None = None,
                 since_ref: str | None = None) -> dict:
    """Generate the complete DHF item cascade for a CR in a single LLM session.

    The model works out what the change touches and writes the items with
    `medharness item`. Deterministic validation follows; if errors remain, one fix
    pass is attempted, and a design review after it.
    """
    design_llm = _resolve_stage_llm("design")
    review_llm = _resolve_stage_llm("design_review")
    since_ref = git.resolve_since_ref(dhf_path.resolve().parent, since_ref or (pr_number and _pr_base(pr_number)))
    run = Run(cr_id, dhf_path, pr_number, since_ref, (design_llm, review_llm), {
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
    })
    prior_session = get_session(pr_number) if pr_number else ""
    run.resume_from(prior_session)

    feedback = _pr_feedback(pr_number, run.steps, run.diagnostics, run.warnings) if pr_number else None
    run.inputs["revision_mode"] = feedback is not None
    if feedback is not None:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "generate_dhf_revision", "used_pr_feedback": True},
        )
        prompt = (
            f"Read the DHF items in DHF/ related to {cr_id}, "
            f"then revise them based on the following pull request review feedback. "
            f"Continue using the CLI (`medharness item create` / `medharness item update`) only. "
            f"Keep the CR's `impact_analysis`, `reviewed_items` and `affected_*` fields consistent with what you change. "
            f"After making changes, re-run:\n"
            f"  medharness --dhf DHF verify dhf\n\n"
            f"Review feedback:\n{feedback['prompt_text']}"
        )
        prompt = _enrich_with_plan_context(prompt, cr_id, dhf_path, run.warnings)
    else:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "generate_dhf_generation", "used_pr_feedback": False},
        )
        prompt = _assemble_generate_dhf_prompt(cr_id, dhf_path, run.warnings)
    run.steps.append(_finish_step(prompt_step, prompt_perf, "ok"))

    run.call("run_initial_generation", prompt, design_llm, critical=True, resume=prior_session)

    items_changed = run.items_changed()
    errors = _validate_design(run, "validate_initial", items_changed)
    run.diagnostics["initial_error_count"] = len(errors)

    if errors:
        run.diagnostics["fix_attempted"] = True
        run.call(
            "run_fix_generation",
            f"The DHF cascade for {cr_id} failed deterministic validation:\n"
            f"{_format_error_lines(errors)}\n\n"
            f"Fix only the items needed to clear these errors via the medharness "
            f"CLI (`medharness item create` / `medharness item update`). Do not introduce other "
            f"changes. After fixing, re-run:\n"
            f"  medharness --dhf DHF verify dhf",
            design_llm, critical=True,
        )
        items_changed = run.items_changed()
        errors = _validate_design(run, "validate_after_fix", items_changed)

    run.warn(design_validation.check_verification_quality(dhf_path, items_changed))
    run.warn(design_validation.check_near_duplicates(dhf_path, items_changed))
    run.warn(design_validation.check_large_edits(run.repo_root, since_ref))
    run.warn(design_validation.check_test_points_follow_requirements(run.repo_root, dhf_path, since_ref))

    design_review_log: list[dict] = []
    design_review_verdict = "unknown"
    for review_cycle in range(1, _MAX_DESIGN_REVIEW_CYCLES + 1):
        run.call(
            "run_design_review" if review_cycle == 1 else f"run_design_review_{review_cycle}",
            _augment_review_prompt(
                _assemble_review_design_prompt(cr_id, dhf_path, items_changed, run.warnings, since_ref), errors),
            review_llm, critical=False,
        )

        review_data = _read_design_review_data(run.repo_root, cr_id)
        design_review_verdict = review_data["verdict"]
        design_review_log.append({"cycle": review_cycle, **review_data})

        if design_review_verdict != "needs_revision" or review_cycle >= _MAX_DESIGN_REVIEW_CYCLES:
            break

        run.call(
            f"run_design_fix_{review_cycle}",
            f"The design review for {cr_id} found issues. "
            f"Read the review at docs/reviews/{cr_id}-Design-Review.md for the specific issues, "
            f"then fix each item via `medharness item create` / `medharness item update`. "
            f"Keep the CR's `impact_analysis`, `reviewed_items` and `affected_*` fields consistent with what you change. "
            f"After making changes, re-run:\n"
            f"  medharness --dhf DHF verify dhf\n"
            f"Do not modify the review file itself.",
            design_llm, critical=False,
        )
        items_changed = run.items_changed()
        errors = _validate_design(run, f"validate_after_review_fix_{review_cycle}", items_changed)

    run.diagnostics["design_review_verdict"] = design_review_verdict
    run.diagnostics["design_review_cycles"] = review_cycle
    run.leave_uncommitted()

    items_changed = run.items_changed()
    if run.unreadable:
        # Added after the fix loop on purpose: an LLM fix pass cannot fetch a ref.
        # It must be in `errors` before design impact, which would otherwise write
        # an empty affected_items onto the CR.
        errors.append({
            "field": "changed_items",
            "issue": (
                f"Could not diff against {since_ref} ({run.unreadable[-1]}), so the "
                f"items this run changed were not checked."
            ),
            "fix": (
                f"Fetch {since_ref} with full history and re-run. A shallow clone or a repo "
                f"with no remote cannot diff."
            ),
        })
        items_changed = None
    artifact_step, artifact_perf = _begin_step(
        "collect_artifacts", {"kind": "dhf_items_changed", "snapshot_only": True}
    )
    run.steps.append(_finish_step(artifact_step, artifact_perf, "ok", {"items_changed": items_changed}))

    design_impact: dict = {"recorded": False, "reason": "skipped_due_to_validation_errors"}
    if not errors:
        impact_step, impact_perf = _begin_step("record_design_impact")
        design_impact = _record_design_impact_in_cr(cr_id, dhf_path, items_changed)
        run.steps.append(_finish_step(
            impact_step, impact_perf, "ok" if design_impact.get("recorded") else "warning", design_impact,
        ))

    if run.session_id and pr_number:
        put_session(pr_number, run.session_id)
    if pr_number:
        _push_to_pr(run.repo_root, pr_number, f"design({cr_id}): build plan", errors)

    result = run.respond(
        "generate_dhf", {"items_changed": items_changed, "design_impact": design_impact}, errors,
    )
    result["design_review"] = _build_review_result("Design", design_review_log)
    if pr_number:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        result["pr_comments"] = _auto_post_pr_feedback(pr_number, cr_id, result, token=token)
    return result


def _run_checks(run: Run, checks: tuple[str, ...], develop_llm) -> list[dict]:
    """Run the `--check` commands, sending a failure back to the model for a fix."""
    results: list[dict] = []
    for attempt in range(_MAX_CHECK_FIX_CYCLES + 1):
        step, perf = _begin_step("run_checks", {"attempt": attempt + 1})
        results = check_runner.run_checks(run.repo_root, checks)
        failed = [c for c in results if not c["passed"]]
        run.steps.append(_finish_step(step, perf, "failed" if failed else "ok",
                                      {"failed": [c["command"] for c in failed]}))
        if not failed or attempt == _MAX_CHECK_FIX_CYCLES:
            break
        report = "\n\n".join(f"`{c['command']}` exited {c['exit_code']}:\n{c['output']}" for c in failed)
        run.call(
            f"run_check_fix_{attempt + 1}",
            f"The checks for {run.cr_id} failed when the harness ran them. Fix the code so each exits 0; "
            f"do not change the checks.\n\n{report}",
            develop_llm, critical=False,
        )
    return results


def generate_code(
    cr_id: str,
    dhf_path: Path,
    pr_number: int | None = None,
    checks: tuple[str, ...] = (),
    since_ref: str | None = None,
) -> dict:
    """Generate or revise implementation code for a CR."""
    develop_llm = _resolve_stage_llm("develop")
    review_llm = _resolve_stage_llm("code_review")
    since_ref = git.resolve_since_ref(dhf_path.resolve().parent, since_ref or (pr_number and _pr_base(pr_number)))
    run = Run(cr_id, dhf_path, pr_number, since_ref, (develop_llm, review_llm), {
        "develop_model": _model_label(develop_llm),
        "code_review_model": _model_label(review_llm),
        "github_feedback": {"attempted": False},
        "preflight_errors": 0,
        "fix_attempted": False,
        "initial_error_count": 0,
        "final_error_count": 0,
        "code_review_verdict": None,
        "code_review_cycles": 0,
        "session_id": None,
        "resumed_session_id": None,
    })
    prior_session = get_session(pr_number) if pr_number else ""
    run.resume_from(prior_session)

    # Pre-flight DHF traceability check — catch structural gaps before the LLM runs
    # so the prompt can include specific fixes rather than the LLM discovering them later.
    # Uses validate_dhf_structure (schema + traceability only) to avoid false positives
    # from reconciliation checks that require a non-empty created_ids list.
    feedback = _pr_feedback(pr_number, run.steps, run.diagnostics, run.warnings) if pr_number else None
    run.inputs["revision_mode"] = feedback is not None
    if feedback is None:
        preflight_step, preflight_perf = _begin_step("preflight_traceability")
        try:
            preflight_errors = design_validation.validate_dhf_structure(dhf_path)
        except Exception:
            preflight_errors = []
        run.diagnostics["preflight_errors"] = len(preflight_errors)
        run.steps.append(_finish_step(
            preflight_step, preflight_perf,
            "warning" if preflight_errors else "ok",
            {"error_count": len(preflight_errors)},
        ))
        for e in preflight_errors:
            run.warnings.append({"source": "preflight_traceability", **e})

    if feedback is not None:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "develop_revision", "used_pr_feedback": True},
        )
        prompt = (
            f"Read the implementation on this branch related to {cr_id}, "
            f"then revise it based on the following pull request review feedback.\n\n"
            f"Review feedback:\n{feedback['prompt_text']}"
        ) + checks_section(checks)
        run.steps.append(_finish_step(prompt_step, prompt_perf, "ok"))
    else:
        prompt_step, prompt_perf = _begin_step(
            "prepare_prompt",
            {"prompt_kind": "develop_generation", "used_pr_feedback": False},
        )
        prompt = _assemble_develop_prompt(cr_id, dhf_path=dhf_path, warnings=run.warnings, checks=checks,
                                          since_ref=since_ref)
        diff = git.compute_diff(run.repo_root, since_ref, *_code_paths(dhf_path, run.repo_root))
        if diff:
            truncated = len(diff) > MAX_DIFF_CHARS
            diff_body = diff[:MAX_DIFF_CHARS]
            prompt += (
                f"\n\n## Existing Implementation (since {since_ref})\n\n"
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
        run.steps.append(_finish_step(prompt_step, prompt_perf, "ok", {"diff_injected": bool(diff)}))

    run.call("run_initial_generation", prompt, develop_llm, critical=True, resume=prior_session)

    code_review_log: list[dict] = []
    code_review_verdict = "unknown"
    for review_cycle in range(1, _MAX_CODE_REVIEW_CYCLES + 1):
        _, review_output = run.call(
            "run_review" if review_cycle == 1 else f"run_review_{review_cycle}",
            _assemble_review_code_prompt(cr_id, since_ref),
            review_llm, critical=False,
        )

        review_data = _parse_review_data(review_output)
        code_review_verdict = review_data["verdict"]
        code_review_log.append({"cycle": review_cycle, **review_data})

        if code_review_verdict != "needs_revision" or review_cycle >= _MAX_CODE_REVIEW_CYCLES:
            break

        run.call(
            f"run_code_fix_{review_cycle}",
            f"The code review for {cr_id} found issues. "
            f"Fix each issue flagged in the review above — modify only the affected files. "
            f"Do not make unrelated changes.",
            develop_llm, critical=False,
        )

    run.diagnostics["code_review_verdict"] = code_review_verdict
    run.diagnostics["code_review_cycles"] = review_cycle

    check_results = _run_checks(run, checks, develop_llm) if checks else []

    if run.session_id and pr_number:
        put_session(pr_number, run.session_id)

    run.leave_uncommitted()
    # Implementing may reconcile SWDD or SRS; the CR's record has to follow, or
    # `verify changes` finds the branch changing items it does not list.
    items_changed = run.items_changed()
    if run.unreadable:
        run.warnings.append(_warning("diff_unavailable", f"affected_items not updated: {run.unreadable[-1]}"))
    else:
        _record_design_impact_in_cr(cr_id, dhf_path, items_changed)
    errors: list[dict] = [
        {"field": "check", "issue": f"`{c['command']}` exited {c['exit_code']} after {_MAX_CHECK_FIX_CYCLES} "
                                   f"fix attempts:\n{c['output'][-1000:]}",
         "fix": "Make the check pass in the working tree, then run `build code` again; nothing was pushed."}
        for c in check_results if not c["passed"]
    ]
    if pr_number and not errors:
        _push_to_pr(run.repo_root, pr_number, f"feat({cr_id}): build code", errors)
    artifact_step, artifact_perf = _begin_step("collect_artifacts", {"kind": "files_changed"})
    try:
        files_changed = git.collect_path_changes(run.repo_root, since_ref, *_code_paths(dhf_path, run.repo_root))
    except git.DiffUnavailable as exc:
        files_changed = None
        run.warnings.append(_warning(
            "diff_unavailable",
            f"Could not diff against {since_ref} ({exc}); files_changed is unknown, not empty.",
        ))
    run.steps.append(_finish_step(artifact_step, artifact_perf, "ok", {"files_changed": files_changed}))

    result = run.respond("develop", {"files_changed": files_changed}, errors)
    result["code_review"] = _build_review_result("Implementation", code_review_log)
    if checks:
        result["checks"] = [{k: c[k] for k in ("command", "exit_code", "passed")} for c in check_results]
    if pr_number:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        result["pr_comments"] = _auto_post_pr_feedback(pr_number, cr_id, result, token=token)
    return result
