from __future__ import annotations

"""MedHarness CLI — main entrypoint and group registration."""

import click

from dhfkit.cli_errors import DHFAwareGroup
from pathlib import Path


@click.group(cls=DHFAwareGroup)
@click.version_option(package_name="medharness")
@click.option(
    "--dhf",
    default="DHF",
    show_default=True,
    metavar="PATH",
    help="Path to the DHF directory. Goes before the command.",
)
@click.pass_context
def main(ctx: click.Context, dhf: str) -> None:
    """MedHarness — a Design History File in the repository, and the checks and steps around it."""
    ctx.ensure_object(dict)
    ctx.obj["dhf"] = Path(dhf)


# The verbs are defined here, not in the module that happens to register
# first: several modules attach commands to the same group, and whoever created
# it would silently decide the group's help text.
@main.group("verify")
def verify() -> None:
    """Check a change against the DHF and the working tree. Runs locally and in CI."""


@main.group("build")
def build() -> None:
    """Produce DHF items, code, and delivery artifacts."""


from medharness.cli.verify import register as register_verify
from medharness.cli.build import register as register_build
from medharness.cli.init import register as register_init
from medharness.cli.item import register as register_item

register_verify(main)
register_build(main)
register_init(main)
register_item(main)
