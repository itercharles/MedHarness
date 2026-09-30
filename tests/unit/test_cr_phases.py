"""Tests for CR phases.

``build plan --cr CR-001`` on a freshly scaffolded project once answered
"CR 'CR-001' not found" for the CR the scaffold had just written.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dhfkit.item_store import ItemStore
from medharness.workflows.cr_state import (
    ACTIVE_PHASES,
    TERMINAL_PHASES,
    CRPhase,
    assert_cr_active,
    get_cr_phase,
)
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Trial")
    return tmp_path / "DHF"


class TestCRPhases:
    def test_scaffolded_cr_is_active(self, dhf: Path) -> None:
        """The documented first command must work on a fresh project."""
        assert assert_cr_active(ItemStore(dhf), "CR-001") in ACTIVE_PHASES

    def test_missing_cr_says_not_found(self, dhf: Path) -> None:
        with pytest.raises(ValueError, match="not found"):
            assert_cr_active(ItemStore(dhf), "CR-999")

    def test_absent_status_reads_as_new(self, dhf: Path) -> None:
        cr = dhf / "items" / "07_cr" / "CR-001.yaml"
        cr.write_text(cr.read_text().replace("status: new\n", ""))
        assert get_cr_phase(ItemStore(dhf), "CR-001") is CRPhase.NEW

    def test_rejected_is_terminal_not_missing(self, dhf: Path) -> None:
        """`build plan` triage writes 'rejected'; it was read as 'not found'."""
        cr = dhf / "items" / "07_cr" / "CR-001.yaml"
        cr.write_text(cr.read_text().replace("status: new", "status: rejected"))

        with pytest.raises(ValueError) as exc:
            assert_cr_active(ItemStore(dhf), "CR-001")
        assert "not found" not in str(exc.value)
        assert "rejected" in str(exc.value)

    def test_unrecognised_status_is_reported_as_such(self, dhf: Path) -> None:
        cr = dhf / "items" / "07_cr" / "CR-001.yaml"
        cr.write_text(cr.read_text().replace("status: new", "status: banana"))

        with pytest.raises(ValueError) as exc:
            assert_cr_active(ItemStore(dhf), "CR-001")
        assert "not found" not in str(exc.value)
        assert "banana" in str(exc.value)

    def test_rejected_is_a_terminal_phase(self) -> None:
        assert CRPhase.REJECTED in TERMINAL_PHASES
        assert CRPhase.REJECTED not in ACTIVE_PHASES


