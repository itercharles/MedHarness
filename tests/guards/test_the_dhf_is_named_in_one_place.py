"""`--dhf` goes before the command, and nowhere else.

Five `medharness` commands accepted `--dhf` after the command as well; the rest
rejected it with "No such option". Someone who learned `verify dhf --dhf DHF`
got a usage error from `context overview --dhf DHF`. The fix once went the other
way — add it to the one command that lacked it — which only moved the edge.

It defaults to `DHF`, the directory `init` creates, so from a project root
the CLI does not need it at all.
"""

from __future__ import annotations

import click
import pytest

from medharness.cli import main as medharness_main


def _leaves(group: click.Group, path: tuple[str, ...] = ()):
    for name, cmd in group.commands.items():
        if isinstance(cmd, click.Group):
            yield from _leaves(cmd, path + (name,))
        else:
            yield path + (name,), cmd


CLIS = {"medharness": medharness_main}
LEAVES = [(cli, path, cmd) for cli, root in CLIS.items() for path, cmd in _leaves(root)]


def test_the_walk_found_the_cli() -> None:
    assert {cli for cli, _, _ in LEAVES} == set(CLIS)
    assert len(LEAVES) >= 15, f"only {len(LEAVES)} commands found"


@pytest.mark.parametrize("cli,path,cmd", LEAVES, ids=[f"{c} {' '.join(p)}" for c, p, _ in LEAVES])
def test_no_command_takes_its_own_dhf(cli: str, path, cmd) -> None:
    own = [p for p in cmd.params if "--dhf" in getattr(p, "opts", ())]
    assert not own, f"`{cli} {' '.join(path)}` declares its own --dhf"


@pytest.mark.parametrize("cli", sorted(CLIS))
def test_the_root_defaults_to_dhf(cli: str) -> None:
    option = next(p for p in CLIS[cli].params if "--dhf" in p.opts)
    assert option.default == "DHF", f"{cli} --dhf defaults to {option.default!r}"
