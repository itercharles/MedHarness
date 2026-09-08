"""Turn a DHF data fault into a message instead of a traceback.

A hand-edited item with a mistyped field is the likeliest mistake a DHF user
makes, and it used to reach the terminal as a `ValidationError` traceback out
of nine of the thirteen commands — `verify dhf` included, whose whole purpose
is reporting exactly that kind of problem.

Both CLIs use this group. `dhfkit` owns it because `dhfkit` must not import
`medharness`, and a DHF data fault is a `dhfkit` concept.

The gates keep their documented shape: exit 1 with nothing on stdout, which
`docs/interface.md` defines as "the gate never ran". That is true here — the
input could not be read — and it is what the commands already did, minus the
traceback.
"""

from __future__ import annotations

import sys

import click

from dhfkit.exceptions import ValidationError


class DHFAwareGroup(click.Group):
    """A Click group that reports DHF data faults as errors."""

    def invoke(self, ctx: click.Context):
        try:
            return super().invoke(ctx)
        except ValidationError as exc:
            raise click.ClickException(
                f"The DHF could not be read: {exc}"
            ) from exc
        except FileNotFoundError as exc:
            # A missing global.yaml is the common case: pointing --dhf at a
            # directory that is not a DHF.
            raise click.ClickException(f"The DHF could not be read: {exc}") from exc


def report_dhf_error(exc: Exception) -> None:
    """For code paths outside a Click group."""
    click.echo(f"ERROR: The DHF could not be read: {exc}", err=True)
    sys.exit(1)
