"""MedHarness CLI — main entrypoint and group registration."""

import click
from pathlib import Path
import medharness._helpers as _h


@click.group()
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
    ctx.obj["dhf"] = _h._resolve_dhf(dhf)


from medharness.cli.dhf import register as register_dhf
from medharness.cli.ci import register as register_ci
from medharness.cli.cr import register as register_cr
from medharness.cli.init import register as register_init

register_dhf(main)
register_ci(main)
register_cr(main)
register_init(main)
