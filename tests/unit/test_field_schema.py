"""
Tests for item type field metadata via adapter's get_item_type().

Verifies that the adapter returns field definitions for item types
and that the field metadata includes name, format, required, options.
"""

import pytest
from tests.fixtures.stub_adapter import StubDHFAdapter


def test_field_name_and_format():
    """Field metadata includes name and format."""
    adapter = StubDHFAdapter()
    adapter._item_types = [{
        "name": "SYS", "code": "SYS", "prefix": "SYS-",
        "parent_types": [], "has_verification": False, "lifecycle": None,
        "fields": [{"name": "title", "format": "short_text", "label": "Title"}],
    }]
    info = adapter.get_item_type("SYS-")
    assert info is not None
    assert info["fields"][0]["name"] == "title"
    assert info["fields"][0]["format"] == "short_text"

def test_item_type_carries_fields():
    """get_item_type returns fields list."""
    adapter = StubDHFAdapter()
    adapter._item_types = [{
        "name": "SYS", "code": "SYS", "prefix": "SYS-",
        "parent_types": [], "has_verification": False, "lifecycle": None,
        "fields": [{"name": "content", "format": "long_text", "required": True}],
    }]
    info = adapter.get_item_type("SYS-")
    assert len(info["fields"]) == 1
    assert info["fields"][0]["required"] is True

def test_fields_default_to_empty():
    """item type with no fields configured returns empty fields list."""
    adapter = StubDHFAdapter()
    info = adapter.get_item_type("UC-")
    assert info is not None
    assert info["fields"] == []

def test_list_item_types():
    """list_item_types returns all configured types."""
    adapter = StubDHFAdapter()
    types = adapter.list_item_types()
    assert len(types) >= 5
    names = [t["name"] for t in types]
    assert "SYS" in names
    assert "CRS" in names

def test_parent_types():
    """CRS parent_types includes UC."""
    adapter = StubDHFAdapter()
    info = adapter.get_item_type("CRS-")
    assert "UC" in info["parent_types"]

def test_unknown_prefix_returns_none():
    """get_item_type returns None for unknown prefix."""
    adapter = StubDHFAdapter()
    assert adapter.get_item_type("UNKNOWN-") is None

def test_has_verification():
    """SYS has_verification is True."""
    adapter = StubDHFAdapter()
    info = adapter.get_item_type("SYS-")
    assert info["has_verification"] is True
