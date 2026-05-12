"""CI gate and evidence commands — Click declarations + presentation.

Calls services/ci.py and _helpers directly. No commands/ci.py intermediate layer.


--dhf convention (by-design):
  - ci dhf-validate takes --dhf DHF: called from the DHF repo (dhf/ci.yml)
  - ci test-coverage takes --dhf PATH: called from the product repo,
    DHF is a checked-out subdirectory
  - ci evidence bundle / artifacts generate / evidence import:
    use the global medharness --dhf PATH flag, also run from
    the product repo
"""

import json
import re
from pathlib import Path
import click
import medharness._helpers as _h
from medharness.services.ci import ci_structural_gate, ci_test_coverage_gate
from medharness.services.github_event import parse_github_event, plan_github_event
from medharness.services.github_session import get_session, put_session
from medharness.services.spec_validation import validate_spec

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

    Surfaces correction count, validation outcome, residual error count,
    elapsed time, and changed-item / changed-file counts when present.
    """
    details = [
        f"{result.get('corrections', 0)} correction(s)",
        f"validation: {result.get('validation', 'unknown')}",
    ]
    err_count = len(result.get("errors") or [])
    if err_count:
        details.append(f"residual errors: {err_count}")
    elapsed_ms = result.get("elapsed_ms")
    if elapsed_ms is not None:
        details.append(f"{elapsed_ms} ms")

    for label, bucket in (
        ("DHF", result.get("items_changed") or {}),
        ("files", result.get("files_changed") or {}),
    ):
        created = len(bucket.get("created") or [])
        updated = len(bucket.get("updated") or [])
        deleted = len(bucket.get("deleted") or [])
        if created or updated or deleted:
            details.append(f"{label}: +{created} ~{updated} -{deleted}")

    return f"OK {stage_label} {verb} for {cr_id} ({', '.join(details)})."


def _validation_spec_path(dhf_path: Path, cr_id: str, spec_path: Path | None) -> Path:
    if spec_path is not None:
        return spec_path
    return dhf_path.resolve().parent / "docs" / "cr-specs" / f"{cr_id}-Spec.md"


def register(main):

    @main.group("ci")
    def ci() -> None:
        """CI-facing facade commands for DHF gates, evidence, and artifacts."""

    @ci.group("evidence")
    def ci_evidence() -> None:
        """CI evidence ingestion commands."""

    @ci_evidence.command("import")
    @click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--format", "fmt", default="junit", show_default=True, type=click.Choice(["junit"]))
    @click.option("--tester", default="")
    @click.option("--run-id", default="")
    @click.option("--run-url", default="")
    @click.option("--commit", default="")
    @click.pass_context
    def ci_evidence_import(ctx: click.Context, paths: tuple[Path, ...], fmt: str,
                           tester: str, run_id: str, run_url: str, commit: str) -> None:
        """Import test evidence files into the DHF (persist-first pattern).

        Alternative to ci evidence bundle's consume-at-bundle-time model:
        use this to persist JUnit results into the DHF repo first,
        then reference them at bundle time.

        """
        adapter = _h._make_adapter(ctx)
        files = [_h._import_results_file(adapter, p, tester, run_id, run_url, commit) for p in paths]
        summary = {
            "format": fmt, "files": files,
            "imported": sum(f["imported"] for f in files),
            "skipped": sum(f["skipped"] for f in files),
            "items_updated": sorted({uid for f in files for uid in f["items_updated"]}),
            "failed_tcs": [tc for f in files for tc in f["failed_tcs"]],
        }
        click.echo(json.dumps(summary, default=str))
        click.echo(f"OK Imported {summary['imported']} result(s), skipped {summary['skipped']}, "
                   f"updated {len(summary['items_updated'])} item(s).", err=True)
        if summary["failed_tcs"]:
            click.echo(f"FAIL Failing TCs: {summary['failed_tcs']}", err=True)

    @ci_evidence.command("bundle")
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
    def ci_evidence_bundle(ctx: click.Context, out_dir: Path,
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

    @ci.group("artifacts")
    def ci_artifacts() -> None:
        """CI artifact generation commands."""

    @ci_artifacts.command("generate")
    @click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path), required=True)
    @click.option("--doc-type", "doc_types", multiple=True, metavar="CODE")
    @click.option("--traceability-type", "traceability_types", multiple=True, metavar="CODE")
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path))
    @click.option("--skip-plans", is_flag=True, default=False)
    @click.pass_context
    def ci_artifacts_generate(ctx: click.Context, out_dir: Path, doc_types: tuple,
                              traceability_types: tuple, junit_files: tuple[Path, ...],
                              junit_dirs: tuple[Path, ...], skip_plans: bool) -> None:
        """Generate CI-ready DHF artifacts: specs + traceability report.

        Outputs specification documents, plan documents, and a traceability
        report. The traceability report is written as JSON (machine-readable,
        consumed by compliance gates) and — when WeasyPrint is installed —
        also as a PDF matrix document at the same basename.

        """
        adapter = _h._make_adapter(ctx)
        core = _h._make_core(ctx)
        dhf_path = ctx.obj["dhf"]
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = _h._run_artifact_generation(adapter, core, dhf_path, out_dir,
                                              doc_types, traceability_types,
                                              junit_paths, skip_plans)
        click.echo(json.dumps(result, default=str))
        click.echo(f"OK Generated {len(result['specifications'])} specification(s), "
                   f"{len(result['plans'])} plan(s), "
                   f"traceability report at {result['traceability']['path']}.", err=True)

    @ci.command("dhf-validate")
    @click.option("--dhf", "dhf_path", type=click.Path(file_okay=False, path_type=Path), required=True)
    @click.option("--run-schema/--no-run-schema", default=True, show_default=True)
    @click.option("--run-traceability/--no-run-traceability", default=True, show_default=True)
    @click.option("--coverage-pair", "coverage_pairs", multiple=True, metavar="PARENT:CHILD")
    @click.option("--fail-on-uncovered", is_flag=True, default=False)
    @click.pass_context
    def ci_dhf_validate(ctx: click.Context, dhf_path: Path, run_schema: bool,
                        run_traceability: bool, coverage_pairs: tuple[str, ...],
                        fail_on_uncovered: bool) -> None:
        """Structural DHF validation gate for CI pipelines.

        Takes its own --dhf PATH option because it runs from the DHF repo
        where the DHF root is simply 'DHF' (not a subdirectory).

        """
        result = ci_structural_gate(dhf_path=dhf_path, run_schema=run_schema,
                                     run_traceability=run_traceability,
                                     coverage_pairs=coverage_pairs,
                                     fail_on_uncovered=fail_on_uncovered)
        r = result["results"]
        dhf_arg = f"--dhf {dhf_path}"
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
                        click.echo(f"    Fix: medharness {dhf_arg} dhf item update {iid}"
                                   f" --data '{{\"<field>\": \"<value>\"}}'", err=True)
        if "traceability" in r:
            t = r["traceability"]
            req = t.get("required", {})
            if not req.get("passed", True):
                for f in req.get("failures", []):
                    click.echo(f"FAIL [required] {f['id']}: {f['issue']}", err=True)
                    click.echo(f"    Fix: add 'dhf_links: [<parent-id>]' to"
                               f" {f['id']}.yaml, or:", err=True)
                    click.echo(f"         medharness {dhf_arg} dhf item update {f['id']}"
                               f" --data '{{\"dhf_links\": [\"<parent-id>\"]}}'", err=True)
            for c in t.get("coverage", []):
                click.echo(f"{'PASS' if c['passed'] else 'FAIL'} [coverage] "
                           f"{c['parent_type']}→{c['child_type']}: "
                           f"{c['covered']}/{c['total']} covered", err=True)
                if not c["passed"]:
                    click.echo(f"    Fix: medharness {dhf_arg} dhf item list"
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

    @ci.command("test-coverage")
    @click.option("--dhf", "dhf_path", type=click.Path(file_okay=False, path_type=Path), required=True)
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path))
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--requirement-type", "req_types", multiple=True, metavar="CODE")
    @click.pass_context
    def ci_test_coverage(ctx: click.Context, dhf_path: Path,
                         junit_dirs: tuple[Path, ...], junit_files: tuple[Path, ...],
                         req_types: tuple[str, ...]) -> None:
        """Check that every requirement has test coverage from JUnit evidence.

        Takes its own --dhf PATH option because it runs from the PRODUCT repo
        where the DHF is a subdirectory (e.g. dhf/DHF or medharness-dhf/DHF).

        """
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = ci_test_coverage_gate(dhf_path=dhf_path, junit_paths=junit_paths, req_types=req_types)
        if result.get("error"):
            raise click.ClickException(result["error"])
        dhf_arg = f"--dhf {dhf_path}"
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
                    click.echo(f"             medharness {dhf_arg} dhf item create --type TC"
                               f" --data '{{\"title\": \"Test {uid}\", \"dhf_links\": [\"{uid}\"]}}'", err=True)
        if not result["passed"]:
            raise click.ClickException("Test coverage gaps found.")

    # ── Spec validation ──

    @ci.command("validate-spec")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--spec", "spec_path", default=None, type=click.Path(path_type=Path),
                  metavar="PATH", help="Path to spec file (default: DHF/documents/specs/<cr_id>-Spec.md)")
    @click.option("--dhf", "dhf_path", default=None, type=click.Path(file_okay=False, path_type=Path),
                  metavar="PATH", help="DHF directory for item existence checks.")
    def ci_validate_spec(cr_id: str, spec_path: Path | None, dhf_path: Path | None) -> None:
        """Validate spec YAML front-matter produced by cr-analyze.

        Checks cr_id, direction_fit, affected_items (existence in DHF),
        and test_plan structure. Exits non-zero if any check fails.
        """
        if spec_path is None:
            if dhf_path:
                spec_path = dhf_path / "documents" / "specs" / f"{cr_id}-Spec.md"
            else:
                raise click.UsageError("Provide --spec <path> or --dhf <path> to locate the spec.")

        errors = validate_spec(spec_path, cr_id, dhf_path)
        if not errors:
            click.echo(f"PASS [validate-spec] {cr_id}: front-matter valid.", err=True)
            return

        for e in errors:
            click.echo(f"FAIL [validate-spec] {cr_id} ({e['field']}): {e['issue']}", err=True)
            click.echo(f"    Fix: {e['fix']}", err=True)
        raise click.ClickException(f"Spec validation failed for {cr_id} ({len(errors)} error(s)).")

    @ci.command("validate-design")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--spec", "spec_path", default=None, type=click.Path(path_type=Path),
                  metavar="PATH", help="Path to spec file (default: docs/cr-specs/<cr_id>-Spec.md)")
    @click.pass_context
    def ci_validate_design(ctx: click.Context, cr_id: str, spec_path: Path | None) -> None:
        """Run deterministic design validation without invoking the AI loop."""
        from medharness.services.design_validation import validate_design  # noqa: PLC0415

        dhf_path: Path = ctx.obj["dhf"]
        resolved_spec = _validation_spec_path(dhf_path, cr_id, spec_path)
        errors = validate_design(cr_id, dhf_path, resolved_spec)
        payload = {
            "cr_id": cr_id,
            "stage": "design",
            "passed": not errors,
            "spec_path": str(resolved_spec),
            "errors": errors,
        }
        click.echo(json.dumps(payload))
        if not errors:
            click.echo(f"PASS [validate-design] {cr_id}: deterministic checks passed.", err=True)
            return
        for error in errors:
            click.echo(f"FAIL [validate-design] {cr_id} ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        raise click.exceptions.Exit(1)

    @ci.command("validate-code")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--spec", "spec_path", default=None, type=click.Path(path_type=Path),
                  metavar="PATH", help="Path to spec file (default: docs/cr-specs/<cr_id>-Spec.md)")
    @click.option("--since-ref", default="origin/main", metavar="REF")
    @click.pass_context
    def ci_validate_code(ctx: click.Context, cr_id: str, spec_path: Path | None, since_ref: str) -> None:
        """Run deterministic implementation validation without invoking the AI loop."""
        from medharness.services.code_validation import validate_code  # noqa: PLC0415

        dhf_path: Path = ctx.obj["dhf"]
        resolved_spec = _validation_spec_path(dhf_path, cr_id, spec_path)
        errors = validate_code(cr_id, dhf_path, resolved_spec, since_ref=since_ref)
        payload = {
            "cr_id": cr_id,
            "stage": "develop",
            "passed": not errors,
            "spec_path": str(resolved_spec),
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

    @ci.command("validate-branch")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--spec", "spec_path", default=None, type=click.Path(path_type=Path),
                  metavar="PATH", help="Path to spec file (default: docs/cr-specs/<cr_id>-Spec.md)")
    @click.option("--since-ref", default="origin/main", metavar="REF")
    @click.option("--code-path", "code_paths", multiple=True, metavar="PATH",
                  help="Product-code paths that must carry implementation changes.")
    @click.pass_context
    def ci_validate_branch(
        ctx: click.Context,
        cr_id: str,
        spec_path: Path | None,
        since_ref: str,
        code_paths: tuple[str, ...],
    ) -> None:
        """Validate that a single branch carries the expected coupled CR changes."""
        from medharness.services.git import validate_atomic_branch  # noqa: PLC0415

        dhf_path: Path = ctx.obj["dhf"]
        repo_root = dhf_path.resolve().parent
        resolved_spec = _validation_spec_path(dhf_path, cr_id, spec_path)
        payload = validate_atomic_branch(
            repo_root,
            dhf_path,
            cr_id,
            since_ref=since_ref,
            code_paths=code_paths or ("apps/", "packages/"),
            spec_path=resolved_spec,
        )
        click.echo(json.dumps(payload))
        if payload["passed"]:
            click.echo(f"PASS [validate-branch] {cr_id}: branch carries coupled spec, code, and DHF changes.", err=True)
            return
        for error in payload["errors"]:
            click.echo(f"FAIL [validate-branch] {cr_id} ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        raise click.exceptions.Exit(1)

    # ── GitHub event context ──

    @ci.command("github-event")
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
    def ci_github_event(ctx: click.Context, event_path: Path | None, manual_cr: str,
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

    @ci.group("claude-session")
    def ci_claude_session() -> None:
        """Store and retrieve Claude Code session IDs via PR comments."""

    @ci_claude_session.command("put")
    @click.argument("pr_number", type=int)
    @click.argument("session_id")
    @click.option("--token", default="", metavar="TOKEN")
    def ci_claude_session_put(pr_number: int, session_id: str, token: str) -> None:
        """Store a Claude session ID as a PR comment marker."""
        url = put_session(pr_number, session_id, token=token)
        click.echo(url)

    @ci_claude_session.command("get")
    @click.argument("pr_number", type=int)
    @click.option("--token", default="", metavar="TOKEN")
    def ci_claude_session_get(pr_number: int, token: str) -> None:
        """Retrieve the last stored Claude session ID from PR comments."""
        session_id = get_session(pr_number, token=token)
        click.echo(session_id)

    # ── Approval gate ──

    @ci.command("approve-gate")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--stage", required=True, type=click.Choice(["spec", "design", "develop"]))
    @click.option("--pr", "pr_number", required=True, type=int, metavar="N")
    @click.option("--token", default="", metavar="TOKEN")
    def ci_approve_gate(cr_id: str, stage: str, pr_number: int, token: str) -> None:
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

    @ci.command("cr-status")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N")
    @click.option("--stage", default="", type=click.Choice(["", "spec", "design", "develop"]))
    @click.option("--branch", "branch_ref", default="", metavar="REF")
    @click.option("--token", default="", metavar="TOKEN")
    def ci_cr_status(cr_id: str, pr_number: int | None, stage: str, branch_ref: str, token: str) -> None:
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

    @ci.command("parse-approval")
    @click.option("--comment", "comment_body", required=True, metavar="TEXT")
    def ci_parse_approval(comment_body: str) -> None:
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

    # ── CR generation ──

    @ci.command("analyze-cr")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="PR number — revision mode: revise spec based on review comments")
    @click.pass_context
    def ci_analyze_cr(ctx: click.Context, cr_id: str, pr_number: int | None) -> None:
        """Generate or revise a CR spec using Claude.

        Assembles prompt (with embedded DHF impact skills), invokes claude -p,
        validates the spec front-matter, and self-corrects if validation fails.

        Model is read from ANTHROPIC_MODEL env var.
        Pass --pr N to revise an existing spec based on PR review comments.
        """
        from medharness.services.cr_generation import generate_spec  # noqa: PLC0415
        dhf: Path = ctx.obj["dhf"]
        result = generate_spec(cr_id, dhf, pr_number=pr_number)
        click.echo(json.dumps(result))
        click.echo(_format_summary("Spec", "revised" if pr_number else "generated", cr_id, result), err=True)

    @ci.command("design-cr")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="PR number — revision mode: revise design based on review comments")
    @click.pass_context
    def ci_design_cr(ctx: click.Context, cr_id: str, pr_number: int | None) -> None:
        """Generate or revise DHF design items for a CR using Claude.

        Assembles prompt (with embedded DHF impact skills), invokes claude -p
        to create/update DHF items via the medharness CLI.

        Model is read from ANTHROPIC_MODEL env var.
        Pass --pr N to revise existing design based on PR review comments.
        """
        from medharness.services.cr_generation import generate_design  # noqa: PLC0415
        dhf: Path = ctx.obj["dhf"]
        result = generate_design(cr_id, dhf, pr_number=pr_number)
        click.echo(json.dumps(result))
        click.echo(_format_summary("Design", "revised" if pr_number else "generated", cr_id, result), err=True)

    @ci.command("develop-cr")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="PR number — revision mode: revise implementation based on review comments")
    @click.pass_context
    def ci_develop_cr(ctx: click.Context, cr_id: str, pr_number: int | None) -> None:
        """Generate or revise implementation code for a CR using Claude.

        Reads the approved spec and CR item, then invokes claude -p to implement
        the required code changes following CLAUDE.md conventions.

        Model is read from ANTHROPIC_MODEL env var.
        Pass --pr N to revise existing implementation based on PR review comments.
        """
        from medharness.services.cr_generation import generate_code  # noqa: PLC0415
        dhf: Path = ctx.obj["dhf"]
        result = generate_code(cr_id, dhf, pr_number=pr_number)
        click.echo(json.dumps(result))
        click.echo(_format_summary("Implementation", "revised" if pr_number else "generated", cr_id, result), err=True)
