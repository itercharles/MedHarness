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
from medharness.services.gates import BLOCKING, GATES, gates_manifest


def _cli_verify_commands() -> set[str]:
    """Every `verify` subcommand the CLI actually exposes."""
    verify = main.commands["verify"]
    return {f"verify {name}" for name in verify.commands}


class TestManifestMatchesTheCLI:
    def test_every_cli_gate_is_described(self) -> None:
        described = {g["command"] for g in GATES}
        missing = _cli_verify_commands() - described
        assert not missing, (
            f"undocumented gate(s): {sorted(missing)}. Add them to GATES — an "
            f"agent discovers gates through the manifest and cannot call what "
            f"it is not told about."
        )

    def test_no_described_gate_is_imaginary(self) -> None:
        described = {g["command"] for g in GATES}
        stale = described - _cli_verify_commands()
        assert not stale, f"manifest describes commands that do not exist: {sorted(stale)}"

    @pytest.mark.parametrize("gate", GATES, ids=lambda g: g["command"])
    def test_required_options_exist_on_the_command(self, gate: dict) -> None:
        """A required option the command does not have would misdirect a caller."""
        name = gate["command"].removeprefix("verify ")
        params = {
            opt
            for param in main.commands["verify"].commands[name].params
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
        assert gate["clauses"], "a gate without a clause has no stated reason to exist"
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

    def test_manifest_publishes_the_envelope(self) -> None:
        assert gates_manifest()["envelope"] == list(ENVELOPE_KEYS)

    def test_manifest_publishes_exit_codes(self) -> None:
        assert set(gates_manifest()["exit_codes"]) == {"0", "1", "2"}


class TestCommand:
    def test_json_output_is_parseable(self) -> None:
        r = CliRunner().invoke(main, ["gates", "--json"])
        assert r.exit_code == 0, r.output
        payload = json.loads(r.output)
        assert {g["command"] for g in payload["gates"]} == {g["command"] for g in GATES}

    def test_human_output_names_every_gate(self) -> None:
        r = CliRunner().invoke(main, ["gates"])
        assert r.exit_code == 0, r.output
        for gate in GATES:
            assert gate["command"] in r.output

    def test_network_and_opt_in_are_visible_to_a_reader(self) -> None:
        """The two facts that change how you wire a pipeline."""
        r = CliRunner().invoke(main, ["gates"])
        assert "[network]" in r.output
        assert "needs safety class" in r.output


class TestEveryGateAnswersWithTheEnvelope:
    """Discovery through the CLI, so a gate implemented anywhere is covered."""

    def test_all_nine_gates_are_registered(self) -> None:
        assert len(_cli_verify_commands()) == len(GATES) == 9
