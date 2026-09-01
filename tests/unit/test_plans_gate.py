"""Tests for plan completeness (IEC 62304 §5.1).

The scaffold ships seven plans as templates and nothing verified any of them was
ever filled in — a DHF of untouched placeholders passed every gate.

Detection compares each plan against the template it came from, section by
section, rather than looking for marker text. Only one of the seven templates
carries a "starter content" banner, so a marker check would miss six of them,
and removing a banner is not the same as writing a plan.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.services.ci import ENVELOPE_KEYS, _sections, plans_gate
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

WRITTEN_PLAN = """# Verification Plan

## 1. Objective
Verify every SRS item has an automated test exercising it, with traceability
from requirement to test intact.

## 2. Scope
Unit and integration verification of the reporting subsystem.

## 3. Methods
Annotated pytest suites executed on every pull request.
"""


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


def _write(dhf: Path, stem: str, content: str = WRITTEN_PLAN) -> None:
    (dhf / "documents" / "plans" / f"{stem}.md").write_text(content)


class TestInactiveUntilClassed:
    def test_undeclared_class_checks_nothing(self, dhf: Path) -> None:
        result = plans_gate(dhf)
        assert result["passed"] is True
        assert result["details"]["checked"] == []
        assert any("no plans are required" in w for w in result["warnings"])

    def test_undeclared_exits_zero(self, dhf: Path) -> None:
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "plans"])
        assert r.exit_code == 0, r.output


class TestUnwrittenPlansFail:
    def test_scaffold_plans_are_recognised_as_templates(self, dhf: Path) -> None:
        """This is the defect: untouched placeholders passed every gate."""
        _declare(dhf, "B")
        result = plans_gate(dhf)

        assert result["passed"] is False
        assert {e["plan"] for e in result["details"]["unwritten"]} >= {
            "development_plan.md", "risk_management_plan.md",
        }

    def test_plans_without_a_banner_are_still_detected(self, dhf: Path) -> None:
        """Only development_plan.md carries starter-content text.

        The other six templates read like finished plans, so a marker-based
        check would miss every one of them. This is why detection compares
        against the template rather than looking for a banner.
        """
        _declare(dhf, "B")
        banner_free = ("risk_management_plan.md", "integration_plan.md",
                       "configuration_management_plan.md", "verification_plan.md")
        for name in banner_free:
            text = (dhf / "documents" / "plans" / name).read_text()
            assert "Starter Content" not in text, f"{name} unexpectedly has a banner"

        unwritten = {e["plan"] for e in plans_gate(dhf)["details"]["unwritten"]}
        assert set(banner_free) <= unwritten

    def test_deleting_the_banner_block_does_not_launder_a_plan(self, dhf: Path) -> None:
        """Removing boilerplate is housekeeping, not authorship."""
        _declare(dhf, "B")
        plan = dhf / "documents" / "plans" / "development_plan.md"
        kept = [
            line for line in plan.read_text().split("\n")
            if not any(m in line for m in
                       ("Starter Content", "scaffolded by MedHarness",
                        "Template — adapt", "below with your project",
                        "and release model before using"))
        ]
        plan.write_text("\n".join(kept))

        unwritten = {e["plan"] for e in plans_gate(dhf)["details"]["unwritten"]}
        assert "development_plan.md" in unwritten

    def test_editing_only_the_front_matter_does_not_launder_a_plan(self, dhf: Path) -> None:
        """Front matter is the document's own header, not the plan.

        Comparison starts at level-2 headings, so rewording a title block —
        deliberately or while tidying boilerplate — cannot make an unwritten
        plan read as written. §5.1 asks for a maintained plan, and the plan is
        its sections.
        """
        _declare(dhf, "B")
        plan = dhf / "documents" / "plans" / "development_plan.md"
        text = plan.read_text()
        for marker in ("Starter Content", "scaffolded by MedHarness", "Replace"):
            text = text.replace(marker, "")
        plan.write_text(text)

        unwritten = {e["plan"] for e in plans_gate(dhf)["details"]["unwritten"]}
        assert "development_plan.md" in unwritten

    def test_missing_required_plan_fails(self, dhf: Path) -> None:
        _declare(dhf, "B")
        (dhf / "documents" / "plans" / "integration_plan.md").unlink()

        result = plans_gate(dhf)
        assert {e["plan"] for e in result["details"]["missing"]} == {"integration_plan.md"}
        assert any("absent" in e for e in result["errors"])


class TestWrittenPlansPass:
    def test_rewritten_plan_passes(self, dhf: Path) -> None:
        _declare(dhf, "B")
        _write(dhf, "verification_plan")

        checked = {e["plan"] for e in plans_gate(dhf)["details"]["checked"]}
        assert "verification_plan.md" in checked

    def test_all_written_passes_the_gate(self, dhf: Path) -> None:
        _declare(dhf, "B")
        for stem in ("development_plan", "risk_management_plan",
                     "configuration_management_plan", "verification_plan",
                     "integration_plan"):
            _write(dhf, stem)

        result = plans_gate(dhf)
        assert result["passed"] is True, result["errors"]
        assert len(result["details"]["checked"]) == 5


class TestPartialIsAWarning:
    def test_one_edited_section_warns_rather_than_failing(self, dhf: Path) -> None:
        """A project may legitimately accept some shipped wording."""
        _declare(dhf, "B")
        plan = dhf / "documents" / "plans" / "integration_plan.md"
        lines = plan.read_text().split("\n")
        for index, line in enumerate(lines):
            if line.startswith("## "):
                lines[index + 1:index + 3] = ["Integration runs on every merge.", ""]
                break
        plan.write_text("\n".join(lines))

        result = plans_gate(dhf)
        partial = {e["plan"] for e in result["details"]["partial"]}
        unwritten = {e["plan"] for e in result["details"]["unwritten"]}
        assert "integration_plan.md" in partial
        assert "integration_plan.md" not in unwritten
        assert any("integration_plan.md" in w for w in result["warnings"])


class TestClassScoping:
    def test_class_b_skips_plans_it_does_not_require(self, dhf: Path) -> None:
        _declare(dhf, "B")
        skipped = {e["plan"] for e in plans_gate(dhf)["details"]["skipped"]}
        assert "maintenance_plan.md" in skipped
        assert "validation_plan.md" in skipped

    def test_class_c_requires_more(self, dhf: Path) -> None:
        _declare(dhf, "C")
        required = {e["plan"] for e in plans_gate(dhf)["details"]["unwritten"]}
        assert "maintenance_plan.md" in required
        assert "validation_plan.md" in required

    def test_class_a_requires_fewest(self, dhf: Path) -> None:
        _declare(dhf, "A")
        result = plans_gate(dhf)
        required = {e["plan"] for e in result["details"]["unwritten"]} | {
            e["plan"] for e in result["details"]["checked"]
        }
        assert "verification_plan.md" not in required
        assert "development_plan.md" in required


class TestSectionSplitting:
    def test_splits_on_headings(self) -> None:
        sections = _sections("# T\n\nintro\n\n## One\nbody one\n\n## Two\nbody two\n")
        assert sections["One"] == "body one"
        assert sections["Two"] == "body two"

    def test_empty_document_has_no_sections(self) -> None:
        assert _sections("") == {}

    def test_body_free_heading_is_captured_as_empty(self) -> None:
        assert _sections("## Heading\n\n## Next\nbody\n")["Heading"] == ""


class TestCLIContract:
    def test_outputs_structured_json(self, dhf: Path) -> None:
        _declare(dhf, "B")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "plans"])
        payload = json.loads(r.output.splitlines()[0])
        assert set(payload) == set(ENVELOPE_KEYS)
        assert set(payload["details"]) >= {"declared", "checked", "missing",
                                           "unwritten", "partial", "skipped"}

    def test_failure_exits_nonzero(self, dhf: Path) -> None:
        _declare(dhf, "B")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "plans"])
        assert r.exit_code != 0
        assert "FAIL [plan]" in r.output
