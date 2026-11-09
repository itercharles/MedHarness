"""A CR is always in its own change set, and was recorded as affecting itself.

`build plan` writes `affected_risk_items`, `impact_analysis` and
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

from dhfkit.store import open_store
from medharness.services.cr_impact import _record_design_impact_in_cr
from medharness.scaffold import replace_placeholders, scaffold_dhf

LINKS = ("derives_from", "implements", "affected_items")


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "SelfRef")
    return tmp_path / "DHF"


class TestTheCrIsExcludedFromItsOwnImpact:
    def test_a_change_set_containing_the_cr_does_not_record_it(self, dhf: Path) -> None:
        """The real shape: `build plan` updates the CR, so it is in `updated`."""
        assert _record_design_impact_in_cr(
            "CR-001", dhf,
            {"created": ["SRS-020"], "updated": ["CR-001", "SYS-001"], "deleted": []},
        ) is None
        assert open_store(dhf).get_item("CR-001")["affected_items"] == ["SRS-020", "SYS-001"]

    def test_the_stored_item_matches(self, dhf: Path) -> None:
        _record_design_impact_in_cr(
            "CR-001", dhf, {"created": [], "updated": ["CR-001"], "deleted": []},
        )
        assert open_store(dhf).get_item("CR-001")["affected_items"] == []

    def test_other_items_are_still_recorded(self, dhf: Path) -> None:
        """Excluding the CR must not exclude anything else."""
        _record_design_impact_in_cr(
            "CR-001", dhf,
            {"created": ["SRS-020"], "updated": ["SYS-001"], "deleted": ["SWDD-009"]},
        )
        assert open_store(dhf).get_item("CR-001")["affected_items"] == ["SRS-020", "SWDD-009", "SYS-001"]

    def test_another_cr_is_not_excluded(self, dhf: Path) -> None:
        """Only *this* CR. A CR genuinely touching another one still records it."""
        _record_design_impact_in_cr(
            "CR-001", dhf, {"created": [], "updated": ["CR-001", "CR-002"], "deleted": []},
        )
        assert open_store(dhf).get_item("CR-001")["affected_items"] == ["CR-002"]


class TestAnImpactThatCannotBeRecordedSaysWhy:
    def test_a_cr_that_is_not_in_the_dhf(self, dhf: Path) -> None:
        reason = _record_design_impact_in_cr("CR-404", dhf, {"created": ["SRS-020"], "updated": [], "deleted": []})
        assert reason is not None and "CR-404 is not in the DHF" in reason


class TestTheResultPassesTheGateThatCaughtIt:
    """The check that matters: does the recorded impact survive `verify dhf`."""

    def test_no_cycle_is_produced(self, dhf: Path) -> None:
        from dhfkit.item_store import ItemStore
        from medharness.services.traceability import find_link_cycles

        _record_design_impact_in_cr(
            "CR-001", dhf,
            {"created": [], "updated": ["CR-001", "SYS-001"], "deleted": []},
        )
        items = ItemStore(dhf).list_items()
        assert find_link_cycles(items, LINKS) == []

    def test_the_unfixed_shape_would_have_cycled(self, dhf: Path) -> None:
        """Pins why this matters rather than trusting the fix on its own."""
        from medharness.services.traceability import find_link_cycles

        as_written_before = [{"id": "CR-001", "affected_items": ["CR-001", "SYS-001"]},
                             {"id": "SYS-001"}]
        assert find_link_cycles(as_written_before, LINKS) == [["CR-001"]]
