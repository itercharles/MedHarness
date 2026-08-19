"""Tests for dangling traceability link detection.

A dangling link is a link whose target ID does not exist in the DHF. It is a
distinct failure from an uncovered item: the author wrote a link, it just
resolves to nothing. Before this check existed, a typo surfaced only as a
downstream coverage gap — with remediation advice ("add a link") that did not
apply, because the link was already there.
"""

import json

from click.testing import CliRunner

from dhfkit.cli import main
from dhfkit.traceability import find_dangling_links


# ---------------------------------------------------------------------------
# find_dangling_links
# ---------------------------------------------------------------------------

class TestFindDanglingLinks:
    def test_clean_items_have_none(self) -> None:
        items = [
            {"id": "SYS-001"},
            {"id": "SRS-001", "derives_from": ["SYS-001"]},
        ]
        assert find_dangling_links(items) == []

    def test_detects_missing_target(self) -> None:
        items = [
            {"id": "SYS-001"},
            {"id": "SRS-001", "derives_from": ["SYS-999"]},
        ]
        assert find_dangling_links(items) == [
            {"source": "SRS-001", "field": "derives_from", "target": "SYS-999"},
        ]

    def test_checks_every_link_field(self) -> None:
        items = [
            {"id": "RCM-001", "mitigates": ["RISK-404"], "implements": ["SYS-404"]},
            {"id": "TC-001", "verifies": ["SRS-404"]},
        ]
        found = {(d["field"], d["target"]) for d in find_dangling_links(items)}
        assert found == {
            ("mitigates", "RISK-404"),
            ("implements", "SYS-404"),
            ("verifies", "SRS-404"),
        }

    def test_partial_link_list_reports_only_bad_entry(self) -> None:
        items = [
            {"id": "SYS-001"},
            {"id": "SRS-001", "derives_from": ["SYS-001", "SYS-999"]},
        ]
        dangling = find_dangling_links(items)
        assert len(dangling) == 1
        assert dangling[0]["target"] == "SYS-999"

    def test_empty_and_missing_fields_are_safe(self) -> None:
        items = [
            {"id": "SYS-001", "derives_from": [], "mitigates": None},
            {"id": "SYS-002"},
        ]
        assert find_dangling_links(items) == []

    def test_output_is_sorted(self) -> None:
        items = [
            {"id": "SRS-002", "derives_from": ["ZZZ-1"]},
            {"id": "SRS-001", "derives_from": ["ZZZ-2"]},
        ]
        assert [d["source"] for d in find_dangling_links(items)] == ["SRS-001", "SRS-002"]


# ---------------------------------------------------------------------------
# CLI behaviour
# ---------------------------------------------------------------------------

def _break_link(dhf, item_glob: str, old: str, new: str) -> None:
    matches = list((dhf / "items").rglob(item_glob))
    assert matches, f"no item matched {item_glob}"
    path = matches[0]
    text = path.read_text()
    assert old in text, f"{old} not found in {path.name}"
    path.write_text(text.replace(old, new))


class TestValidateTraceabilityCLI:
    def test_dangling_link_exits_nonzero(self, populated_dhf) -> None:
        _break_link(populated_dhf, "SRS-*.yaml", "SYS-", "SYS-DOES-NOT-EXIST-")
        r = CliRunner().invoke(main, ["--dhf", str(populated_dhf), "validate", "traceability"])
        assert r.exit_code == 1, r.output
        assert "DANGLING" in r.output

    def test_dangling_link_names_source_field_and_target(self, populated_dhf) -> None:
        _break_link(populated_dhf, "SRS-*.yaml", "SYS-", "SYS-GONE-")
        r = CliRunner().invoke(main, ["--dhf", str(populated_dhf), "validate", "traceability"])
        assert "derives_from" in r.output
        assert "SYS-GONE-" in r.output
        assert "target does not exist" in r.output

    def test_report_includes_dangling(self, populated_dhf, tmp_path) -> None:
        _break_link(populated_dhf, "SRS-*.yaml", "SYS-", "SYS-GONE-")
        report = tmp_path / "trace.json"
        CliRunner().invoke(
            main,
            ["--dhf", str(populated_dhf), "validate", "traceability", "--report", str(report)],
        )
        payload = json.loads(report.read_text())
        assert payload["dangling"]
        assert payload["passed"] is False


class TestCoverageLabelling:
    """Uncovered items are advisory by default and must not be labelled FAIL."""

    def test_advisory_gap_uses_warning_glyph(self, populated_dhf) -> None:
        # Remove every SWDD so SRS items lose downstream coverage.
        for path in (populated_dhf / "items").rglob("SWDD-*.yaml"):
            path.unlink()
        r = CliRunner().invoke(main, ["--dhf", str(populated_dhf), "validate", "traceability"])
        assert r.exit_code == 0, r.output
        assert "⚠" in r.output
        assert "not blocking" in r.output

    def test_fail_on_uncovered_switches_to_blocking(self, populated_dhf) -> None:
        for path in (populated_dhf / "items").rglob("SWDD-*.yaml"):
            path.unlink()
        r = CliRunner().invoke(
            main,
            ["--dhf", str(populated_dhf), "validate", "traceability", "--fail-on-uncovered"],
        )
        assert r.exit_code == 1, r.output
        assert "FAIL —" in r.output
        assert "uncovered item(s)" in r.output

    def test_clean_dhf_still_passes(self, populated_dhf) -> None:
        r = CliRunner().invoke(main, ["--dhf", str(populated_dhf), "validate", "traceability"])
        assert r.exit_code == 0, r.output
