"""`workflow` — what Git and GitHub say about a change. CI helpers."""

from __future__ import annotations

import json
from pathlib import Path

import click

from medharness.cli.output import details, emit
from medharness.services.github_event import parse_github_event, plan_github_event, read_event


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


def register(main):
    workflow = main.commands["workflow"]

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
        emit(payload)
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
        for error in details(payload).get("findings", []):
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
        from medharness.services.envelope import envelope_from# noqa: PLC0415
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
        emit(payload)

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
