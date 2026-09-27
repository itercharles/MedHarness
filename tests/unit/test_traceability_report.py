"""The traceability matrix and the verification evidence `build release` bundles.

Both are functions of items and item types, so most of these pass values and
need no DHF on disk.
"""

from __future__ import annotations

from pathlib import Path


from medharness.services.traceability_report import (
    traceability_matrix,
    traceability_report,
    verification_evidence,
)

TYPES = [
    {"code": "CRS", "prefix": "CRS-", "has_verification": False},
    {"code": "SYS", "prefix": "SYS-", "has_verification": True},
    {"code": "SRS", "prefix": "SRS-", "has_verification": True},
]


def _item(item_id: str, *links: str) -> dict:
    return {"id": item_id, "title": item_id.lower(), "all_linked_uids": list(links)}


ITEMS = [
    _item("CRS-001"),
    _item("SYS-001", "CRS-001"),
    _item("SYS-002", "CRS-001"),
    _item("SRS-001", "SYS-001"),
    _item("SRS-002", "SYS-001"),
    _item("SRS-009"),
]


def _junit(path: Path, links: str, *, failed: bool = False, skipped: bool = False) -> Path:
    extra = "<failure message='boom'>x</failure>" if failed else ""
    extra += "<skipped/>" if skipped else ""
    path.write_text(
        "<testsuites><testsuite name='s' tests='1'>"
        "<testcase classname='t' name='test_x' time='0.1'>"
        f"<properties><property name='medharness.links' value='{links}'/></properties>"
        f"{extra}</testcase></testsuite></testsuites>"
    )
    return path


class TestTheMatrix:
    def test_one_row_per_chain_with_the_requested_columns(self) -> None:
        m = traceability_matrix(ITEMS, TYPES, ["CRS", "SYS", "SRS"])
        assert m["columns"] == ["CRS", "SYS", "SRS"]
        assert {"CRS", "SYS", "SRS", "is_orphan", "orphan_type", "is_complete"} == set(m["rows"][0])

    def test_a_linked_chain_is_complete(self) -> None:
        rows = traceability_matrix(ITEMS, TYPES, ["CRS", "SYS", "SRS"])["rows"]
        complete = [(r["CRS"], r["SYS"], r["SRS"]) for r in rows if r["is_complete"]]
        assert complete == [("CRS-001", "SYS-001", "SRS-001"), ("CRS-001", "SYS-001", "SRS-002")]

    def test_a_chain_that_stops_early_is_incomplete(self) -> None:
        rows = traceability_matrix(ITEMS, TYPES, ["CRS", "SYS", "SRS"])["rows"]
        [sys2] = [r for r in rows if r["SYS"] == "SYS-002"]
        assert sys2["SRS"] is None and not sys2["is_complete"] and not sys2["is_orphan"]

    def test_an_item_no_chain_reaches_is_an_orphan_row(self) -> None:
        rows = traceability_matrix(ITEMS, TYPES, ["CRS", "SYS", "SRS"])["rows"]
        [orphan] = [r for r in rows if r["SRS"] == "SRS-009"]
        assert orphan == {"CRS": None, "SYS": None, "SRS": "SRS-009",
                          "is_orphan": True, "orphan_type": "SRS", "is_complete": False}

    def test_any_subset_of_types(self) -> None:
        rows = traceability_matrix(ITEMS, TYPES, ["SYS", "SRS"])["rows"]
        assert [(r["SYS"], r["SRS"]) for r in rows if r["is_complete"]] == [
            ("SYS-001", "SRS-001"), ("SYS-001", "SRS-002")]

    def test_types_are_matched_by_configured_prefix_not_by_code(self) -> None:
        types = [{"code": "REQ", "prefix": "R-", "has_verification": False},
                 {"code": "TST", "prefix": "T-VER-", "has_verification": False}]
        rows = traceability_matrix([_item("R-1"), _item("T-VER-1", "R-1")], types,
                                   ["REQ", "TST"])["rows"]
        assert rows == [{"REQ": "R-1", "TST": "T-VER-1", "is_orphan": False,
                         "orphan_type": None, "is_complete": True}]


class TestVerificationRequiresEvidence:
    """Derived from JUnit, never read from the item."""

    def test_a_yaml_claiming_verified_is_not_believed(self) -> None:
        items = [{**_item("SRS-001"), "verification_status": "verified"}]
        assert verification_evidence(items, TYPES)["SRS-001"]["verification_status"] == "not_verified"

    def test_a_linked_passing_test_verifies(self, tmp_path: Path) -> None:
        e = verification_evidence(ITEMS, TYPES, [_junit(tmp_path / "a.xml", "SRS-001")])
        assert e["SRS-001"] == {"verification_status": "verified",
                                "test_cases": [{"name": "t › test_x", "status": "PASS"}]}

    def test_a_linked_failing_test_marks_failed(self, tmp_path: Path) -> None:
        e = verification_evidence(ITEMS, TYPES, [_junit(tmp_path / "a.xml", "SRS-001", failed=True)])
        assert e["SRS-001"]["verification_status"] == "failed"

    def test_a_skipped_test_is_no_evidence(self, tmp_path: Path) -> None:
        e = verification_evidence(ITEMS, TYPES, [_junit(tmp_path / "a.xml", "SRS-001", skipped=True)])
        assert e["SRS-001"]["verification_status"] == "not_verified"

    def test_evidence_for_another_item_verifies_nothing(self, tmp_path: Path) -> None:
        e = verification_evidence(ITEMS, TYPES, [_junit(tmp_path / "a.xml", "SYS-001")])
        assert e["SYS-001"]["verification_status"] == "verified"
        assert e["SRS-001"]["verification_status"] == "not_verified"

    def test_only_verifiable_types_are_reported(self) -> None:
        assert "CRS-001" not in verification_evidence(ITEMS, TYPES)


class TestTheReport:
    def test_rows_carry_the_status_of_their_lowest_verifiable_level(self, tmp_path: Path) -> None:
        report = traceability_report(ITEMS, TYPES, ["CRS", "SYS", "SRS"],
                                     [_junit(tmp_path / "a.xml", "SRS-001")])
        [row] = [r for r in report["rows"] if r["SRS"] == "SRS-001"]
        assert row["level_statuses"] == {"SYS": "not_verified", "SRS": "verified"}
        assert row["verification_status"] == "verified"

    def test_coverage_is_keyed_by_type_code(self) -> None:
        coverage = traceability_report(ITEMS, TYPES, ["CRS", "SYS", "SRS"])["coverage"]
        assert sorted(coverage) == ["SRS", "SYS"]
        assert [c["id"] for c in coverage["SRS"]] == ["SRS-001", "SRS-002", "SRS-009"]


def test_a_real_dhf_resolves_types_by_code() -> None:
    """`list_item_types()` names carry display names; columns are codes."""
    from dhfkit.local_adapter import LocalDHFAdapter
    from dhfkit.tests.fixtures import create_test_dhf, populate_test_dhf_direct

    dhf_path = create_test_dhf()
    populate_test_dhf_direct(dhf_path)
    adapter = LocalDHFAdapter(dhf_path)
    rows = traceability_matrix(adapter.list_items(), adapter.list_item_types(), ["SYS", "SRS"])["rows"]
    assert any(r["SYS"] is not None for r in rows)
