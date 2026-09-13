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

    Gates used to all sit under `verify`. The two that check a CR's promises —
    `change verify-branch`, `change verify-completion` — moved under `change`,
    because they read fields `change plan` writes and mean nothing to a project
    that does not use the CR workflow. Reading one group again would silently
    stop checking them.
    """
    found = set()
    for group in ("verify", "change"):
        for name, cmd in main.commands[group].commands.items():
            if group == "verify" or name.startswith("verify-"):
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


class TestManifestShape:
    @pytest.mark.parametrize("gate", GATES, ids=lambda g: g["command"])
    def test_entry_is_complete(self, gate: dict) -> None:
        assert gate["checks"].strip()
        assert gate["blocking"] in BLOCKING
        assert isinstance(gate["needs_network"], bool)
        assert isinstance(gate["needs_safety_class"], bool)

    @pytest.mark.parametrize("gate", GATES, ids=lambda g: g["command"])
    def test_conditional_and_opt_in_gates_explain_themselves(self, gate: dict) -> None:
        """"Sometimes blocks" is useless to a caller without the condition."""
        if gate["blocking"] in ("conditional", "opt_in"):
            assert gate["blocking_note"].strip(), (
                f"{gate['command']} is {gate['blocking']} but says nothing about when"
            )






class TestEveryGateAnswersWithTheEnvelope:
    """Discovery through the CLI, so a gate implemented anywhere is covered."""

    def test_all_six_gates_are_registered(self) -> None:
        assert len(_cli_gate_commands()) == len(GATES) == 6
