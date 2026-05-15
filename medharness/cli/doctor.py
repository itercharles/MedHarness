"""medharness doctor — CLI declarations."""

from __future__ import annotations

import json
import sys
import click


def register(main):

    @main.command("doctor")
    @click.option(
        "--json", "output_json", is_flag=True, default=False,
        help="Output machine-readable JSON instead of human-readable text.",
    )
    @click.pass_context
    def doctor(ctx: click.Context, output_json: bool) -> None:
        """Check local environment, CLI tools, and DHF config health.

        Verifies Python version, medharness/dhfkit imports, Claude CLI,
        gh CLI auth, and (if --dhf is set) DHF config and adapter init.
        """
        from medharness.commands.doctor import run_doctor
        dhf_path = ctx.obj.get("dhf") if ctx.obj else None
        report = run_doctor(dhf_path)

        if output_json:
            click.echo(json.dumps(report, indent=2))
            if not report["healthy"]:
                sys.exit(1)
            return

        for check in report["checks"]:
            icon = "✓" if check["passed"] else "✗"
            click.echo(f"  {icon}  {check['check']}: {check['detail']}")

        click.echo("")
        click.echo(report["summary"])
        if not report["healthy"]:
            sys.exit(1)
