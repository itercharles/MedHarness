from __future__ import annotations

"""MedHarness CLI — main entrypoint and group registration."""

import click

from dhfkit.cli_errors import DHFAwareGroup
from pathlib import Path
import medharness._helpers as _h


@click.group(cls=DHFAwareGroup)
@click.version_option(package_name="medharness")
@click.option(
    "--dhf",
    default=None,
    metavar="PATH",
    help="Path to the DHF directory.",
)
@click.pass_context
def main(ctx: click.Context, dhf: str | None) -> None:
    """MedHarness CLI — AI harness and DHF tooling for medical device software."""
    ctx.ensure_object(dict)
    ctx.obj["dhf"] = Path(dhf) if dhf else None


from medharness.cli.dhf import register as register_dhf
from medharness.cli.ci import register as register_ci
from medharness.cli.init import register as register_init
from medharness.cli.doctor import register as register_doctor
from medharness.cli.analyse import register as register_analyse

register_dhf(main)
register_ci(main)
register_init(main)
register_doctor(main)
register_analyse(main)
