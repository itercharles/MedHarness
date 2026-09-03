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
import re
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
    """Run a gate in a real subprocess.

    Deliberately not CliRunner: it captures an exception raised *after* the JSON
    line is written, so a command that prints its result and then crashes looks
    identical to one that succeeded. Two crashes shipped behind exactly that —
    `verify plans` on a missing plan and `verify branch` on any failure.
    """
    import subprocess
    import sys

    args = [sys.executable, "-m", "medharness", "--dhf", str(dhf), *command.split()]
    args += [a.format(dhf=dhf) for a in GATE_ARGS.get(command, [])]
    proc = subprocess.run(args, capture_output=True, text=True)
    assert "Traceback" not in proc.stderr, (
        f"{command} crashed:\n{proc.stderr[-600:]}"
    )
    lines = proc.stdout.splitlines()
    assert lines, f"{command} wrote no JSON to stdout:\n{proc.stderr[-400:]}"
    return json.loads(lines[0])


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


@pytest.fixture
def failing_dhf(tmp_path: Path) -> Path:
    """A DHF broken in the way each gate's failure path needs.

    The clean-scaffold fixture reaches only the happy paths — soup
    short-circuits on "none checkable", plans skips everything without a class,
    and branch has nothing to compare. Every crash found in review lived on a
    failure path, so the contract has to be checked there too.
    """
    import subprocess

    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Broken")
    dhf = tmp_path / "DHF"

    config = dhf / "config" / "global.yaml"
    config.write_text(
        config.read_text()
        .replace('software_safety_class: ""', 'software_safety_class: "B"')
        .replace('classification_rationale: ""', 'classification_rationale: "Assessed."')
    )
    # A required plan that is absent, not merely unwritten.
    (dhf / "documents" / "plans" / "integration_plan.md").unlink(missing_ok=True)
    # A link that resolves to nothing.
    rcm = next((dhf / "items").rglob("RCM-*.yaml"))
    rcm.write_text(rcm.read_text().replace("RISK-001", "RISK-404"))

    # Real JUnit evidence, so `verify tests` reaches its row-rendering path.
    # Without it `results` is empty, the envelope backstop fires, and a warning
    # that only the row path can drop looks reported — which is how a gate-level
    # warning ("levels are not being checked") stayed off stderr.
    results = dhf / "test-results"
    results.mkdir(exist_ok=True)
    req = next((i.stem for i in (dhf / "items").rglob("SRS-*.yaml")), "SRS-001")
    (results / "j.xml").write_text(
        '<testsuites><testsuite name="s" tests="1" failures="0" errors="0">'
        '<testcase classname="t" name="a"><properties>'
        f'<property name="medharness.links" value="{req}"/>'
        '<property name="medharness.level" value="unit"/>'
        "</properties></testcase></testsuite></testsuites>"
    )

    for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.email=t@e", "-c",
                "user.name=t", "commit", "-qm", "base"]):
        subprocess.run(["git", *cmd], cwd=tmp_path, capture_output=True)
    return dhf


class TestFailurePathsHonourTheContract:
    """Where the crashes were.

    Every defect the review found sat on a path the clean-scaffold tests never
    reached: a missing plan, a branch with no changes, a coverage pair that
    fails. A contract checked only on success is not checked.
    """

    FAILING = ("verify dhf", "verify plans", "verify classification",
               "verify verification", "verify completion", "verify branch")

    @pytest.mark.parametrize("command", FAILING)
    def test_no_crash_on_the_failure_path(self, command: str, failing_dhf: Path) -> None:
        _run_gate(command, failing_dhf)  # asserts no traceback, JSON present

    @pytest.mark.parametrize("command", FAILING)
    def test_a_failing_gate_still_explains_itself(self, command: str, failing_dhf: Path) -> None:
        result = _run_gate(command, failing_dhf)
        if not result["passed"]:
            assert result["errors"], f"{command} failed with empty errors"

    def test_explicit_coverage_pair_failure_is_reported(self, failing_dhf: Path) -> None:
        """--coverage-pair results live under their own key and were skipped."""
        from medharness.services.ci import ci_structural_gate

        r = ci_structural_gate(failing_dhf, coverage_pairs=("NOPE:CRS",))
        assert r["passed"] is False
        assert r["errors"], "an explicit coverage pair failed with nothing in errors"

    def test_soup_reports_real_vulnerabilities(self, dhf: Path) -> None:
        """The scaffold has nothing checkable, so the finding path needs a stub."""
        from unittest.mock import MagicMock, patch

        from medharness.services.ci import soup_vuln_gate

        soup = dhf / "items" / "09_soup"
        soup.mkdir(parents=True, exist_ok=True)
        (soup / "SOUP-900.yaml").write_text(
            "id: SOUP-900\ntitle: requests\nname: requests\n"
            "version: '2.6.0'\necosystem: PyPI\n"
        )
        with patch("urllib.request.urlopen") as opened:
            opened.return_value.__enter__ = lambda s: s
            opened.return_value.__exit__ = MagicMock(return_value=False)
            opened.return_value.read.return_value = json.dumps(
                {"results": [{"vulns": [{"id": "GHSA-x", "modified": "2024-01-01"}]}]}
            ).encode()
            result = soup_vuln_gate(dhf)

        assert result["passed"] is False
        assert result["errors"], "vulnerable SOUP reported with empty errors"


def _stderr_of(command: str, dhf: Path) -> tuple[dict, str]:
    """Run a gate and return both halves of what it told the world."""
    import subprocess
    import sys

    args = [sys.executable, "-m", "medharness", "--dhf", str(dhf), *command.split()]
    args += [a.format(dhf=dhf) for a in GATE_ARGS.get(command, [])]
    proc = subprocess.run(args, capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    assert lines, f"{command} wrote no JSON:\n{proc.stderr[-400:]}"
    return json.loads(lines[0]), proc.stderr


#: What a finding is *about* — an item ID, a file, a package. stderr may phrase
#: the rest however it likes, but it cannot omit these and still be actionable.
IDENTIFIER = re.compile(r"[A-Z]{2,}-\d+[\w.]*|[\w-]+\.(?:md|ya?ml)|[\w-]+@[\w.]+")


def _normalise(text: str) -> str:
    return text.replace("\u2192", "->").replace("\u2014", "-")


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w./@-]+", _normalise(text)) if len(w) > 3]


class TestStderrCarriesTheEnvelope:
    """stdout is the contract; stderr is what a person reads in a CI log.

    A finding the gate computed, put in the envelope, and never printed is
    invisible to everyone not parsing JSON. `verify tests` failed on a missing
    --junit-dir with "Test coverage gaps found." — naming the wrong cause — and
    `verify dhf` never showed its verification_criteria warnings at all.
    """

    ALL = ("verify dhf", "verify tests", "verify classification", "verify plans",
           "verify verification", "verify completion", "verify branch", "verify code")

    @pytest.mark.parametrize("command", ALL)
    def test_stderr_reports_the_envelope(self, command: str, failing_dhf: Path) -> None:
        result, stderr = _stderr_of(command, failing_dhf)
        normalised = _normalise(stderr)
        for message in result["errors"] + result["warnings"]:
            names = set(IDENTIFIER.findall(_normalise(message)))
            if names:
                # A finding about something nameable: stderr must name it.
                missing = sorted(n for n in names if n not in normalised)
                assert not missing, (
                    f"{command}: stderr never mentions {missing} from:\n"
                    f"  {message}\n  stderr was:\n{stderr[-500:]}"
                )
                continue
            # Nothing to name — fall back to overlap, which is what caught
            # "No JUnit files found" being reported as a coverage gap.
            words = _words(message)
            if not words:
                continue
            hit = sum(1 for w in words if w in normalised)
            assert hit / len(words) >= 0.6, (
                f"{command}: envelope message never reached stderr:\n"
                f"  {message}\n  stderr was:\n{stderr[-500:]}"
            )

    @pytest.mark.parametrize("command", ALL)
    def test_no_finding_is_printed_twice(self, command: str, failing_dhf: Path) -> None:
        _, stderr = _stderr_of(command, failing_dhf)
        lines = [line for line in stderr.splitlines() if line.strip()]
        duplicated = {line for line in lines if lines.count(line) > 1}
        assert not duplicated, (
            f"{command} printed the same line twice — two renderers over one "
            f"finding:\n  " + "\n  ".join(sorted(duplicated))
        )

    def test_soup_prints_each_vulnerability_once(self, dhf: Path) -> None:
        """The generic duplication check cannot reach here.

        `failing_dhf` has no checkable SOUP, so the gate short-circuits and its
        rendering path is never exercised — which is why the double-print (one
        line from `_render_envelope`, an identical one from a manual loop beside
        it) survived a suite that already checked every other gate for it.
        """
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        soup = dhf / "items" / "09_soup"
        soup.mkdir(parents=True, exist_ok=True)
        (soup / "SOUP-900.yaml").write_text(
            "id: SOUP-900\ntitle: requests\nname: requests\n"
            "version: '2.6.0'\necosystem: PyPI\n"
        )

        def _osv(*_a, **_k):
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.read.return_value = json.dumps(
                {"results": [{"vulns": [{"id": "GHSA-x", "modified": "2024-01-01"}]}],
                 "id": "GHSA-x", "summary": "Session fixation"}
            ).encode()
            return resp

        with patch("urllib.request.urlopen", side_effect=_osv):
            r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "soup"])

        lines = [line for line in r.stderr.splitlines() if "GHSA-x" in line]
        assert len(lines) == 1, f"vulnerability reported {len(lines)}x:\n" + "\n".join(lines)
        assert "Session fixation" in lines[0], "the reader lost the summary"


class TestGateLevelWarningsReachStderr:
    """A warning about the gate, not about a row, had nowhere to be printed.

    `verify tests` renders per-type rows and — since an earlier fix — the
    envelope when there are no rows at all. A warning that applies to the whole
    gate while rows exist fell between the two: it was in the JSON and absent
    from the log. `failing_dhf` cannot catch it, because it declares a class and
    so never produces one.
    """

    @pytest.fixture
    def inert_dhf(self, tmp_path: Path) -> Path:
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Inert")
        dhf = tmp_path / "DHF"
        results = dhf / "test-results"
        results.mkdir(exist_ok=True)
        req = next((i.stem for i in (dhf / "items").rglob("SRS-*.yaml")), "SRS-001")
        (results / "j.xml").write_text(
            '<testsuites><testsuite name="s" tests="1" failures="0" errors="0">'
            '<testcase classname="t" name="a"><properties>'
            f'<property name="medharness.links" value="{req}"/>'
            '<property name="medharness.level" value="unit"/>'
            "</properties></testcase></testsuite></testsuites>"
        )
        return dhf

    def test_the_reason_levels_are_inert_is_printed(self, inert_dhf: Path) -> None:
        result, stderr = _stderr_of("verify tests", inert_dhf)

        gate_level = [
            w for w in result["warnings"]
            if not any(w == row.get("warning") for row in result["details"]["results"])
        ]
        assert gate_level, "no class is declared, so the gate should say levels are inert"
        assert result["details"]["results"], "the fixture must produce rows to be meaningful"
        for message in gate_level:
            assert "software_safety_class" in stderr, (
                f"a gate-level warning stayed out of the log:\n  {message}\n"
                f"  stderr was:\n{stderr[-400:]}"
            )
