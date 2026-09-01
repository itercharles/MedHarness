"""Tests for IEC 62304 §4.3 software safety classification.

The class is the axis the standard turns on: it decides which development
activities are required at all. Without one, every existing gate can prove that
items are consistent with each other but not that the required ones exist.

Adoption is opt-in — an undeclared class warns and exits zero — so these tests
pin both halves: that a project which has not opted in keeps passing, and that
declaring a class actually activates the checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.models.config import ProjectConfig
from medharness.cli import main
from medharness.services.ci import ENVELOPE_KEYS, classification_gate
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Trial")
    return tmp_path / "DHF"


def _declare(dhf: Path, cls: str, rationale: str = "Assessed under RISK-001.") -> None:
    path = dhf / "config" / "global.yaml"
    text = path.read_text()
    text = text.replace('software_safety_class: ""', f'software_safety_class: "{cls}"')
    text = text.replace('classification_rationale: ""',
                        f'classification_rationale: "{rationale}"')
    path.write_text(text)


def _drop_items(dhf: Path, *dirs: str) -> None:
    import shutil
    for name in dirs:
        shutil.rmtree(dhf / "items" / name, ignore_errors=True)


class TestUndeclaredIsOptIn:
    def test_scaffold_has_no_class_declared(self, dhf: Path) -> None:
        assert not ProjectConfig.load(dhf / "config").software_safety_class

    def test_undeclared_passes_with_a_warning(self, dhf: Path) -> None:
        result = classification_gate(dhf)
        assert result["passed"] is True
        assert result["details"]["declared"] is None
        assert any("§4.3" in w for w in result["warnings"])

    def test_undeclared_exits_zero(self, dhf: Path) -> None:
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "classification"])
        assert r.exit_code == 0, r.output
        assert "WARN [classification]" in r.output

    def test_undeclared_checks_nothing(self, dhf: Path) -> None:
        """No class means no activity requirements, even with items missing."""
        _drop_items(dhf, "05_swdd", "04_modules", "06_sysarch")
        assert classification_gate(dhf)["passed"] is True


class TestDeclaredClassActivatesChecks:
    def test_class_b_passes_on_the_scaffold(self, dhf: Path) -> None:
        _declare(dhf, "B")
        result = classification_gate(dhf)
        assert result["passed"] is True, result["errors"]
        assert result["details"]["declared"] == "B"

    def test_class_c_requires_detailed_design(self, dhf: Path) -> None:
        _declare(dhf, "C")
        _drop_items(dhf, "05_swdd", "04_modules")

        result = classification_gate(dhf)
        assert result["passed"] is False
        missing = {e["code"] for e in result["details"]["missing_item_types"]}
        assert missing == {"SWDD", "MODULE"}

    def test_class_b_does_not_require_detailed_design(self, dhf: Path) -> None:
        """§5.4 is Class C; a Class B project omitting SWDD is not in error."""
        _declare(dhf, "B")
        _drop_items(dhf, "05_swdd")
        assert classification_gate(dhf)["passed"] is True

    def test_class_a_does_not_require_architecture(self, dhf: Path) -> None:
        """§5.3 is Class B and above."""
        _declare(dhf, "A")
        _drop_items(dhf, "06_sysarch", "05_swdd", "04_modules")
        assert classification_gate(dhf)["passed"] is True

    def test_risk_management_is_required_at_every_class(self, dhf: Path) -> None:
        """§7 and ISO 14971 do not scale with the software safety class."""
        for cls in ("A", "B", "C"):
            config = ProjectConfig.load(dhf / "config")
            required = (config.safety_activities["classes"][cls]["required_items"])
            assert "RISK" in required and "RCM" in required

    def test_missing_items_name_the_clause(self, dhf: Path) -> None:
        _declare(dhf, "C")
        _drop_items(dhf, "05_swdd")
        entry = next(e for e in classification_gate(dhf)["details"]["missing_item_types"]
                     if e["code"] == "SWDD")
        assert "5.4" in entry["clause_hint"]


class TestRationaleIsRequired:
    def test_declared_class_without_rationale_fails(self, dhf: Path) -> None:
        _declare(dhf, "B", rationale="")
        result = classification_gate(dhf)
        assert result["passed"] is False
        assert any("rationale" in e for e in result["errors"])

    def test_rationale_present_is_reported(self, dhf: Path) -> None:
        _declare(dhf, "B")
        assert classification_gate(dhf)["details"]["rationale_present"] is True


class TestInvalidClass:
    def test_unknown_class_is_rejected(self, dhf: Path) -> None:
        _declare(dhf, "D")
        result = classification_gate(dhf)
        assert result["passed"] is False
        assert any("expected one of" in e for e in result["errors"])

    def test_lowercase_class_is_accepted(self, dhf: Path) -> None:
        _declare(dhf, "b")
        result = classification_gate(dhf)
        assert result["details"]["declared"] == "B"
        assert result["passed"] is True


class TestModuleOverride:
    """§4.3(b) allows a software item to sit below the system class."""

    def _module(self, dhf: Path, body: str) -> None:
        path = next((dhf / "items" / "04_modules").glob("MODULE-*.yaml"))
        path.write_text(path.read_text().rstrip("\n") + "\n" + body)

    def test_override_without_rationale_warns(self, dhf: Path) -> None:
        _declare(dhf, "C")
        self._module(dhf, "safety_class: A\n")

        result = classification_gate(dhf)
        override = result["details"]["module_overrides"][0]
        assert override["safety_class"] == "A"
        assert override["justified"] is False
        assert any("segregation_rationale" in w for w in result["warnings"])

    def test_override_with_rationale_is_accepted(self, dhf: Path) -> None:
        _declare(dhf, "C")
        self._module(
            dhf,
            "safety_class: A\nsegregation_rationale: Runs in a separate process "
            "with no shared state; see SYSARCH-001.\n",
        )

        result = classification_gate(dhf)
        assert result["details"]["module_overrides"][0]["justified"] is True
        assert not result["warnings"]

    def test_override_never_blocks_the_gate(self, dhf: Path) -> None:
        """The justification may live in the architecture, so this warns only."""
        _declare(dhf, "C")
        self._module(dhf, "safety_class: A\n")
        assert classification_gate(dhf)["passed"] is True


class TestActivityMapIsProjectOwned:
    def test_map_ships_with_the_scaffold(self, dhf: Path) -> None:
        assert (dhf / "config" / "safety_activities.yaml").is_file()

    def test_editing_the_map_changes_what_is_required(self, dhf: Path) -> None:
        """Assessors differ on the §5 table, so the project owns the mapping."""
        _declare(dhf, "A")
        path = dhf / "config" / "safety_activities.yaml"
        path.write_text(
            "classes:\n  A:\n    required_items: [SYSARCH]\n    required_plans: []\n"
            "    required_test_levels: [unit]\n"
        )
        _drop_items(dhf, "06_sysarch")

        result = classification_gate(dhf)
        assert result["passed"] is False
        assert result["details"]["missing_item_types"][0]["code"] == "SYSARCH"

    def test_class_with_no_mapping_warns_rather_than_passing_silently(self, dhf: Path) -> None:
        _declare(dhf, "B")
        (dhf / "config" / "safety_activities.yaml").write_text("classes: {}\n")

        result = classification_gate(dhf)
        assert any("nothing is being checked" in w for w in result["warnings"])


class TestProjectNameReachesDocuments:
    """project_name was read from global.yaml and dropped by ProjectConfig."""

    def test_config_exposes_the_project_name(self, dhf: Path) -> None:
        assert ProjectConfig.load(dhf / "config").project_name == "Trial"

    def test_generated_document_carries_it(self, dhf: Path) -> None:
        from dhfkit.cli import main as dhfkit_main

        CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "doc", "generate", "SRS"])
        text = (dhf / "documents" / "specs"
                / "software_requirement_specification.md").read_text()
        assert "Trial" in text
        assert "DHF Project" not in text


class TestCLIContract:
    def test_outputs_structured_json(self, dhf: Path) -> None:
        _declare(dhf, "B")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "classification"])
        payload = json.loads(r.output.splitlines()[0])
        assert payload["details"]["declared"] == "B"
        assert set(payload) == set(ENVELOPE_KEYS)
        assert "declared" in payload["details"]

    def test_failure_exits_nonzero(self, dhf: Path) -> None:
        _declare(dhf, "C")
        _drop_items(dhf, "05_swdd", "04_modules")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "classification"])
        assert r.exit_code != 0
        assert "FAIL [classification]" in r.output
