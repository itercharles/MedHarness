"""The command reference in docs/interface.md is generated, so it cannot drift.

It had drifted every way a hand-kept copy can: a README table that listed 8 of
16 commands, a manifest that called `--junit` required when the command did not,
a hint that named an option the command had lost. The reference and the gate
table are now rendered from the Click tree and `services/gates.py`; this fails
when the committed document is not what the generator writes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import click

from medharness.cli import main

ROOT = Path(__file__).resolve().parents[2]


def _generator():
    spec = importlib.util.spec_from_file_location(
        "generate_interface", ROOT / "scripts" / "generate_interface.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_committed_document_is_what_the_generator_writes() -> None:
    generator = _generator()
    current = generator.DOC.read_text(encoding="utf-8")
    assert generator.update(current) == current, (
        "docs/interface.md is out of date: run `python scripts/generate_interface.py`"
    )


def test_every_command_and_option_is_in_the_reference() -> None:
    """Generated is not the same as complete: check it against the tree itself."""
    reference = _generator().render_reference()
    for group, node in main.commands.items():
        commands = node.commands.items() if isinstance(node, click.Group) else [("", node)]
        for name, cmd in commands:
            path = f"{group} {name}".strip()
            assert f"`{path}`" in reference, f"`{path}` is missing from the reference"
            for param in cmd.params:
                if isinstance(param, click.Option) and "--help" not in param.opts:
                    assert f"`{param.opts[0]}" in reference, f"{path}: {param.opts[0]} is missing"
