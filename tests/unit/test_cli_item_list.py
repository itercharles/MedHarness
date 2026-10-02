"""Tests for CLI command: item list [--type CODE]"""
import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner


from medharness.cli import main


def _parse_lines(output: str) -> list[dict]:
    """Parse newline-delimited JSON output, skipping non-JSON lines."""
    results = []
    for line in output.strip().splitlines():
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return results


def test_item_list_returns_all_items(populated_dhf):
    """item list returns all items as newline-delimited JSON."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'list'])
    assert result.exit_code == 0
    items = _parse_lines(result.output)
    assert len(items) > 0


def test_item_list_filter_by_type(populated_dhf):
    """item list --type SYS returns only SYS items."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'list', '--type', 'SYS'])
    assert result.exit_code == 0
    items = _parse_lines(result.output)
    assert len(items) > 0
    for item in items:
        assert item['id'].startswith('SYS-'), f"Expected SYS- prefix, got {item['id']}"


def test_item_list_filter_unknown_type_returns_empty(populated_dhf):
    """item list --type UNKNOWN returns no items (empty output, exit 0)."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'list', '--type', 'UNKNOWN'])
    assert result.exit_code == 0
    items = _parse_lines(result.output)
    assert items == []


class TestRetrievalOptions:
    """`--match`, `--linked-to` and `--brief`: how an agent finds items in a large DHF."""

    @pytest.fixture
    def dhf(self, tmp_path: Path) -> Path:
        from dhfkit.tests.fixtures import bare_dhf

        dhf = bare_dhf(tmp_path / "DHF")

        def create(type_: str, **data) -> str:
            r = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "create", "--type", type_,
                                          "--data", json.dumps(data, ensure_ascii=False)])
            assert r.exit_code == 0, r.output
            return json.loads(r.stdout.splitlines()[0])["id"]

        self.sys_a = create("SYS", category="Functional", title="Export report", content="Exports the Report as PDF")
        self.sys_b = create("SYS", category="Functional", title="Login", content="Password rules")
        self.srs_a = create("SRS", title="PDF layout", derives_from=[self.sys_a],
                            verification_criteria="Page size is A4")
        self.srs_b = create("SRS", title="导出报告", derives_from=[self.sys_b],
                            verification_criteria="文件名包含日期")
        return dhf

    def _list(self, dhf: Path, *args: str):
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "list", *args])
        return r, [it["id"] for it in _parse_lines(r.stdout)]

    def test_match_needs_every_word_in_any_text_field_ignoring_case(self, dhf: Path) -> None:
        r, ids = self._list(dhf, "--match", "exports PDF")
        assert r.exit_code == 0 and ids == [self.sys_a]

    def test_match_reaches_strings_inside_lists(self, dhf: Path) -> None:
        _, ids = self._list(dhf, "--match", self.sys_a, "--type", "SRS")
        assert ids == [self.srs_a]

    def test_match_finds_cjk_text(self, dhf: Path) -> None:
        _, ids = self._list(dhf, "--match", "导出 日期")
        assert ids == [self.srs_b]

    def test_match_combines_with_type(self, dhf: Path) -> None:
        _, ids = self._list(dhf, "--match", "pdf", "--type", "SRS")
        assert ids == [self.srs_a]

    @pytest.mark.parametrize("text", ["", "   "])
    def test_an_empty_match_is_refused(self, dhf: Path, text: str) -> None:
        r, ids = self._list(dhf, "--match", text)
        assert r.exit_code == 1 and ids == []
        assert "--match" in r.stderr

    def test_linked_to_keeps_both_directions(self, dhf: Path) -> None:
        _, up = self._list(dhf, "--linked-to", self.srs_a)
        _, down = self._list(dhf, "--linked-to", self.sys_a)
        assert up == [self.sys_a] and down == [self.srs_a]

    def test_linked_to_combines_with_type_and_match(self, dhf: Path) -> None:
        _, ids = self._list(dhf, "--linked-to", self.sys_a, "--type", "SYS")
        assert ids == []
        _, ids = self._list(dhf, "--linked-to", self.sys_a, "--match", "a4")
        assert ids == [self.srs_a]

    def test_an_unknown_linked_to_is_refused(self, dhf: Path) -> None:
        r, ids = self._list(dhf, "--linked-to", "SYS-999")
        assert r.exit_code == 1 and ids == []
        assert "Item 'SYS-999' not found." in r.stderr

    def test_brief_prints_four_keys(self, dhf: Path) -> None:
        r, _ = self._list(dhf, "--brief", "--type", "SRS")
        rows = _parse_lines(r.stdout)
        assert all(set(row) == {"id", "type", "title", "links"} for row in rows)
        assert rows[0] == {"id": self.srs_a, "type": "SRS", "title": "PDF layout", "links": [self.sys_a]}

    def test_no_match_is_empty_success(self, dhf: Path) -> None:
        r, ids = self._list(dhf, "--match", "nonexistent-term")
        assert r.exit_code == 0 and r.stdout == ""
        assert "(0 item(s))" in r.stderr
