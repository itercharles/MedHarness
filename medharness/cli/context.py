"""`medharness context` — what an AI agent reads before working on a CR."""

from __future__ import annotations

import json
from pathlib import Path

import click

from dhfkit.local_adapter import LocalDHFAdapter
from medharness.cli.options import collect_junit_paths


def register(main):

    @main.command("context")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR the agent is about to work on.")
    @click.option("--junit", "junit_files", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="A JUnit XML results file (repeatable). Adds test coverage.")
    @click.option("--junit-dir", "junit_dirs", multiple=True,
                  type=click.Path(file_okay=False, path_type=Path),
                  help="Directory of JUnit XML results (repeatable). Adds test coverage.")
    @click.pass_context
    def context(ctx: click.Context, cr_id: str,
                junit_files: tuple[Path, ...], junit_dirs: tuple[Path, ...]) -> None:
        """What an AI agent reads before working on a CR, as JSON.

        The same context `build plan` and `build code` put in their prompts.

        \b
        scope "whole_dhf": the CR records no affected_items yet (before
                           `build plan`), so items holds every item summarized.
        scope "affected":  items holds the CR's affected_items in full, and
                           modules only the modules that own them.

        Always present: project, cr, scope, types, items, modules, risks.
        --junit/--junit-dir add test_coverage. Whether the DHF holds together
        is `verify dhf`'s answer, not this command's.
        """
        from medharness.services.context import cr_context

        adapter = LocalDHFAdapter(ctx.obj["dhf"])
        result = cr_context(adapter, cr_id)

        junit_paths = collect_junit_paths(junit_files, junit_dirs)
        if junit_paths:
            from medharness.services.context import compute_item_coverage
            result["test_coverage"] = compute_item_coverage(junit_paths, adapter)

        click.echo(json.dumps(result, default=str))
