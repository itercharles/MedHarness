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
from medharness.services.github_event import parse_github_event
from medharness.services.github_session import get_session, put_session
from medharness.services.spec_validation import validate_spec

_ITEM_ID_RE = re.compile(r"^([A-Z]+-\d+)")


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
        """Generate CI-ready DHF artifacts: Markdown specs + JSON traceability report.

        Outputs specification documents (Markdown), plan documents, and a
        machine-readable traceability report (JSON). No PDF generation.

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

    # ── GitHub event context ──

    @ci.command("github-event")
    @click.option("--event", "event_path", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--manual-cr", default="", metavar="CR_ID")
    @click.option("--github-output", "github_output_path", default=None, type=click.Path(dir_okay=False, path_type=Path))
    @click.pass_context
    def ci_github_event(ctx: click.Context, event_path: Path | None, manual_cr: str,
                        github_output_path: Path | None) -> None:
        """Parse GitHub event payload and output CR context for CI workflow steps.

        Writes cr_id, mode, and pr_number to --github-output (if provided)
        in $GITHUB_OUTPUT format. Also prints JSON to stdout.
        """
        result = parse_github_event(event_path, manual_cr_id=manual_cr)
        payload = {
            "cr_id": result.cr_id,
            "mode": result.mode,
            "pr_number": result.pr_number,
            "reason": result.reason,
        }
        click.echo(json.dumps(payload, default=str))

        if github_output_path:
            with open(github_output_path, "a", encoding="utf-8") as f:
                for key in ("cr_id", "mode", "pr_number"):
                    val = payload.get(key)
                    if val is not None:
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
