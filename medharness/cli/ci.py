"""Workflow-facing commands — Click declarations + presentation.

Calls services/ci.py and _helpers directly. No commands/ci.py intermediate layer.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import click
import medharness._helpers as _h
from medharness.services.ci import ci_structural_gate, ci_test_coverage_gate
from medharness.services.github_event import parse_github_event, plan_github_event
from medharness.services.github_session import get_session, put_session
_ITEM_ID_RE = re.compile(r"^([A-Z]+-\d+)")


def _parse_key_value_pairs(
    values: tuple[str, ...],
    *,
    option_name: str,
    separator: str = "=",
) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if separator not in value:
            raise click.UsageError(
                f"Invalid {option_name} value '{value}'. Expected KEY{separator}VALUE."
            )
        key, mapped = value.split(separator, 1)
        key = key.strip()
        mapped = mapped.strip()
        if not key or not mapped:
            raise click.UsageError(
                f"Invalid {option_name} value '{value}'. Expected KEY{separator}VALUE."
            )
        result[key] = mapped
    return result


def _parse_branch_stage_pairs(values: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    parsed = _parse_key_value_pairs(values, option_name="--branch-stage")
    return tuple(parsed.items())


def _format_summary(stage_label: str, verb: str, cr_id: str, result: dict) -> str:
    """Compose the human-readable stderr summary for CI generate-* commands.

    Surfaces client-facing outcome, fix attempts, residual error count,
    elapsed time, and changed-item / changed-file counts when present.
    """
    diagnostics = result.get("diagnostics") or {}
    artifacts = result.get("artifacts") or {}
    timing = result.get("timing") or {}
    details = [
        f"outcome: {result.get('outcome', 'unknown')}",
    ]
    if diagnostics.get("fix_attempted"):
        details.append("fix attempted")
    err_count = len(result.get("errors") or [])
    if err_count:
        details.append(f"errors: {err_count}")
    elapsed_ms = timing.get("elapsed_ms")
    if elapsed_ms is not None:
        details.append(f"{elapsed_ms} ms")

    for label, bucket in (
        ("DHF", artifacts.get("items_changed") or {}),
        ("files", artifacts.get("files_changed") or {}),
    ):
        created = len(bucket.get("created") or [])
        updated = len(bucket.get("updated") or [])
        deleted = len(bucket.get("deleted") or [])
        if created or updated or deleted:
            details.append(f"{label}: +{created} ~{updated} -{deleted}")

    prefix = "ERROR" if result.get("outcome") == "tool_error" else "OK"
    return f"{prefix} {stage_label} {verb} for {cr_id} ({', '.join(details)})."


def _raise_for_outcome_error(result: dict) -> None:
    """Exit non-zero for tool_error and completed_with_errors outcomes."""
    if result.get("outcome") in ("tool_error", "completed_with_errors"):
        raise click.exceptions.Exit(1)


def register(main):

    @main.group("verify")
    def verify() -> None:
        """Run validation and coverage checks for controlled changes."""

    @main.group("evidence")
    def evidence() -> None:
        """Build evidence and delivery artifacts."""

    @main.group("approval")
    def approval() -> None:
        """Check and interpret approval state for a change."""

    @main.group("change")
    def change() -> None:
        """Analyze, implement, and track change requests."""

    @main.group("automation")
    def automation() -> None:
        """Helpers for workflow automation and integrations."""

    @evidence.command("bundle")
    @click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path), required=True)
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path))
    @click.option("--coverage-pair", "coverage_pairs", multiple=True, metavar="PARENT:CHILD")
    @click.option("--traceability-type", "traceability_types", multiple=True, metavar="CODE")
    @click.option("--run-id", "run_id", default="")
    @click.option("--run-url", "run_url", default="")
    @click.option("--commit", "commit_sha", default="")
    @click.option("--continue-on-gate-failure", is_flag=True, default=False)
    @click.pass_context
    def evidence_bundle(ctx: click.Context, out_dir: Path,
                           junit_files: tuple[Path, ...], junit_dirs: tuple[Path, ...],
                           coverage_pairs: tuple[str, ...], traceability_types: tuple[str, ...],
                           run_id: str, run_url: str, commit_sha: str,
                           continue_on_gate_failure: bool) -> None:
        """Produce a read-only CI evidence bundle.

        Consumes JUnit files directly at bundle time (consume-at-bundle model).
        Runs the acceptance gate internally — no separate gate command needed.

        """
        from medharness.services.ci import build_evidence_bundle
        dhf: Path = ctx.obj["dhf"]
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = build_evidence_bundle(
            dhf_path=dhf, out_dir=out_dir, junit_paths=junit_paths,
            coverage_pairs=coverage_pairs, traceability_types=traceability_types,
            run_id=run_id, run_url=run_url, commit_sha=commit_sha,
            continue_on_gate_failure=continue_on_gate_failure,
        )
        manifest = result["manifest"]
        gate_passed = result["gate_passed"]
        click.echo(json.dumps(manifest, default=str))
        click.echo(f"OK Bundle written to {out_dir} (gate {'PASS' if gate_passed else 'FAIL'}).", err=True)
        if not gate_passed and not continue_on_gate_failure:
            raise click.ClickException("DHF acceptance gate failed.")

    @verify.command("dhf")
    @click.option("--dhf", "dhf_path", type=click.Path(file_okay=False, path_type=Path))
    @click.option("--run-schema/--no-run-schema", default=True, show_default=True)
    @click.option("--run-traceability/--no-run-traceability", default=True, show_default=True)
    @click.option("--coverage-pair", "coverage_pairs", multiple=True, metavar="PARENT:CHILD")
    @click.option("--fail-on-uncovered", is_flag=True, default=False)
    @click.pass_context
    def verify_dhf(ctx: click.Context, dhf_path: Path, run_schema: bool,
                        run_traceability: bool, coverage_pairs: tuple[str, ...],
                        fail_on_uncovered: bool) -> None:
        """Structural DHF validation gate for CI pipelines.

        Takes its own --dhf PATH option because it runs from the DHF repo
        where the DHF root is simply 'DHF' (not a subdirectory).

        """
        effective_dhf = dhf_path or ctx.obj.get("dhf")
        if effective_dhf is None:
            raise click.ClickException("--dhf is required when not set globally")
        result = ci_structural_gate(dhf_path=effective_dhf, run_schema=run_schema,
                                     run_traceability=run_traceability,
                                     coverage_pairs=coverage_pairs,
                                     fail_on_uncovered=fail_on_uncovered)
        click.echo(json.dumps(result, default=str))
        r = result["results"]
        dhf_arg = f"--dhf {effective_dhf}"
        if "schema" in r:
            s = r["schema"]
            if s["passed"]:
                click.echo(f"PASS [schema]: {s.get('item_count', 0)} items valid", err=True)
            else:
                click.echo("FAIL [schema]: validation errors found", err=True)
                for err in s.get("errors", []):
                    click.echo(f"  ✗ {err}", err=True)
                    m = _ITEM_ID_RE.match(str(err))
                    if m:
                        iid = m.group(1)
                        click.echo(f"    Fix: dhfkit {dhf_arg} item update {iid}"
                                   f" --data '{{\"<field>\": \"<value>\"}}'", err=True)
        if "traceability" in r:
            t = r["traceability"]
            req = t.get("required", {})
            if not req.get("passed", True):
                for f in req.get("failures", []):
                    click.echo(f"FAIL [required] {f['id']}: {f['issue']}", err=True)
                    click.echo(f"    Fix: add 'dhf_links: [<parent-id>]' to"
                               f" {f['id']}.yaml, or:", err=True)
                    click.echo(f"         dhfkit {dhf_arg} item update {f['id']}"
                               f" --data '{{\"dhf_links\": [\"<parent-id>\"]}}'", err=True)
            for c in t.get("coverage", []):
                click.echo(f"{'PASS' if c['passed'] else 'FAIL'} [coverage] "
                           f"{c['parent_type']}→{c['child_type']}: "
                           f"{c['covered']}/{c['total']} covered", err=True)
                if not c["passed"]:
                    click.echo(f"    Fix: dhfkit {dhf_arg} item list"
                               f" --type {c['child_type']} to find uncovered items,"
                               f" then add dhf_links to their YAML.", err=True)
            if t.get("summary"):
                click.echo(t["summary"], err=True)
        if "coverage" in r:
            for row in r["coverage"].get("pairs", []):
                click.echo(f"{'PASS' if row.get('passed') else 'FAIL'} [gate] "
                           f"{row['parent_type']}→{row['child_type']}: "
                           f"{row['covered']}/{row['total']} covered", err=True)
        if not result["passed"]:
            raise click.ClickException("DHF validation failed.")

    @verify.command("tests")
    @click.option("--dhf", "dhf_path", type=click.Path(file_okay=False, path_type=Path))
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path))
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--requirement-type", "req_types", multiple=True, metavar="CODE")
    @click.pass_context
    def verify_tests(ctx: click.Context, dhf_path: Path,
                         junit_dirs: tuple[Path, ...], junit_files: tuple[Path, ...],
                         req_types: tuple[str, ...]) -> None:
        """Check requirement coverage from JUnit evidence.

        Takes its own --dhf PATH option because it runs from the PRODUCT repo
        where the DHF is a subdirectory (e.g. dhf/DHF or medharness-dhf/DHF).

        """
        effective_dhf = dhf_path or ctx.obj.get("dhf")
        if effective_dhf is None:
            raise click.ClickException("--dhf is required when not set globally")
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = ci_test_coverage_gate(dhf_path=effective_dhf, junit_paths=junit_paths, req_types=req_types)
        if result.get("error"):
            raise click.ClickException(result["error"])
        click.echo(json.dumps(result))
        dhf_arg = f"--dhf {effective_dhf}"
        for row in result["results"]:
            if "warning" in row:
                click.echo(f"WARN: {row['warning']} '{row['type']}' — skipped.", err=True)
            elif row["passed"]:
                click.echo(f"PASS [test-coverage] {row['type']}: {row['covered']}/{row['total']} covered", err=True)
            else:
                click.echo(f"FAIL [test-coverage] {row['type']}: {row['covered']}/{row['total']} covered", err=True)
                for uid in row.get("uncovered", []):
                    click.echo(f"      ↳ uncovered: {uid}", err=True)
                    click.echo(f"        Fix: add 'dhf_links: [{uid}]' to a test case, or:", err=True)
                    click.echo(f"             dhfkit {dhf_arg} item create --type TC"
                               f" --data '{{\"title\": \"Test {uid}\", \"dhf_links\": [\"{uid}\"]}}'", err=True)
        for row in result.get("testing_points", []):
            if row["passed"]:
                click.echo(
                    f"PASS [test-coverage] {row['req_id']} test points: {row['covered']}/{row['total']} covered",
                    err=True,
                )
            else:
                click.echo(
                    f"FAIL [test-coverage] {row['req_id']} test points: {row['covered']}/{row['total']} covered",
                    err=True,
                )
                for pt in row.get("uncovered", []):
                    click.echo(f"      ↳ uncovered test point: {pt}", err=True)
        if not result["passed"]:
            raise click.ClickException("Test coverage gaps found.")

    @verify.command("verification")
    @click.option("--dhf", "dhf_path", type=click.Path(file_okay=False, path_type=Path))
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path))
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--requirement-type", "req_types", multiple=True, metavar="CODE")
    @click.pass_context
    def verify_verification(
        ctx: click.Context,
        dhf_path: Path,
        junit_dirs: tuple[Path, ...],
        junit_files: tuple[Path, ...],
        req_types: tuple[str, ...],
    ) -> None:
        """Check that every requirement has a declared verification method with evidence.

        Three gap categories are reported:
          missing_method      — no verification_method declared (gate failure)
          unverified_test     — Test method declared but no passing TC in JUnit (gate failure)
          manual_review_required — non-Test method only; requires human sign-off (warning)

        Exits non-zero when missing_method or unverified_test gaps exist.
        """
        from medharness.services.ci import validate_verification_completeness

        effective_dhf = dhf_path or ctx.obj.get("dhf")
        if effective_dhf is None:
            raise click.ClickException("--dhf is required when not set globally")
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = validate_verification_completeness(
            dhf_path=effective_dhf,
            junit_paths=junit_paths,
            req_types=req_types,
        )
        click.echo(json.dumps(result))

        for item in result.get("missing_method", []):
            click.echo(f"FAIL [validate-verification] {item['id']}: no verification_method declared", err=True)
        for item in result.get("unverified_test", []):
            click.echo(f"FAIL [validate-verification] {item['id']}: Test method declared but no passing TC linked", err=True)
        for item in result.get("manual_review_required", []):
            methods = ", ".join(item.get("methods", []))
            click.echo(f"WARN [validate-verification] {item['id']}: {methods} — requires manual sign-off record", err=True)

        click.echo(result["summary"], err=True)
        if not result["passed"]:
            raise click.ClickException("Verification completeness gaps found.")

    @verify.command("completion")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--dhf", "dhf_path", type=click.Path(file_okay=False, path_type=Path))
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path))
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.pass_context
    def verify_completion(
        ctx: click.Context,
        cr_id: str,
        dhf_path: Path | None,
        junit_dirs: tuple[Path, ...],
        junit_files: tuple[Path, ...],
    ) -> None:
        """Verify CR closure: all proposed items created and verification evidence present.

        Reads proposed_new_items from the CR item, checks each proposed type was
        created in the DHF, then runs the verification completeness gate for those
        types. Use after a CR branch is merged and CI evidence is available.

        Exits non-zero when any proposed items are missing or unverified.
        """
        from medharness.services.ci import cr_closure_gate

        effective_dhf = dhf_path or ctx.obj.get("dhf")
        if effective_dhf is None:
            raise click.ClickException("--dhf is required when not set globally")
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = cr_closure_gate(cr_id=cr_id, dhf_path=effective_dhf, junit_paths=junit_paths)
        click.echo(json.dumps(result))

        for item in result.get("missing_items", []):
            click.echo(
                f"FAIL [cr-complete] {item['type']}: {item.get('issue', 'proposed item not found')}",
                err=True,
            )
        for item in result.get("verification_gaps", []):
            click.echo(f"FAIL [cr-complete] {item['id']}: no verification_method declared", err=True)
        for item in result.get("unverified_test", []):
            click.echo(f"FAIL [cr-complete] {item['id']}: Test method declared but no passing TC linked", err=True)
        for item in result.get("manual_review_required", []):
            methods = ", ".join(item.get("methods", []))
            click.echo(f"WARN [cr-complete] {item['id']}: {methods} — requires manual sign-off record", err=True)

        click.echo(result["summary"], err=True)
        if not result["passed"]:
            raise click.ClickException(f"CR {cr_id} closure verification failed.")

    @verify.command("code")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--since-ref", default="origin/main", metavar="REF")
    @click.pass_context
    def verify_code(ctx: click.Context, cr_id: str, since_ref: str) -> None:
        """Run deterministic implementation validation without invoking the AI loop."""
        from medharness.services.code_validation import validate_code  # noqa: PLC0415

        dhf_path: Path = ctx.obj["dhf"]
        errors = validate_code(cr_id, dhf_path, since_ref=since_ref)
        payload = {
            "cr_id": cr_id,
            "stage": "develop",
            "passed": not errors,
            "since_ref": since_ref,
            "errors": errors,
        }
        click.echo(json.dumps(payload))
        if not errors:
            click.echo(f"PASS [validate-code] {cr_id}: deterministic checks passed.", err=True)
            return
        for error in errors:
            click.echo(f"FAIL [validate-code] {cr_id} ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        raise click.exceptions.Exit(1)

    @verify.command("branch")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--since-ref", default="origin/main", metavar="REF")
    @click.option("--code-path", "code_paths", multiple=True, metavar="PATH",
                  help="Opt into code-change enforcement: path(s) under which at least one file must be modified. "
                       "Omitting this option skips the code-change check entirely.")
    @click.pass_context
    def verify_branch(
        ctx: click.Context,
        cr_id: str,
        since_ref: str,
        code_paths: tuple[str, ...],
    ) -> None:
        """Validate that a single branch carries the expected coupled CR changes."""
        from medharness.services.git import validate_atomic_branch  # noqa: PLC0415

        dhf_path: Path = ctx.obj["dhf"]
        repo_root = dhf_path.resolve().parent
        payload = validate_atomic_branch(
            repo_root,
            dhf_path,
            cr_id,
            since_ref=since_ref,
            code_paths=code_paths,
        )
        click.echo(json.dumps(payload))
        risk_impact = payload.get("risk_impact", [])
        if risk_impact:
            ids = ", ".join(r["risk_id"] for r in risk_impact)
            click.echo(
                f"WARN [validate-branch] {cr_id}: {len(risk_impact)} risk item(s) potentially affected"
                f" — {ids}. Verify risk controls are current.",
                err=True,
            )
        if payload["passed"]:
            if code_paths:
                click.echo(f"PASS [validate-branch] {cr_id}: branch carries coupled DHF and code changes.", err=True)
            else:
                click.echo(
                    f"PASS [validate-branch] {cr_id}: branch carries DHF changes "
                    f"(pass --code-path to also enforce code changes).",
                    err=True,
                )
            return
        for error in payload["errors"]:
            click.echo(f"FAIL [validate-branch] {cr_id} ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        raise click.exceptions.Exit(1)

    # ── GitHub event context ──

    @automation.command("github-event")
    @click.option("--event", "event_path", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--manual-cr", default="", metavar="CR_ID")
    @click.option("--manual-stage", default="", metavar="STAGE")
    @click.option("--branch-stage", "branch_stage_values", multiple=True, metavar="PREFIX=STAGE",
                  help="Infer stage from branch prefix; may be passed multiple times.")
    @click.option("--stage-label-prefix", default="", metavar="PREFIX",
                  help="Infer stage from PR labels matching <prefix><stage>.")
    @click.option("--dispatch-action", "dispatch_action_values", multiple=True, metavar="STAGE=ACTION",
                  help="Map workflow_dispatch stage inputs to caller-defined actions.")
    @click.option("--review-action", "review_action_values", multiple=True, metavar="STATE[:STAGE]=ACTION",
                  help="Map review state or state+stage pairs to caller-defined actions.")
    @click.option("--pr-action", "pr_action_values", multiple=True, metavar="STATE[:STAGE]=ACTION",
                  help="Map pull_request states (merged/closed) and optional stages to caller-defined actions.")
    @click.option("--default-action", default="", metavar="ACTION",
                  help="Fallback action when no explicit mapping matches.")
    @click.option("--github-output", "github_output_path", default=None, type=click.Path(dir_okay=False, path_type=Path))
    @click.pass_context
    def automation_github_event(ctx: click.Context, event_path: Path | None, manual_cr: str,
                        manual_stage: str,
                        branch_stage_values: tuple[str, ...],
                        stage_label_prefix: str,
                        dispatch_action_values: tuple[str, ...],
                        review_action_values: tuple[str, ...],
                        pr_action_values: tuple[str, ...],
                        default_action: str,
                        github_output_path: Path | None) -> None:
        """Parse GitHub event payload and output CR context for CI workflow steps.

        The base parser returns CR context. Optional stage/action mappings let a
        client repo keep lifecycle policy in Python while still choosing its
        own branch conventions, label scheme, and action names.
        """
        result = parse_github_event(event_path, manual_cr_id=manual_cr)
        branch_stage_pairs = _parse_branch_stage_pairs(branch_stage_values)
        dispatch_actions = _parse_key_value_pairs(dispatch_action_values, option_name="--dispatch-action")
        review_actions = _parse_key_value_pairs(review_action_values, option_name="--review-action")
        pr_actions = _parse_key_value_pairs(pr_action_values, option_name="--pr-action")
        plan = plan_github_event(
            result,
            branch_stage_pairs=branch_stage_pairs,
            stage_label_prefix=stage_label_prefix,
            dispatch_actions=dispatch_actions,
            review_actions=review_actions,
            pr_actions=pr_actions,
            default_action=default_action,
            manual_stage=manual_stage,
        )
        payload = {
            "cr_id": result.cr_id,
            "mode": result.mode,
            "pr_number": result.pr_number,
            "reason": result.reason,
            "event_name": result.event_name,
            "branch_ref": result.branch_ref,
            "review_state": result.review_state,
            "merged": result.merged,
            "labels": list(result.labels),
            "dispatch_stage": result.dispatch_stage,
            "stage": plan.stage,
            "action": plan.action,
        }
        click.echo(json.dumps(payload, default=str))

        if github_output_path:
            with open(github_output_path, "a", encoding="utf-8") as f:
                for key in ("cr_id", "mode", "pr_number", "stage", "action", "event_name", "branch_ref"):
                    val = payload.get(key)
                    if val is not None and val != "":
                        f.write(f"{key}={val}\n")

    # ── Claude session ──

    @automation.group("session")
    def automation_session() -> None:
        """Store and retrieve Claude Code session IDs via PR comments."""

    @automation_session.command("put")
    @click.argument("pr_number", type=int)
    @click.argument("session_id")
    @click.option("--token", default="", metavar="TOKEN")
    def automation_session_put(pr_number: int, session_id: str, token: str) -> None:
        """Store a Claude session ID as a PR comment marker."""
        url = put_session(pr_number, session_id, token=token)
        click.echo(url)

    @automation_session.command("get")
    @click.argument("pr_number", type=int)
    @click.option("--token", default="", metavar="TOKEN")
    def automation_session_get(pr_number: int, token: str) -> None:
        """Retrieve the last stored Claude session ID from PR comments."""
        session_id = get_session(pr_number, token=token)
        click.echo(session_id)

    # ── Approval gate ──

    @approval.command("check")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--stage", required=True, type=click.Choice(["design", "develop"]))
    @click.option("--pr", "pr_number", required=True, type=int, metavar="N")
    @click.option("--token", default="", metavar="TOKEN")
    def approval_check(cr_id: str, stage: str, pr_number: int, token: str) -> None:
        """Check whether a CR stage has been explicitly approved via PR label.

        Exits 0 if the stage label is present on the PR, non-zero otherwise.
        """
        from medharness.services.pr_approval import check_approved, label_for_stage  # noqa: PLC0415
        approved = check_approved(pr_number, stage, token=token)
        label = label_for_stage(stage)
        payload = {
            "cr_id": cr_id,
            "stage": stage,
            "pr_number": pr_number,
            "approved": approved,
            "label": label,
        }
        click.echo(json.dumps(payload))
        if approved:
            click.echo(f"PASS [{stage}-approve] {cr_id}: label '{label}' found on PR #{pr_number}.", err=True)
        else:
            click.echo(f"FAIL [{stage}-approve] {cr_id}: label '{label}' missing on PR #{pr_number}.", err=True)
            raise click.exceptions.Exit(1)

    @change.command("status")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N")
    @click.option("--stage", default="", type=click.Choice(["", "design", "develop"]))
    @click.option("--branch", "branch_ref", default="", metavar="REF")
    @click.option("--token", default="", metavar="TOKEN")
    def change_status(cr_id: str, pr_number: int | None, stage: str, branch_ref: str, token: str) -> None:
        """Report machine-readable CR stage and approval status.

        The stage may be supplied directly or inferred from a branch ref using
        the built-in stage prefixes. Approval is only checked when both a PR
        number and a known stage are available.
        """
        from medharness.services.pr_approval import (  # noqa: PLC0415
            check_approved,
            label_for_stage,
            stage_for_branch,
        )

        resolved_stage = stage or (stage_for_branch(branch_ref) or "")
        label = label_for_stage(resolved_stage) if resolved_stage else None
        approved: bool | None = None
        approval_state = "not_applicable"
        if pr_number is not None and resolved_stage and label:
            approved = check_approved(pr_number, resolved_stage, token=token)
            approval_state = "approved" if approved else "pending"

        payload = {
            "cr_id": cr_id,
            "pr_number": pr_number,
            "branch_ref": branch_ref,
            "stage": resolved_stage,
            "approval_label": label,
            "approval_state": approval_state,
            "approved": approved,
        }
        click.echo(json.dumps(payload))

        details = [f"approval: {approval_state}"]
        if resolved_stage:
            details.append(f"stage={resolved_stage}")
        if label:
            details.append(f"label={label}")
        if pr_number is not None:
            details.append(f"pr=#{pr_number}")
        click.echo(f"OK CR status for {cr_id} ({', '.join(details)}).", err=True)

    @approval.command("parse")
    @click.option("--comment", "comment_body", required=True, metavar="TEXT")
    def approval_parse(comment_body: str) -> None:
        """Parse a PR comment body for /approve or /reject commands.

        Outputs JSON with action and reason. Useful in CI workflow steps
        that receive the comment body from the GitHub event payload.
        """
        from medharness.services.pr_approval import parse_approval_command  # noqa: PLC0415
        cmd = parse_approval_command(comment_body)
        if cmd is None:
            click.echo(json.dumps({"action": None, "reason": ""}))
        else:
            click.echo(json.dumps({"action": cmd.action, "reason": cmd.reason}))

    @approval.command("act")
    @click.option("--comment", "comment_body", required=True, metavar="TEXT")
    @click.option("--pr", "pr_number", required=True, type=int, metavar="N")
    @click.option("--stage", required=True, type=click.Choice(["spec", "design", "develop"]))
    @click.option("--token", default="", metavar="TOKEN")
    def approval_act(comment_body: str, pr_number: int, stage: str, token: str) -> None:
        """Execute an approval command from a PR comment body.

        On /approve: adds the stage label and posts a confirmation comment.
        On /reject: posts a rejection comment (with reason) and closes the PR.
        On no command: exits 0 with action=null.
        """
        from medharness.services.pr_approval import (  # noqa: PLC0415
            add_approval_label,
            close_pr,
            label_for_stage,
            parse_approval_command,
            post_comment,
        )

        cmd = parse_approval_command(comment_body)
        payload: dict = {"pr_number": pr_number, "stage": stage, "action": None, "success": True}

        if cmd is None:
            click.echo(json.dumps(payload))
            click.echo("OK [approval-act]: no command found in comment.", err=True)
            return

        payload["action"] = cmd.action

        if cmd.action == "approve":
            label = label_for_stage(stage)
            label_ok = add_approval_label(pr_number, stage, token=token)
            comment_body_text = f"Approved — label `{label}` added. Ready for next stage."
            comment_ok = post_comment(pr_number, comment_body_text, token=token)
            payload["label"] = label
            payload["label_added"] = label_ok
            payload["comment_posted"] = comment_ok
            payload["success"] = label_ok and comment_ok
            click.echo(json.dumps(payload))
            if not label_ok:
                click.echo(f"FAIL [approval-act] PR #{pr_number}: could not add label '{label}'.", err=True)
                raise click.exceptions.Exit(1)
            if not comment_ok:
                click.echo(f"FAIL [approval-act] PR #{pr_number}: label added but could not post confirmation comment.", err=True)
                raise click.exceptions.Exit(1)
            click.echo(f"PASS [approval-act] PR #{pr_number}: approved at stage={stage}.", err=True)

        elif cmd.action == "reject":
            body_lines = ["Change request rejected."]
            if cmd.reason:
                body_lines.append(f"\nReason: {cmd.reason}")
            comment_ok = post_comment(pr_number, "\n".join(body_lines), token=token)
            payload["reason"] = cmd.reason
            payload["comment_posted"] = comment_ok
            if not comment_ok:
                payload["pr_closed"] = False
                payload["success"] = False
                click.echo(json.dumps(payload))
                click.echo(f"FAIL [approval-act] PR #{pr_number}: could not post rejection comment.", err=True)
                raise click.exceptions.Exit(1)
            close_ok = close_pr(pr_number, token=token)
            payload["pr_closed"] = close_ok
            payload["success"] = comment_ok and close_ok
            click.echo(json.dumps(payload))
            if close_ok:
                click.echo(f"PASS [approval-act] PR #{pr_number}: rejected and closed.", err=True)
            else:
                click.echo(f"FAIL [approval-act] PR #{pr_number}: could not close PR.", err=True)
                raise click.exceptions.Exit(1)

    # ── Stage label management ──

    @change.command("advance")
    @click.option("--pr", "pr_number", required=True, type=int, metavar="N")
    @click.option("--from-stage", "from_stage", required=True, metavar="STAGE")
    @click.option("--to-stage", "to_stage", required=True, metavar="STAGE")
    @click.option("--issue", "issue_number", default=None, type=int, metavar="N")
    @click.option("--label-prefix", default="cr:stage/", show_default=True, metavar="PREFIX")
    @click.option("--token", default="", metavar="TOKEN")
    def change_advance(
        pr_number: int, from_stage: str, to_stage: str,
        issue_number: int | None, label_prefix: str, token: str,
    ) -> None:
        """Advance a CR stage label on a PR (and optionally an issue).

        Removes the from-stage label and adds the to-stage label. A missing
        from-stage label is silently ignored (idempotent).
        """
        from medharness.services.github_pr import add_label, remove_label  # noqa: PLC0415

        from_label = f"{label_prefix}{from_stage}"
        to_label = f"{label_prefix}{to_stage}"

        remove_label(pr_number, from_label, token=token)
        ok = add_label(pr_number, to_label, token=token)

        if issue_number is not None:
            remove_label(issue_number, from_label, token=token)
            add_label(issue_number, to_label, token=token)

        payload = {
            "pr_number": pr_number,
            "from_label": from_label,
            "to_label": to_label,
            "issue_number": issue_number,
            "ok": ok,
        }
        click.echo(json.dumps(payload))
        if not ok:
            click.echo(
                f"FAIL [{to_stage}-advance] Could not add label '{to_label}' to PR #{pr_number} — "
                f"check GH_TOKEN permissions and that the label exists.",
                err=True,
            )
            raise click.exceptions.Exit(1)
        click.echo(f"OK Advanced stage {from_stage} → {to_stage} on PR #{pr_number}.", err=True)

    # ── CR generation ──

    @change.command("plan")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="PR number — revision mode: revise DHF cascade based on review comments")
    @click.pass_context
    def change_plan(ctx: click.Context, cr_id: str, pr_number: int | None) -> None:
        """Generate the full DHF item cascade for a CR in a single Claude session.

        Drives the V-model (CRS→SYS→SYSARCH/RISK/RCM→SRS→SWDD) without a prior
        analyze-cr spec stage. Claude uses the medharness CLI to create/update DHF
        items and validates traceability inline. Python-side validation and a fix
        pass run as a safety net.

        Model is read from ANTHROPIC_MODEL env var.
        Pass --pr N to revise existing DHF items based on PR review comments.
        """
        from medharness.services.cr_generation import generate_dhf  # noqa: PLC0415
        from medharness.workflows.cr_state import assert_cr_active  # noqa: PLC0415
        dhf: Path = ctx.obj["dhf"]
        try:
            assert_cr_active(_h._make_adapter(ctx.obj["dhf"]), cr_id)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        except (FileNotFoundError, OSError):
            pass  # DHF config not loadable yet; generate_dhf will surface the error
        result = generate_dhf(cr_id, dhf, pr_number=pr_number)
        click.echo(json.dumps(result))
        click.echo(
            _format_summary("DHF cascade", "revised" if pr_number else "generated", cr_id, result),
            err=True,
        )
        for error in result.get("errors") or []:
            click.echo(f"  FAIL ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        _raise_for_outcome_error(result)

    @change.command("implement")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="PR number — revision mode: revise implementation based on review comments")
    @click.option("--ci-failures", "ci_failures_path", default=None,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="JSON file containing structured CI failure output to feed back to Claude")
    @click.pass_context
    def change_implement(ctx: click.Context, cr_id: str, pr_number: int | None,
                      ci_failures_path: Path | None) -> None:
        """Generate or revise implementation code for a CR using Claude.

        Reads the approved spec and CR item, then invokes claude -p to implement
        the required code changes following CLAUDE.md conventions.

        Model is read from ANTHROPIC_MODEL env var.
        Pass --pr N to revise existing implementation based on PR review comments.
        Pass --ci-failures PATH to feed structured CI failure JSON back as a
        targeted correction prompt instead of free-text PR review comments.
        """
        from medharness.services.cr_generation import generate_code  # noqa: PLC0415
        from medharness.workflows.cr_state import assert_cr_active  # noqa: PLC0415
        dhf: Path = ctx.obj["dhf"]
        try:
            assert_cr_active(_h._make_adapter(ctx.obj["dhf"]), cr_id)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        except (FileNotFoundError, OSError):
            pass  # DHF config not loadable yet; generate_code will surface the error
        ci_failures: dict | None = None
        if ci_failures_path is not None:
            try:
                ci_failures = json.loads(ci_failures_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise click.ClickException(f"Could not read --ci-failures file: {exc}") from exc
        result = generate_code(cr_id, dhf, pr_number=pr_number, ci_failures=ci_failures)
        click.echo(json.dumps(result))
        click.echo(_format_summary("Implementation", "revised" if pr_number else "generated", cr_id, result), err=True)
        for error in result.get("errors") or []:
            click.echo(f"  FAIL ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        _raise_for_outcome_error(result)
