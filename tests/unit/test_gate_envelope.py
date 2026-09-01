"""The gate result envelope is a contract, not a coincidence.

Before this, the only key every gate shared was ``passed``. Five gates meant
five shapes, so a CI script or an agent had to write a parser per gate — and
each new gate added another.

These tests fail if a gate drifts, and — more importantly — if a *new* gate is
added without adopting the envelope. The discovery test enumerates the module
rather than naming gates, so it covers gates that do not exist yet.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.services import ci as ci_module
from medharness.services.ci import (
    ENVELOPE_KEYS,
    ci_test_coverage_gate,
    gate_result,
)
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

#: Gates that take only a DHF path, so they can be called generically.
SIMPLE_GATES = (
    "ci_structural_gate",
    "soup_vuln_gate",
    "classification_gate",
    "plans_gate",
)

#: Arguments each CLI gate needs to reach its reporting path.
GATE_ARGS = {
    "verify tests": ["--junit-dir", "{dhf}/test-results"],
    "verify completion": ["--cr", "CR-001"],
    "verify branch": ["--cr", "CR-001"],
    "verify code": ["--cr", "CR-001"],
}


def _run_gate(command: str, dhf) -> dict:
    from medharness.cli import main as cli_main

    args = ["--dhf", str(dhf), *command.split()]
    args += [a.format(dhf=dhf) for a in GATE_ARGS.get(command, [])]
    r = CliRunner().invoke(cli_main, args)
    return json.loads(r.output.splitlines()[0])


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Trial")
    return tmp_path / "DHF"


def _call(name: str, dhf: Path):
    fn = getattr(ci_module, name)
    kwargs = {}
    if "offline_mode" in inspect.signature(fn).parameters:
        kwargs["offline_mode"] = "warn"  # keep the network out of the test
    return fn(dhf, **kwargs)


class TestEveryCLIGateHonoursTheContract:
    """All nine, not just the four callable with a bare path.

    An earlier version parametrised only SIMPLE_GATES, so `verify branch` shipped
    with dicts in `errors` and `verify verification` failed with nothing in it —
    both invisible to a test that never called them.
    """

    @staticmethod
    def _commands() -> list[str]:
        from medharness.services.gates import GATES

        return [g["command"] for g in GATES]

    def test_messages_are_strings(self, dhf: Path) -> None:
        offenders = {
            cmd: [m for m in _run_gate(cmd, dhf)["errors"] + _run_gate(cmd, dhf)["warnings"]
                  if not isinstance(m, str)]
            for cmd in self._commands()
        }
        assert not {k: v for k, v in offenders.items() if v}

    def test_a_failing_gate_says_why(self, dhf: Path) -> None:
        silent = [
            cmd for cmd in self._commands()
            if not (r := _run_gate(cmd, dhf))["passed"] and not r["errors"]
        ]
        assert not silent, f"gates failed without explaining: {silent}"

    def test_summary_is_never_empty(self, dhf: Path) -> None:
        blank = [cmd for cmd in self._commands() if not _run_gate(cmd, dhf)["summary"].strip()]
        assert not blank, f"gates with no summary: {blank}"


class TestEnvelopeShape:
    @pytest.mark.parametrize("gate", SIMPLE_GATES)
    def test_top_level_is_exactly_the_envelope(self, gate: str, dhf: Path) -> None:
        assert set(_call(gate, dhf)) == set(ENVELOPE_KEYS)

    @pytest.mark.parametrize("gate", SIMPLE_GATES)
    def test_field_types_are_stable(self, gate: str, dhf: Path) -> None:
        r = _call(gate, dhf)
        assert isinstance(r["gate"], str) and r["gate"]
        assert isinstance(r["passed"], bool)
        assert isinstance(r["summary"], str)
        assert isinstance(r["errors"], list)
        assert isinstance(r["warnings"], list)
        assert isinstance(r["details"], dict)

    @pytest.mark.parametrize("gate", SIMPLE_GATES)
    def test_messages_are_strings(self, gate: str, dhf: Path) -> None:
        """A caller prints these; a nested dict would render as noise."""
        r = _call(gate, dhf)
        assert all(isinstance(m, str) for m in r["errors"] + r["warnings"])

    @pytest.mark.parametrize("gate", SIMPLE_GATES)
    def test_failure_is_explained(self, gate: str, dhf: Path) -> None:
        """A gate that fails must say why, or the caller cannot act."""
        r = _call(gate, dhf)
        if not r["passed"]:
            assert r["errors"], f"{gate} failed with no errors listed"


class TestNoGateEscapesTheEnvelope:
    def test_every_cli_gate_emits_the_envelope(self, dhf: Path) -> None:
        """Discovery through the CLI, not through function names.

        An earlier version of this test enumerated functions named ``*_gate``
        in one module. Three gates — verification, branch, code — are
        implemented elsewhere, so they escaped it and shipped with their own
        shapes. Asking the CLI what commands exist has no such blind spot.
        """
        from medharness.services.gates import GATES

        # Arguments each gate needs to reach its reporting path.
        extra = {
            "tests": ["--junit-dir", str(dhf / "test-results")],
            "completion": ["--cr", "CR-001"],
            "branch": ["--cr", "CR-001"],
            "code": ["--cr", "CR-001"],
        }
        offenders = []
        for gate in GATES:
            name = gate["command"].removeprefix("verify ")
            args = ["--dhf", str(dhf), "verify", name] + extra.get(name, [])
            r = CliRunner().invoke(main, args)
            line = (r.output or "").splitlines()
            try:
                payload = json.loads(line[0])
            except (IndexError, json.JSONDecodeError):
                offenders.append((name, "no JSON on stdout")); continue
            if set(payload) != set(ENVELOPE_KEYS):
                offenders.append((name, sorted(set(payload) ^ set(ENVELOPE_KEYS))))
        assert not offenders, f"gates not emitting the envelope: {offenders}"

    def test_cr_closure_gate_uses_the_envelope(self, dhf: Path) -> None:
        from medharness.services.ci import cr_closure_gate

        result = cr_closure_gate(dhf_path=dhf, cr_id="CR-001", junit_paths=[])
        assert set(result) == set(ENVELOPE_KEYS)

    def test_test_coverage_gate_uses_the_envelope(self, dhf: Path) -> None:
        from medharness.services.ci import ci_test_coverage_gate

        assert set(ci_test_coverage_gate(dhf, [])) == set(ENVELOPE_KEYS)

    def test_test_coverage_gate_envelope_holds_with_evidence(
        self, dhf: Path, tmp_path: Path
    ) -> None:
        """The no-evidence path returns early — cover the normal path too."""
        junit = tmp_path / "r.xml"
        junit.write_text(
            "<testsuites><testsuite name='s' tests='1'>"
            "<testcase classname='t' name='test_x' time='0.1'><properties>"
            "<property name='medharness.id' value='TC-SRS-001'/>"
            "<property name='medharness.links' value='SRS-001'/>"
            "</properties></testcase></testsuite></testsuites>"
        )
        assert set(ci_test_coverage_gate(dhf, [junit])) == set(ENVELOPE_KEYS)


class TestEnvelopeHelper:
    def test_details_absorbs_unknown_keys(self) -> None:
        r = gate_result("verify x", True, "ok", anything=1, else_=2)
        assert r["details"] == {"anything": 1, "else_": 2}

    def test_message_lists_are_copied(self) -> None:
        """A caller mutating the result must not reach back into the gate."""
        errors = ["a"]
        r = gate_result("verify x", False, "bad", errors=errors)
        r["errors"].append("b")
        assert errors == ["a"]

    def test_omitted_message_lists_default_to_empty(self) -> None:
        r = gate_result("verify x", True, "ok")
        assert r["errors"] == [] and r["warnings"] == []


class TestCLIEmitsTheEnvelope:
    """stdout is the machine surface; it must carry the envelope verbatim."""

    @pytest.mark.parametrize("command", ["dhf", "classification", "plans"])
    def test_stdout_first_line_is_the_envelope(self, command: str, dhf: Path) -> None:
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", command])
        payload = json.loads(r.output.splitlines()[0])
        assert set(payload) == set(ENVELOPE_KEYS)

    def test_passed_agrees_with_the_exit_code(self, dhf: Path) -> None:
        for command in ("dhf", "classification", "plans"):
            r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", command])
            payload = json.loads(r.output.splitlines()[0])
            assert (r.exit_code == 0) is payload["passed"], command
