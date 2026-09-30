"""Regenerate the parts of docs/interface.md that the code already states.

The command reference (every command, its summary and options) is read from the
Click tree, and the gate table from `services/gates.py`, so neither can drift
from the CLI. The prose around them is written by hand.

    python scripts/generate_interface.py           # rewrite docs/interface.md
    python scripts/generate_interface.py --check   # exit 1 if it is out of date
"""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import click

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "interface.md"

#: How the reference lists the groups; a group not named here is appended.
GROUP_ORDER = ("item", "verify", "build", "init")


def _summary(cmd: click.Command) -> str:
    """The first paragraph of the command's help, on one line."""
    paragraph = inspect.cleandoc(cmd.help or "").split("\n\n")[0]
    return " ".join(paragraph.split())


def _commands(main: click.Group) -> list[tuple[str, click.Command]]:
    """Every command as (`group name`, command); a top-level command has no group."""
    found: list[tuple[str, click.Command]] = []
    names = [n for n in GROUP_ORDER if n in main.commands]
    names += [n for n in main.commands if n not in names]
    for name in names:
        node = main.commands[name]
        if isinstance(node, click.Group):
            found += [(f"{name} {sub}", cmd) for sub, cmd in node.commands.items()]
        else:
            found.append((name, node))
    return found


def render_reference() -> str:
    from medharness.cli import main

    ctx = click.Context(main, info_name="medharness")
    lines = ["| Command | What it does |", "|---|---|"]
    commands = _commands(main)
    lines += [f"| `{path}` | {_summary(cmd)} |" for path, cmd in commands]

    for path, cmd in commands:
        options = []
        for param in cmd.get_params(click.Context(cmd, parent=ctx, info_name=path)):
            if not isinstance(param, click.Option) or "--help" in param.opts:
                continue
            record = param.get_help_record(click.Context(cmd, parent=ctx))
            options.append(f"| `{record[0]}` | {' '.join(record[1].split())} |")
        arguments = " ".join(
            p.make_metavar(click.Context(cmd)) for p in cmd.params if isinstance(p, click.Argument)
        )
        usage = f"medharness {path}" + (f" {arguments}" if arguments else "")
        lines += ["", f"#### `{usage}`", "", _summary(cmd)]
        if options:
            lines += ["", "| Option | |", "|---|---|", *options]
    return "\n".join(lines)


def render_gate_table() -> str:
    from medharness.cli import main
    from medharness.services.gates import GATES

    lines = ["| Gate | Checks | Options | Network | Blocking |", "|---|---|---|---|---|"]
    for gate in GATES:
        group, _, name = gate["command"].partition(" ")
        params = main.commands[group].commands[name].params
        options = [
            f"`{p.opts[0]}`" + (" (required)" if p.required else "")
            for p in params if isinstance(p, click.Option) and "--help" not in p.opts
        ]
        lines.append(
            f"| `{gate['command']}` | {gate['checks']} | {', '.join(options) or '—'} "
            f"| {'yes' if gate['needs_network'] else 'no'} | `{gate['blocking']}` |"
        )
    return "\n".join(lines)


BLOCKS = {"reference": render_reference, "gates": render_gate_table}


def update(text: str) -> str:
    """`text` with every generated block replaced by a fresh rendering."""
    for name, render in BLOCKS.items():
        pattern = re.compile(
            rf"(<!-- BEGIN GENERATED: {name} [^>]*-->)\n.*?\n?(<!-- END GENERATED: {name} -->)", re.S
        )
        if not pattern.search(text):
            raise SystemExit(f"{DOC.name} has no GENERATED block named {name!r}")
        text = pattern.sub(lambda m: f"{m.group(1)}\n{render()}\n{m.group(2)}", text)
    return text


def main() -> int:
    current = DOC.read_text(encoding="utf-8")
    fresh = update(current)
    if "--check" in sys.argv:
        if fresh != current:
            print(f"{DOC.relative_to(ROOT)} is out of date: run python scripts/generate_interface.py",
                  file=sys.stderr)
            return 1
        return 0
    DOC.write_text(fresh, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
