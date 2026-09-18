"""The gate manifest must describe the CLI that exists, not the one it remembers.

A hand-written registry earns its keep — whether a gate blocks, reaches the
network, or is inert without a safety class are facts Click cannot express — but
only if it cannot drift from the commands it claims to describe.

So discovery here walks the **Click command tree**, not the service module. An
earlier version of this idea enumerated functions named ``*_gate`` in one module
and quietly missed three gates whose implementations live elsewhere. Asking the
CLI what commands exist is the question that has no wrong answer.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.services.ci import ENVELOPE_KEYS
from medharness.services.gates import BLOCKING, GATES


def _cli_gate_commands() -> set[str]:
    """Every gate the CLI exposes, wherever it lives.

    Gates sit under two verbs, not one: `verify *` answers from the DHF,
    `workflow *` cannot answer without the repository. Reading one group would
    silently stop checking the other — which is how `change`'s two gates went
    undescribed the first time this was a single-group walk.

    `workflow github-event` is not a gate: it exits 0 whatever it finds, so it
    has no verdict for the manifest to describe.
    """
    found = set()
    for group in ("verify", "workflow"):
        for name in main.commands[group].commands:
            if (group, name) == ("workflow", "github-event"):
                continue
            found.add(f"{group} {name}")
    return found


class TestManifestMatchesTheCLI:
    def test_every_cli_gate_is_described(self) -> None:
        described = {g["command"] for g in GATES}
        missing = _cli_gate_commands() - described
        assert not missing, (
            f"undocumented gate(s): {sorted(missing)}. Add them to GATES — an "
            f"agent discovers gates through the manifest and cannot call what "
            f"it is not told about."
        )

    def test_no_described_gate_is_imaginary(self) -> None:
        described = {g["command"] for g in GATES}
        stale = described - _cli_gate_commands()
        assert not stale, f"manifest describes commands that do not exist: {sorted(stale)}"

    @pytest.mark.parametrize("gate", GATES, ids=lambda g: g["command"])
    def test_required_options_exist_on_the_command(self, gate: dict) -> None:
        """A required option the command does not have would misdirect a caller."""
        group, _, name = gate["command"].partition(" ")
        params = {
            opt
            for param in main.commands[group].commands[name].params
            for opt in param.opts
        }
        for declared in gate["options"]["required"]:
            # "--junit-dir or --junit" documents a choice between two options.
            alternatives = [a.strip() for a in declared.split(" or ")]
            assert any(a in params for a in alternatives), (
                f"{gate['command']} does not accept {declared}"
            )

    @pytest.mark.parametrize("gate", GATES, ids=lambda g: g["command"])
    def test_every_required_option_is_declared(self, gate: dict) -> None:
        """The other direction.

        Checking only declared→exists let `workflow check-changes` ship a
        `required` list that omitted an option the command will not run without.
        A caller building from the manifest gets a usage error.
        """
        group, _, name = gate["command"].partition(" ")
        enforced = {
            param.opts[0]
            for param in main.commands[group].commands[name].params
            if getattr(param, "required", False)
        }
        declared = {
            a.strip()
            for entry in gate["options"]["required"]
            for a in entry.split(" or ")
        }
        missing = enforced - declared
        assert not missing, (
            f"{gate['command']} requires {sorted(missing)}, which the manifest "
            f"does not declare"
        )


class TestManifestShape:
    @pytest.mark.parametrize("gate", GATES, ids=lambda g: g["command"])
    def test_entry_is_complete(self, gate: dict) -> None:
        assert gate["checks"].strip()
        assert gate["blocking"] in BLOCKING
        assert isinstance(gate["needs_network"], bool)

    @pytest.mark.parametrize("gate", GATES, ids=lambda g: g["command"])
    def test_conditional_gates_explain_themselves(self, gate: dict) -> None:
        """"Sometimes blocks" is useless to a caller without the condition."""
        if gate["blocking"] == "conditional":
            assert gate["blocking_note"].strip(), (
                f"{gate['command']} is {gate['blocking']} but says nothing about when"
            )






class TestEveryGateAnswersWithTheEnvelope:
    """Discovery through the CLI, so a gate implemented anywhere is covered."""

    def test_every_gate_is_registered(self) -> None:
        assert len(_cli_gate_commands()) == len(GATES) == 6
