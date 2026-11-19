"""`medharness init` — Click declaration."""

import json
import click


def register(main):
    @main.command("init")
    @click.pass_context
    def init_cmd(ctx: click.Context) -> None:
        """Scaffold a DHF, and the AGENTS.md coding agents read, in the current directory.

        Takes no prompts — the project name is derived from the directory name.
        Existing files are not overwritten.
        """
        if ctx.parent.get_parameter_source("dhf") is not click.core.ParameterSource.DEFAULT:
            raise click.UsageError("init always scaffolds ./DHF and takes no --dhf.")
        from medharness.scaffold import run_init
        click.echo(json.dumps(run_init()))
