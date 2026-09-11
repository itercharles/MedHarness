"""A CR is always in its own change set, and was recorded as affecting itself.

`change plan` writes `triage_result`, `affected_risk_items` and
`implementation_notes` onto the CR item, so the CR appears among the items
changed on the branch. `_record_design_impact_in_cr` then wrote that whole set
into the CR's own `affected_items` — including the CR.

That is a one-item traceability cycle. It was invisible until 0.20.0 added cycle
detection, at which point **every CR the AI workflow had planned failed the gate
that shipped to catch broken references.** The reference project found it on
CR-012 (`affected_items: [CR-012]`) and CR-013 within minutes of upgrading.

Nothing caught it here because every test of this path fed an empty change set —
`{"created": [], "updated": [], "deleted": []}` — and a CR can only appear in a
change set that is not empty.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import dhfkit.api as api
from medharness.services.cr_impact import _record_design_impact_in_cr
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "SelfRef")
    return tmp_path / "DHF"


class TestTheCrIsExcludedFromItsOwnImpact:
    def test_a_change_set_containing_the_cr_does_not_record_it(self, dhf: Path) -> None:
        """The real shape: `change plan` updates the CR, so it is in `updated`."""
        result = _record_design_impact_in_cr(
            "CR-001", dhf,
            {"created": ["SRS-020"], "updated": ["CR-001", "SYS-001"], "deleted": []},
        )
        assert result["recorded"] is True
        assert "CR-001" not in result["affected_items"]
        assert result["affected_items"] == ["SRS-020", "SYS-001"]

    def test_the_stored_item_matches(self, dhf: Path) -> None:
        _record_design_impact_in_cr(
            "CR-001", dhf, {"created": [], "updated": ["CR-001"], "deleted": []},
        )
        assert api.get_item(dhf, "CR-001")["affected_items"] == []

    def test_other_items_are_still_recorded(self, dhf: Path) -> None:
        """Excluding the CR must not exclude anything else."""
        result = _record_design_impact_in_cr(
            "CR-001", dhf,
            {"created": ["SRS-020"], "updated": ["SYS-001"], "deleted": ["SWDD-009"]},
        )
        assert result["affected_items"] == ["SRS-020", "SWDD-009", "SYS-001"]

    def test_another_cr_is_not_excluded(self, dhf: Path) -> None:
        """Only *this* CR. A CR genuinely touching another one still records it."""
        result = _record_design_impact_in_cr(
            "CR-001", dhf, {"created": [], "updated": ["CR-001", "CR-002"], "deleted": []},
        )
        assert result["affected_items"] == ["CR-002"]


class TestTheResultPassesTheGateThatCaughtIt:
    """The check that matters: does the recorded impact survive `verify dhf`."""

    def test_no_cycle_is_produced(self, dhf: Path) -> None:
        from dhfkit.local_adapter import LocalDHFAdapter
        from medharness.services.traceability import find_link_cycles

        _record_design_impact_in_cr(
            "CR-001", dhf,
            {"created": [], "updated": ["CR-001", "SYS-001"], "deleted": []},
        )
        items = LocalDHFAdapter(dhf).list_items()
        assert find_link_cycles(items) == []

    def test_the_unfixed_shape_would_have_cycled(self, dhf: Path) -> None:
        """Pins why this matters rather than trusting the fix on its own."""
        from medharness.services.traceability import find_link_cycles

        as_written_before = [{"id": "CR-001", "affected_items": ["CR-001", "SYS-001"]},
                             {"id": "SYS-001"}]
        assert find_link_cycles(as_written_before) == [["CR-001"]]


class TestTheSuiteExercisesANonEmptyChangeSet:
    """Why this shipped: the tests only ever ran the empty case.

    Of the mocks standing in for `collect_dhf_item_changes`, twenty returned
    `{"created": [], "updated": [], "deleted": []}`. A CR can only appear in its
    own change set when that set is not empty, so the defect lived in the shape
    no test supplied — the same failure mode as `verify branch` shipping a
    TypeError behind mocks that fed the pre-envelope shape.

    This does not demand every mock change. It demands that *some* test drive
    the path with a change set containing the CR, which is what the class above
    does.
    """

    def _mocked_shapes(self) -> list[bool]:
        import ast

        empties = []
        for path in sorted(Path(__file__).resolve().parents[2].joinpath("tests").rglob("test_*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "patch"):
                    continue
                if not (node.args and isinstance(node.args[0], ast.Constant)):
                    continue
                if "collect_dhf_item_changes" not in str(node.args[0].value):
                    continue
                value = next((k.value for k in node.keywords if k.arg == "return_value"), None)
                try:
                    parsed = ast.literal_eval(value) if value is not None else None
                except (ValueError, SyntaxError):
                    continue
                if isinstance(parsed, dict):
                    empties.append(all(not parsed.get(b) for b in
                                       ("created", "updated", "deleted")))
        return empties

    def test_the_scan_found_the_mocks(self) -> None:
        assert len(self._mocked_shapes()) > 10, "the scan is broken"

    def test_not_every_change_set_in_the_suite_is_empty(self) -> None:
        shapes = self._mocked_shapes()
        non_empty = shapes.count(False)
        assert non_empty >= 3, (
            f"{shapes.count(True)} of {len(shapes)} change-set mocks are empty and "
            f"only {non_empty} are not. A CR appears in its own change set only "
            f"when that set is populated — the case this file exists for."
        )
