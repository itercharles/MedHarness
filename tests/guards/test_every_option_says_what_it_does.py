"""Every option explains itself in --help.

39 options had no help text: `--coverage-pair`, `--since-ref`, `--token`,
`--requirement-type` among them. A reader of `--help` could not tell what they
took, what they defaulted to, or whether they were needed.
"""

from __future__ import annotations

import click
import pytest

from medharness.cli import main as medharness_main


def _options(cli: str, group: click.Group, path: tuple[str, ...] = ()):
    for param in group.params:
        if isinstance(param, click.Option) and param.name not in ("help", "version"):
            yield cli, path, param
    for name, cmd in group.commands.items():
        if isinstance(cmd, click.Group):
            yield from _options(cli, cmd, path + (name,))
        else:
            for param in cmd.params:
                if isinstance(param, click.Option):
                    yield cli, path + (name,), param


OPTIONS = list(_options("medharness", medharness_main))


def test_the_walk_found_options() -> None:
    assert len(OPTIONS) >= 25, f"only {len(OPTIONS)} options found"


@pytest.mark.parametrize(
    "cli,path,option", OPTIONS,
    ids=[f"{c} {' '.join(p)} {o.opts[0]}" for c, p, o in OPTIONS],
)
def test_the_option_has_help(cli: str, path, option: click.Option) -> None:
    assert (option.help or "").strip(), (
        f"`{cli} {' '.join(path)} {option.opts[0]}` has no help text"
    )
