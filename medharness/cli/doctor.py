"""medharness doctor — CLI declarations."""

from __future__ import annotations

import json
import sys

import click
from click.core import ParameterSource


def register(main):

    @main.command("doctor")
    @click.pass_context
    def doctor(ctx: click.Context) -> None:
        """Check local environment, CLI tools, and DHF config health.

        Verifies Python version, medharness/dhfkit imports, the model CLI, gh
        auth, and the DHF config. The DHF is checked when --dhf names one or
        ./DHF exists; before `init` there is nothing to check.
        """
        from medharness.commands.doctor import run_doctor

        dhf = ctx.obj["dhf"]
        named = ctx.parent.get_parameter_source("dhf") is not ParameterSource.DEFAULT
        report = run_doctor(dhf if named or dhf.exists() else None)

        click.echo(json.dumps(report))
        for check in report["checks"]:
            icon = "✓" if check["passed"] else "✗"
            click.echo(f"  {icon}  {check['check']}: {check['detail']}", err=True)
        click.echo(report["summary"], err=True)
        if not report["healthy"]:
            sys.exit(1)
