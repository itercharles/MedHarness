"""A gate that needs a CR belongs with the commands that make one.

All six gates used to sit under `verify`, which said they were the same kind of
thing. Four read the DHF and apply to any project using it. Two read
`affected_items` and `proposed_new_items` — fields `change plan` writes — and
mean nothing to a project that does not run the CR workflow. Grouping them
together told an adopter to wire all six into CI.

The split is the `--cr` requirement, so it can be checked rather than trusted.
"""

from __future__ import annotations

from medharness.cli import main
from medharness.services.gates import GATES


def test_the_manifest_is_not_empty() -> None:
    assert len(GATES) >= 5, f"only {len(GATES)} gates — the import is wrong"


def test_a_gate_needing_a_cr_lives_under_change() -> None:
    misplaced = [
        g["command"] for g in GATES
        if "--cr" in g["options"]["required"] and not g["command"].startswith("change ")
    ]
    assert not misplaced, (
        "these gates require a CR but sit outside `change`, where a project not "
        f"running the CR workflow will read them as applying to it: {misplaced}"
    )


def test_a_gate_under_verify_needs_no_cr() -> None:
    coupled = [
        g["command"] for g in GATES
        if g["command"].startswith("verify ") and "--cr" in g["options"]["required"]
    ]
    assert not coupled, f"`verify` gates must work without a CR: {coupled}"


def test_every_manifest_command_resolves() -> None:
    """The manifest names a path; the path must exist wherever it points."""
    for gate in GATES:
        group, _, name = gate["command"].partition(" ")
        assert group in main.commands, f"{gate['command']}: no group {group!r}"
        assert name in main.commands[group].commands, (
            f"{gate['command']} is in the manifest but not in the CLI"
        )
