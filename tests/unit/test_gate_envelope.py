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
    def test_every_gate_in_the_module_is_covered(self) -> None:
        """Guards the next gate, not just today's.

        A gate added without the envelope is caught here rather than by a
        caller discovering its parser does not fit.
        """
        found = {
            name for name, obj in vars(ci_module).items()
            if name.endswith("_gate") and inspect.isfunction(obj)
            and not name.startswith("_")
        }
        # Two gates take more than a DHF path and are exercised separately below.
        assert found - {"cr_closure_gate", "ci_test_coverage_gate"} == set(SIMPLE_GATES), (
            f"gate set changed: {found}. Add it to SIMPLE_GATES or give it its "
            f"own envelope test."
        )

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
