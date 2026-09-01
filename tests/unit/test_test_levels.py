"""Tests for verification-level evidence (IEC 62304 §5.6, §5.7).

`verify tests` mapped JUnit results to requirements without regard for whether
they came from unit, integration, or system testing. The standard asks for
integration (§5.6) and system testing (§5.7) as distinct records, so a project
running only unit tests showed every requirement verified.

The level travels with the evidence as a JUnit property rather than being
inferred from a directory, so it survives the CI boundary — a results file
copied between jobs keeps saying what it is.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from dhfkit.junit_parser import DEFAULT_TEST_LEVEL, TEST_LEVELS
from medharness.services.ci import ci_test_coverage_gate
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Trial")
    return tmp_path / "DHF"


def _declare(dhf: Path, cls: str) -> None:
    path = dhf / "config" / "global.yaml"
    text = path.read_text()
    text = text.replace('software_safety_class: ""', f'software_safety_class: "{cls}"')
    text = text.replace('classification_rationale: ""',
                        'classification_rationale: "Assessed under RISK-001."')
    path.write_text(text)


def _junit(path: Path, req: str, level: str | None, tc_suffix: str = "") -> Path:
    level_prop = (
        f'<property name="medharness.level" value="{level}"/>' if level else ""
    )
    path.write_text(
        f"<testsuites><testsuite name='s' tests='1'>"
        f"<testcase classname='t' name='test_{req}{tc_suffix}' time='0.1'>"
        f"<properties>"
        f'<property name="medharness.id" value="TC-{req}{tc_suffix}"/>'
        f'<property name="medharness.links" value="{req}"/>'
        f"{level_prop}"
        f"</properties></testcase></testsuite></testsuites>"
    )
    return path


class TestInertWithoutAClass:
    def test_levels_do_not_gate_an_unclassified_project(self, dhf: Path, tmp_path: Path) -> None:
        """A project that has not opted in sees exactly its previous behaviour."""
        junit = _junit(tmp_path / "u.xml", "SRS-001", "unit")
        result = ci_test_coverage_gate(dhf, [junit], req_types=("SRS",))

        assert result["details"]["required_levels"] == []
        assert result["details"]["level_gaps"] == []
        assert result["details"]["results"][0]["passed"] is True

    def test_level_is_still_recorded_when_not_gated(self, dhf: Path, tmp_path: Path) -> None:
        junit = _junit(tmp_path / "i.xml", "SRS-001", "integration")
        result = ci_test_coverage_gate(dhf, [junit], req_types=("SRS",))
        assert result["details"]["levels_seen"] == ["integration"]


class TestClassRequiresLevels:
    def test_unit_only_evidence_fails_class_b(self, dhf: Path, tmp_path: Path) -> None:
        """This is the defect: unit tests alone marked everything verified."""
        _declare(dhf, "B")
        junit = _junit(tmp_path / "u.xml", "SRS-001", "unit")

        result = ci_test_coverage_gate(dhf, [junit], req_types=("SRS",))

        assert result["passed"] is False
        gap = result["details"]["level_gaps"][0]
        assert gap["req_id"] == "SRS-001"
        assert gap["have"] == ["unit"]
        assert set(gap["missing"]) == {"integration", "system"}

    def test_all_levels_present_passes(self, dhf: Path, tmp_path: Path) -> None:
        _declare(dhf, "B")
        junits = [
            _junit(tmp_path / f"{lvl}.xml", "SRS-001", lvl, tc_suffix=f"-{lvl}")
            for lvl in ("unit", "integration", "system")
        ]

        result = ci_test_coverage_gate(dhf, junits, req_types=("SRS",))
        assert result["details"]["level_gaps"] == []

    def test_class_a_requires_unit_only(self, dhf: Path, tmp_path: Path) -> None:
        _declare(dhf, "A")
        junit = _junit(tmp_path / "u.xml", "SRS-001", "unit")

        result = ci_test_coverage_gate(dhf, [junit], req_types=("SRS",))
        assert result["details"]["required_levels"] == ["unit"]
        assert result["details"]["level_gaps"] == []

    def test_gap_names_what_is_missing(self, dhf: Path, tmp_path: Path) -> None:
        _declare(dhf, "C")
        junit = _junit(tmp_path / "u.xml", "SRS-001", "integration")

        gap = ci_test_coverage_gate(dhf, [junit], req_types=("SRS",))["details"]["level_gaps"][0]
        assert "unit" in gap["missing"]
        assert "system" in gap["missing"]
        assert gap["have"] == ["integration"]


class TestUnlabelledIsUnit:
    def test_evidence_without_a_level_counts_as_unit(self, dhf: Path, tmp_path: Path) -> None:
        """Existing suites keep working — this is what they already were."""
        _declare(dhf, "A")
        junit = _junit(tmp_path / "plain.xml", "SRS-001", None)

        result = ci_test_coverage_gate(dhf, [junit], req_types=("SRS",))
        assert result["details"]["levels_seen"] == [DEFAULT_TEST_LEVEL]
        assert result["details"]["level_gaps"] == []

    def test_unrecognised_level_falls_back_to_unit(self, dhf: Path, tmp_path: Path) -> None:
        _declare(dhf, "A")
        junit = _junit(tmp_path / "odd.xml", "SRS-001", "smoke")

        result = ci_test_coverage_gate(dhf, [junit], req_types=("SRS",))
        assert result["details"]["levels_seen"] == ["unit"]


class TestPytestMarker:
    """The marker is the authoring surface; a property nobody can emit is useless."""

    def _run(self, tmp_path: Path, body: str) -> tuple[int, str, Path]:
        test_file = tmp_path / "test_marked.py"
        test_file.write_text(body)
        junit = tmp_path / "out.xml"
        # No -p flag: dhfkit registers the plugin as a pytest11 entry point, so
        # loading it explicitly registers it twice and pytest refuses. Relying on
        # the entry point also means this exercises the path a real user gets.
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q",
             f"--junit-xml={junit}"],
            capture_output=True, text=True, cwd=tmp_path,
        )
        return proc.returncode, proc.stdout + proc.stderr, junit

    def test_marker_writes_the_property(self, tmp_path: Path) -> None:
        code, output, junit = self._run(tmp_path, (
            "import pytest\n"
            '@pytest.mark.dhf_links("SRS-001")\n'
            '@pytest.mark.dhf_level("integration")\n'
            "def test_x(): assert True\n"
        ))
        assert code == 0, output
        assert 'name="medharness.level" value="integration"' in junit.read_text()

    def test_unmarked_test_writes_no_level(self, tmp_path: Path) -> None:
        _, _, junit = self._run(tmp_path, (
            "import pytest\n"
            '@pytest.mark.dhf_links("SRS-001")\n'
            "def test_x(): assert True\n"
        ))
        assert "medharness.level" not in junit.read_text()

    def test_invalid_level_fails_loudly(self, tmp_path: Path) -> None:
        """A typo must not silently record the wrong verification level."""
        code, output, _ = self._run(tmp_path, (
            "import pytest\n"
            '@pytest.mark.dhf_links("SRS-001")\n'
            '@pytest.mark.dhf_level("smoke")\n'
            "def test_x(): assert True\n"
        ))
        assert code != 0
        assert "dhf_level must be one of unit, integration, system" in output

    @pytest.mark.parametrize("level", TEST_LEVELS)
    def test_every_modelled_level_is_accepted(self, tmp_path: Path, level: str) -> None:
        code, output, junit = self._run(tmp_path, (
            "import pytest\n"
            '@pytest.mark.dhf_links("SRS-001")\n'
            f'@pytest.mark.dhf_level("{level}")\n'
            "def test_x(): assert True\n"
        ))
        assert code == 0, output
        assert f'value="{level}"' in junit.read_text()
