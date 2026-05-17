"""Tests for dhfkit.traceability.build_module_map."""

from __future__ import annotations

import pytest

from dhfkit.traceability import build_module_map


class _FakeDocType:
    def __init__(self, code: str, prefix: str):
        self.code = code
        self.prefix = prefix


class _FakeConfig:
    def __init__(self, has_module: bool = True, has_swdd: bool = True):
        self._has_module = has_module
        self._has_swdd = has_swdd

    def get_doc_type(self, code: str):
        if code == "MODULE" and self._has_module:
            return _FakeDocType("MODULE", "MODULE-")
        if code == "SWDD" and self._has_swdd:
            return _FakeDocType("SWDD", "SWDD-")
        return None


def _items(*specs) -> list[dict]:
    return list(specs)


def test_returns_empty_when_no_module_doc_type() -> None:
    config = _FakeConfig(has_module=False)
    items = _items({"id": "SWDD-001", "title": "d", "module": ["MODULE-001"], "implements": ["SRS-001"]})
    assert build_module_map(items, config) == []


def test_returns_empty_when_no_swdd_doc_type() -> None:
    config = _FakeConfig(has_swdd=False)
    items = _items({"id": "MODULE-001", "title": "Auth"})
    assert build_module_map(items, config) == []


def test_single_module_single_swdd() -> None:
    config = _FakeConfig()
    items = _items(
        {"id": "MODULE-001", "title": "Auth Module"},
        {"id": "SWDD-001", "title": "Token logic", "module": ["MODULE-001"], "implements": ["SRS-001"]},
    )
    result = build_module_map(items, config)
    assert len(result) == 1
    m = result[0]
    assert m["module_id"] == "MODULE-001"
    assert m["title"] == "Auth Module"
    assert len(m["swdds"]) == 1
    assert m["swdds"][0]["swdd_id"] == "SWDD-001"
    assert m["swdds"][0]["implements"] == ["SRS-001"]
    assert m["all_requirements"] == ["SRS-001"]


def test_multiple_swdds_per_module() -> None:
    config = _FakeConfig()
    items = _items(
        {"id": "MODULE-001", "title": "API"},
        {"id": "SWDD-001", "title": "Rate limit", "module": ["MODULE-001"], "implements": ["SRS-001"]},
        {"id": "SWDD-002", "title": "Auth", "module": ["MODULE-001"], "implements": ["SRS-002", "SRS-003"]},
    )
    result = build_module_map(items, config)
    assert len(result) == 1
    m = result[0]
    assert len(m["swdds"]) == 2
    assert set(m["all_requirements"]) == {"SRS-001", "SRS-002", "SRS-003"}


def test_multiple_modules_are_sorted() -> None:
    config = _FakeConfig()
    items = _items(
        {"id": "MODULE-002", "title": "DB"},
        {"id": "MODULE-001", "title": "API"},
        {"id": "SWDD-001", "module": ["MODULE-002"], "implements": ["SRS-010"], "title": "Query"},
        {"id": "SWDD-002", "module": ["MODULE-001"], "implements": ["SRS-001"], "title": "Route"},
    )
    result = build_module_map(items, config)
    assert result[0]["module_id"] == "MODULE-001"
    assert result[1]["module_id"] == "MODULE-002"


def test_module_with_no_swdds_appears_in_map() -> None:
    config = _FakeConfig()
    items = _items({"id": "MODULE-001", "title": "Orphan module"})
    result = build_module_map(items, config)
    assert len(result) == 1
    assert result[0]["module_id"] == "MODULE-001"
    assert result[0]["swdds"] == []
    assert result[0]["all_requirements"] == []


def test_swdd_module_as_string_not_list() -> None:
    config = _FakeConfig()
    items = _items(
        {"id": "MODULE-001", "title": "M"},
        {"id": "SWDD-001", "title": "D", "module": "MODULE-001", "implements": ["SRS-001"]},
    )
    result = build_module_map(items, config)
    assert result[0]["swdds"][0]["swdd_id"] == "SWDD-001"


def test_implements_as_string_not_list() -> None:
    config = _FakeConfig()
    items = _items(
        {"id": "MODULE-001", "title": "M"},
        {"id": "SWDD-001", "title": "D", "module": ["MODULE-001"], "implements": "SRS-001"},
    )
    result = build_module_map(items, config)
    assert result[0]["swdds"][0]["implements"] == ["SRS-001"]


def test_all_requirements_deduplicates() -> None:
    config = _FakeConfig()
    items = _items(
        {"id": "MODULE-001", "title": "M"},
        {"id": "SWDD-001", "module": ["MODULE-001"], "implements": ["SRS-001", "SRS-002"], "title": "A"},
        {"id": "SWDD-002", "module": ["MODULE-001"], "implements": ["SRS-001", "SRS-003"], "title": "B"},
    )
    result = build_module_map(items, config)
    reqs = result[0]["all_requirements"]
    assert reqs.count("SRS-001") == 1
    assert set(reqs) == {"SRS-001", "SRS-002", "SRS-003"}
