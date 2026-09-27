"""`workflow` — what Git and GitHub say about a change. CI helpers."""

from __future__ import annotations

import json
from pathlib import Path

import click

from medharness.cli.output import details, emit


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

    # ── Approval gate ──

    @workflow.command("check-approval")
    @click.option("--pr", "pr_number", required=True, type=int, metavar="N",
                  help="The pull request whose reviews are read.")
    @click.option("--token", default="", metavar="TOKEN",
                  help="GitHub token. Default: $GH_TOKEN, then $GITHUB_TOKEN.")
    def check_approval(pr_number: int, token: str) -> None:
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
                f"PASS — PR #{pr_number} approved by "
                f"{who or 'an unnamed reviewer'} at commit "
                f"{evidence['head_sha'][:7] or '?'}."
                if approved else
                f"FAIL — {evidence['reason']} on PR #{pr_number}."
            ),
            "errors": [] if approved else [
                f"{evidence['reason']} on PR #{pr_number}."
            ],
            "pr_number": pr_number,
            **evidence,
        })
        emit(payload)

        if evidence["approved"]:
            click.echo(
                f"PASS [approve] PR #{pr_number} approved "
                f"({who or 'reviewer unknown'}), commit {evidence['head_sha'][:7]}.",
                err=True,
            )
            return
        click.echo(
            f"FAIL [approve] {evidence['reason']} on PR #{pr_number}.",
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
