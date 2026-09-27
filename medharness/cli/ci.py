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
from medharness.services.github_event import parse_github_event, plan_github_event, read_event
_ITEM_ID_RE = re.compile(r"^([A-Z]+-\d+)")


def _d(result: dict) -> dict:
    """The gate's structured findings, for rendering the lines below.

    In-process only. `_emit` does not serialise them: a caller acts on the
    verdict and reads the messages, and nothing has ever read the structures.
    """
    return result.get("details") or {}


def _emit(result: dict) -> None:
    """Write the gate's answer to stdout: the verdict, and what it found."""
    click.echo(json.dumps(
        {k: v for k, v in result.items() if k != "details"}, default=str,
    ))


def _render_envelope(result: dict, tag: str) -> None:
    """Print the envelope's errors and warnings.

    Used where the envelope is the *only* source for a finding. Gates whose own
    loops already print a richer line (uncovered IDs, fix hints) must not also
    call this — two renderers over the same findings printed every SOUP
    vulnerability twice.

    `test_stderr_reports_the_envelope` asserts the other half: no gate may leave
    an envelope message unprinted.
    """
    for message in result.get("warnings") or []:
        click.echo(f"WARN [{tag}] {message}", err=True)
    for message in result.get("errors") or []:
        click.echo(f"FAIL [{tag}] {message}", err=True)


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

    verify = main.commands["verify"]
    build = main.commands["build"]
    workflow = main.commands["workflow"]

    @verify.command("dhf")
    @click.option("--fail-on-uncovered", is_flag=True, default=False,
                  help="Exit non-zero when items lack downstream coverage. "
                       "Without it, coverage gaps are reported as WARN only.")
    @click.pass_context
    def verify_dhf(ctx: click.Context, fail_on_uncovered: bool) -> None:
        """Check the DHF holds together: schema, links, cycles, coverage.

        Always blocking: schema errors, required-traceability failures, and
        dangling links (a link whose target ID does not exist).

        Advisory by default: coverage gaps — pass --fail-on-uncovered to enforce.
        """
        effective_dhf = ctx.obj["dhf"]
        result = ci_structural_gate(dhf_path=effective_dhf,
                                     fail_on_uncovered=fail_on_uncovered)
        _emit(result)
        r = _d(result)["results"]
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
        for gap in r.get("verification_gaps", []):
            click.echo(f"WARN [verification] {gap['id']}: {gap['issue']}", err=True)
            click.echo(f"      Fix: dhfkit {dhf_arg} item update {gap['id']}"
                       f" --data '{{\"verification_criteria\": \"<how this is verified>\"}}'",
                       err=True)
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
            for message in [e for e in result["errors"] if "target does not exist" in e]:
                click.echo(f"FAIL [dangling] {message}", err=True)
                click.echo("    Fix: correct the ID in the source item, or create the "
                           "target. The link exists but resolves to nothing.", err=True)
            for message in [e for e in result["errors"] if e.startswith("Traceability cycle:")]:
                # The gate's own wording, not a second rendering of it: two
                # spellings of one finding is two findings to a reader.
                click.echo(f"FAIL [cycle] {message}", err=True)
                click.echo("    Fix: the V-model is directed. Remove whichever link "
                           "reverses the chain so each item has an origin.", err=True)

            # Uncovered items are advisory unless --fail-on-uncovered is set; label
            # them WARN so a green build never prints FAIL.
            gap_label = "FAIL" if fail_on_uncovered else "WARN"
            for c in t.get("coverage", []):
                click.echo(f"{'PASS' if c['passed'] else gap_label} [coverage] "
                           f"{c['parent_type']}→{c['child_type']}: "
                           f"{c['covered']}/{c['total']} covered", err=True)
                if not c["passed"]:
                    click.echo(f"    Fix: dhfkit {dhf_arg} item list"
                               f" --type {c['child_type']} to find uncovered items,"
                               f" then add dhf_links to their YAML.", err=True)
                    if not fail_on_uncovered:
                        click.echo("         Advisory only — pass --fail-on-uncovered"
                                   " to block the build on this.", err=True)
        if "coverage" in r:
            for row in r["coverage"].get("pairs", []):
                if row.get("error"):
                    # Without this the line read as a coverage shortfall, which
                    # sent people looking for missing items rather than a typo.
                    click.echo(f"FAIL [gate] {row['parent_type']}→{row['child_type']}: "
                               f"{row['error']}", err=True)
                    continue
                if row.get("skipped"):
                    click.echo(f"SKIP [gate] {row['parent_type']}→{row['child_type']}: "
                               f"{row['skipped']}", err=True)
                    continue
                click.echo(f"{'PASS' if row.get('passed') else 'FAIL'} [gate] "
                           f"{row['parent_type']}→{row['child_type']}: "
                           f"{row['covered']}/{row['total']} covered", err=True)
        if not result["passed"]:
            raise click.ClickException("DHF validation failed.")

    @verify.command("tests")
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path),
                  help="Directory of JUnit XML results (repeatable).")
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="A JUnit XML results file (repeatable).")
    @click.option("--require-method", is_flag=True, default=False,
                  help="Make a requirement with no declared verification_method fail. "
                       "Warns by default, so a project adding the field is not blocked.")
    @click.pass_context
    def verify_tests(ctx: click.Context,
                         junit_dirs: tuple[Path, ...], junit_files: tuple[Path, ...],
                         require_method: bool = False) -> None:
        """Check each requirement is verified by the method it declares.

        A requirement declaring Test needs a passing JUnit case linked to it;
        declared test points each need a covering case.
        """
        effective_dhf = ctx.obj["dhf"]
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = ci_test_coverage_gate(dhf_path=effective_dhf, junit_paths=junit_paths,
                                       require_method=require_method)
        _emit(result)
        dhf_arg = f"--dhf {effective_dhf}"
        # The rows below print per-type coverage; the envelope's warnings are
        # about the gate as a whole and have no row to be printed beside.
        for message in result.get("warnings") or []:
            click.echo(f"WARN [test-coverage] {message}", err=True)
        rows = _d(result)["results"]
        if not rows:
            # Every detail loop below iterates `results`; with none, the envelope
            # is the only place the reason exists. Without this, a missing
            # --junit-dir failed with "Test coverage gaps found." — pointing at
            # coverage when nothing had been read.
            _render_envelope(result, "test-coverage")
        for row in rows:
            if row["passed"]:
                click.echo(f"PASS [test-coverage] {row['type']}: "
                           f"{row['covered']}/{row['total']} requirements covered", err=True)
            else:
                click.echo(f"FAIL [test-coverage] {row['type']}: "
                           f"{row['covered']}/{row['total']} requirements covered", err=True)
                for uid in row.get("uncovered", []):
                    click.echo(f"      ↳ uncovered: {uid}", err=True)
                    click.echo(f"        Fix: add 'dhf_links: [{uid}]' to a test case, or:", err=True)
                    click.echo(f"             dhfkit {dhf_arg} item create --type TC"
                               f" --data '{{\"title\": \"Test {uid}\", \"dhf_links\": [\"{uid}\"]}}'", err=True)
        for row in _d(result).get("testing_points", []):
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


    @verify.command("completion")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR to close.")
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path),
                  help="Directory of JUnit XML results for the items this CR touched (repeatable).")
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="A JUnit XML results file for the items this CR touched (repeatable).")
    @click.pass_context
    def verify_completion(
        ctx: click.Context,
        cr_id: str,
        junit_dirs: tuple[Path, ...],
        junit_files: tuple[Path, ...],
    ) -> None:
        """Check a CR delivered what it proposed: its items created and verified.

        Reads proposed_new_items from the CR item, checks each proposed type was
        created in the DHF, then runs the verification completeness gate over the
        items this CR touched — its affected_items and the items matching its
        proposals — so a CR is not charged with the DHF's existing gaps.

        Reads only the working tree, so it runs on the branch as well as on main.
        Run it on the branch to block the merge: the CR fields and the proposed
        items settle there. Run it again on main for the half that
        can differ — the tests re-run against whatever else landed meanwhile.

        Exits non-zero when any proposed items are missing or unverified.
        """
        from medharness.services.ci import cr_closure_gate

        effective_dhf = ctx.obj["dhf"]
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = cr_closure_gate(cr_id=cr_id, dhf_path=effective_dhf,
                                 junit_paths=junit_paths)
        _emit(result)

        for field in _d(result).get("incomplete_cr_fields", []):
            click.echo(f"FAIL [completion] {field['issue']}", err=True)
        for item in _d(result).get("missing_items", []):
            click.echo(
                f"FAIL [completion] {item['type']}: {item.get('issue', 'proposed item not found')}",
                err=True,
            )
        for item in _d(result).get("verification_gaps", []):
            click.echo(f"FAIL [completion] {item['id']}: no verification_method declared", err=True)
        for item in _d(result).get("unverified_test", []):
            click.echo(f"FAIL [completion] {item['id']}: Test method declared but no passing TC linked", err=True)
        for item in _d(result).get("manual_review_required", []):
            methods = ", ".join(item.get("methods", []))
            click.echo(f"WARN [completion] {item['id']}: {methods} — requires manual sign-off record", err=True)

        click.echo(result["summary"], err=True)
        if not result["passed"]:
            raise click.ClickException(f"CR {cr_id} closure verification failed.")

    @verify.command("soup")
    @click.option("--manifest", "manifest_paths", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  metavar="PATH",
                  help="Dependency manifest to compare the register against (repeatable). "
                       "Auto-discovers when omitted.")
    @click.option("--fail-on-drift", is_flag=True, default=False,
                  help="Make an undocumented or misversioned component fail the gate. "
                       "Warns by default, so a project backfilling its register is not blocked.")
    @click.option("--offline-mode", type=click.Choice(["fail", "warn"]), default="fail",
                  help="Behaviour when osv.dev is unreachable. 'warn' keeps the gate "
                       "passing for air-gapped or proxy-restricted pipelines.")
    @click.pass_context
    def verify_soup(
        ctx: click.Context,
        manifest_paths: tuple[Path, ...],
        fail_on_drift: bool,
        offline_mode: str,
    ) -> None:
        """Check the SOUP register matches what ships, and is not known-vulnerable.

        Compares the register against the dependency manifests, then each item
        against the OSV database. A package in a manifest with no SOUP item, or
        at a different version, warns unless --fail-on-drift is passed.

        SOUP items must have an 'ecosystem' field (e.g. PyPI, npm) to be checked.
        Exits non-zero if any unresolved vulnerabilities are found.

        A vulnerability the team has assessed can be recorded on the SOUP item so it
        no longer blocks, per IEC 62304 §8.1.2 — both 'id' and 'rationale' are required:

            accepted_vulns:
              - id: GHSA-xxxx-yyyy-zzzz
                rationale: "Affected API is not reachable from our code paths."

        Newly published vulnerabilities still block, because acceptance is per-ID.

        Outputs structured JSON to stdout; human-readable messages to stderr.
        """
        from medharness.services.ci import soup_gate

        effective_dhf = ctx.obj["dhf"]
        result = soup_gate(effective_dhf, offline_mode=offline_mode,
                           manifest_paths=list(manifest_paths), fail_on_drift=fail_on_drift)
        _emit(result)

        for entry in _d(result).get("accepted", []):
            click.echo(
                f"ACCEPTED [soup-vuln] {entry['soup_id']} ({entry['name']}@{entry['version']}): "
                f"{entry['vuln_id']} — {entry['rationale']}",
                err=True,
            )

        _render_envelope(result, "soup-vuln")
        if _d(result).get("drift", {}).get("undocumented") or \
                _d(result).get("drift", {}).get("misversioned"):
            click.echo("    Fix: medharness --dhf DHF build dhf --write, then commit. "
                       "Pass --fail-on-drift to block the build on this.", err=True)
        click.echo(result["summary"], err=True)
        if not result["passed"]:
            raise click.ClickException("SOUP check failed.")

    @workflow.command("check-changes")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR whose affected_items the branch must change.")
    @click.option("--since-ref", default="origin/main", metavar="REF",
                  help="What the branch is compared against.")
    @click.option("--code-path", "code_paths", multiple=True, metavar="PATH",
                  help="Opt into code-change enforcement: path(s) under which at least one file must be modified. "
                       "Omitting this option skips the code-change check entirely.")
    @click.pass_context
    def check_changes(
        ctx: click.Context,
        cr_id: str,
        since_ref: str,
        code_paths: tuple[str, ...],
    ) -> None:
        """Check the branch changed the items the CR said it would.

        Reads `affected_items` off the CR and diffs the branch against
        `--since-ref`. An item the CR promised that the branch never touches
        fails, and so does a CR that promised nothing and changed no DHF item
        at all — that means `build plan` never ran.

        `--code-path src/` adds a second requirement: at least one file under
        those paths must have changed too. Without the flag that check is
        skipped, so a design-only branch passes.

        Needs a reachable `--since-ref`. This is the only command that reads a
        git diff, which is what puts it under `workflow` rather than `verify`.
        """
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
        _emit(payload)
        if payload["passed"]:
            if code_paths:
                click.echo(f"PASS [check-changes] {cr_id}: branch carries coupled DHF and code changes.", err=True)
            else:
                click.echo(
                    f"PASS [check-changes] {cr_id}: branch carries DHF changes "
                    f"(pass --code-path to also enforce code changes).",
                    err=True,
                )
            return
        for error in _d(payload).get("findings", []):
            click.echo(f"FAIL [check-changes] {error['field']}: {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        raise click.exceptions.Exit(1)

    # ── GitHub event context ──

    @workflow.command("github-event")
    @click.option("--event", "event_path", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="Event payload JSON. Default: $GITHUB_EVENT_PATH.")
    @click.option("--manual-cr", default="", metavar="CR_ID",
                  help="CR to report instead of the one the event names.")
    @click.option("--manual-stage", default="", metavar="STAGE",
                  help="Stage to report instead of the one the event implies.")
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
    @click.option("--github-output", "github_output_path", default=None, type=click.Path(dir_okay=False, path_type=Path),
                  help="File to append step outputs to, normally $GITHUB_OUTPUT.")
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
        """Read a GitHub event: which CR and stage it concerns, and what to do.

        The base parser returns CR context. Optional stage/action mappings let a
        client repo keep lifecycle policy in Python while still choosing its
        own branch conventions, label scheme, and action names.

        Branch on `action`, not on `mode`. `action` is the verdict your own
        mappings produced and is an opaque string this tool never interprets.
        `mode` is this tool's built-in reading of the event — one of `new`,
        `iterate`, `cancel`, `skip` — and is only the value `action` falls back
        to when no mapping matches. They differ whenever a mapping fires, which
        is the normal case, not a contradiction.

        This is not a gate: it reports what an event concerns and exits 0
        whatever it finds. Nothing here passes or fails.
        """
        try:
            event, event_name = read_event(event_path)
        except ValueError as exc:
            # A usage-shaped failure: exit 1 with nothing on stdout, which
            # docs/interface.md defines as "raised before the command ran".
            raise click.ClickException(str(exc)) from exc
        result = parse_github_event(event, event_name, manual_cr_id=manual_cr)
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
            # Absent means "not derivable from the payload", not "none": an
            # issue linked through the GitHub UI leaves no trace there.
            "issue_number": result.issue_number,
        }
        click.echo(json.dumps(payload, default=str))

        if github_output_path:
            with open(github_output_path, "a", encoding="utf-8") as f:
                for key in ("cr_id", "mode", "pr_number", "stage", "action",
                            "event_name", "branch_ref", "issue_number"):
                    val = payload.get(key)
                    if val is not None and val != "":
                        f.write(f"{key}={val}\n")

    # ── Approval gate ──

    @workflow.command("check-approval")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR this approval is for; named in the answer.")
    @click.option("--pr", "pr_number", required=True, type=int, metavar="N",
                  help="The pull request whose reviews are read.")
    @click.option("--token", default="", metavar="TOKEN",
                  help="GitHub token. Default: $GH_TOKEN, then $GITHUB_TOKEN.")
    def check_approval(cr_id: str, pr_number: int, token: str) -> None:
        """Check that a reviewer approved the commit this PR would merge.

        Reads the PR's reviews and requires an APPROVED one whose `commit_id`
        is the current head. An approval of an earlier commit is reported as
        stale and fails: it approved work that has since changed.

        There is no stage to pass: a design approval goes stale as soon as the
        code lands, so the develop gate needs its own review either way.

        Exits 0 when such a review exists, 1 otherwise.
        """
        from medharness.services.ci import envelope_from  # noqa: PLC0415
        from medharness.services.pr_approval import approval_evidence  # noqa: PLC0415

        evidence = approval_evidence(pr_number, token=token)
        approved = evidence["approved"]
        who = ", ".join(
            f"{a['by']} at {a['at']}" for a in evidence["approvals"] if a.get("by")
        )
        payload = envelope_from("workflow check-approval", {
            "passed": approved,
            "summary": (
                f"PASS — {cr_id} approved on PR #{pr_number} by "
                f"{who or 'an unnamed reviewer'} at commit "
                f"{evidence['head_sha'][:7] or '?'}."
                if approved else
                f"FAIL — {cr_id}: {evidence['reason']} on PR #{pr_number}."
            ),
            "errors": [] if approved else [
                f"{cr_id}: {evidence['reason']} on PR #{pr_number}."
            ],
            "cr_id": cr_id,
            "pr_number": pr_number,
            **evidence,
        })
        _emit(payload)

        if evidence["approved"]:
            click.echo(
                f"PASS [approve] {cr_id}: approved on PR #{pr_number} "
                f"({who or 'reviewer unknown'}), commit {evidence['head_sha'][:7]}.",
                err=True,
            )
            return
        click.echo(
            f"FAIL [approve] {cr_id}: {evidence['reason']} on PR #{pr_number}.",
            err=True,
        )
        for a in evidence["stale_approvals"]:
            commit = (a.get("commit") or "?")[:7]
            click.echo(
                f"    {a.get('by')} approved commit {commit}; the PR now merges "
                f"{evidence['head_sha'][:7] or '?'}.", err=True,
            )
        click.echo(
            "    Fix: a label is not evidence — have a reviewer approve the "
            "current commit.", err=True,
        )
        raise click.exceptions.Exit(1)

    # ── CR generation ──

    @build.command("plan")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR to design: its item cascade and impact analysis.")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="PR number — revision mode: revise DHF cascade based on review comments")
    @click.pass_context
    def change_plan(ctx: click.Context, cr_id: str, pr_number: int | None) -> None:
        """Draft the DHF item cascade and impact analysis for a CR, with a model.

        Drives the V-model (CRS→SYS→SYSARCH/RISK/RCM→SRS→SWDD). The model writes
        items through the dhfkit CLI; deterministic validation and one fix pass
        run afterwards, then a design review.

        The model is MEDHARNESS_DESIGN_MODEL (and MEDHARNESS_DESIGN_REVIEW_MODEL
        for the review) as "provider:model", else Anthropic with ANTHROPIC_MODEL.
        Pass --pr N to revise the items from that PR's review comments.
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
        _emit(result)
        click.echo(
            _format_summary("DHF cascade", "revised" if pr_number else "generated", cr_id, result),
            err=True,
        )
        for error in result.get("errors") or []:
            click.echo(f"  FAIL ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        _raise_for_outcome_error(result)

    @build.command("code")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR whose approved design to implement.")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="PR number — revision mode: revise implementation based on review comments")
    @click.option("--ci-failures", "ci_failures_path", default=None,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="JSON file containing structured CI failure output to feed back to Claude")
    @click.pass_context
    def change_implement(ctx: click.Context, cr_id: str, pr_number: int | None,
                      ci_failures_path: Path | None) -> None:
        """Write the code and tests for a CR's approved design, with a model.

        Reads the CR's implementation_notes and the items it affects, and
        implements them following the repository's CLAUDE.md.

        The model is MEDHARNESS_DEVELOP_MODEL (and MEDHARNESS_CODE_REVIEW_MODEL
        for the review) as "provider:model", else Anthropic with ANTHROPIC_MODEL.
        Pass --pr N to revise the code from that PR's review comments.
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
        _emit(result)
        click.echo(_format_summary("Implementation", "revised" if pr_number else "generated", cr_id, result), err=True)
        for error in result.get("errors") or []:
            click.echo(f"  FAIL ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        _raise_for_outcome_error(result)
