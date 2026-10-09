"""How every command writes its answer: JSON to stdout, lines to stderr."""

from __future__ import annotations

import json

import click


def details(result: dict) -> dict:
    """The gate's structured findings, for the lines a command prints.

    In-process only: `emit` does not serialise them. A caller acts on the
    verdict and reads the messages in `errors` and `warnings`.
    """
    return result.get("details") or {}


def emit(result: dict) -> None:
    """Write the gate's answer to stdout: the verdict, and what it found."""
    click.echo(json.dumps(
        {k: v for k, v in result.items() if k != "details"}, default=str,
    ))


def render_envelope(result: dict, tag: str) -> None:
    """Print the envelope's errors and warnings.

    Used where the envelope is the *only* source for a finding. Gates whose own
    loops already print a richer line (uncovered IDs, fix hints) must not also
    call this — two renderers over the same findings printed every SOUP
    vulnerability twice.

    `test_stderr_reports_the_envelope` asserts the other half: no gate may leave
    an envelope message unprinted.
    """
    for message in result.get("warnings") or []:
        click.echo(f"WARN [{tag}] {message}", err=True)
    for message in result.get("errors") or []:
        click.echo(f"FAIL [{tag}] {message}", err=True)
