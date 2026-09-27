"""`medharness init` — Click declaration."""

import json
import click


def register(main):
    @main.command("init")
    def init_cmd() -> None:
        """Scaffold a DHF and a CLAUDE.md in the current directory.

        Takes no prompts — the project name is derived from the directory name.
        Existing files are not overwritten.
        """
        from medharness.workflows.init import run_init
        click.echo(json.dumps(run_init()))
