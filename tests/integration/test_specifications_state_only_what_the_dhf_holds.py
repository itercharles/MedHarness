"""A generated specification says what the items hold, and invents nothing.

The templates counted `approved`/`draft`/`retired` items, though no requirement
type has a lifecycle, so every document reported zero of each and an approval rate
of 0%. They listed a requirement's links from a field that does not exist, so the
traceability they promised never appeared, and the CR specification summarised
statuses no CR can have.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dhfkit.store import open_store
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def store(tmp_path: Path):
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Specs")
    return open_store(tmp_path / "DHF")


def _render(store, code: str) -> str:
    return store._generator().render_markdown_spec(code, store._doc_specs, "1.0")


def test_no_specification_reports_states_its_items_cannot_have(store) -> None:
    for code in store.get_available_doc_types():
        md = _render(store, code)
        for invented in ("Retired", "Approval Rate", "Document Owner", "Next Review", "UNKNOWN"):
            assert invented not in md, f"{code} specification says {invented!r}"


def test_a_requirement_lists_the_items_it_links_to(store) -> None:
    md = _render(store, "SRS")
    assert "#### Linked Items" in md and "- SYS-001" in md


def test_the_cr_specification_summarises_the_statuses_the_crs_have(store) -> None:
    md = _render(store, "CR")
    assert "- **NEW**: 1 change request(s)" in md
    assert "| Status | Draft |" in md
