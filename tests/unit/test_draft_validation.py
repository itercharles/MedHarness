"""
Tests for draft item pre-validation against field schemas.

Verifies that validate_draft() checks required fields and allowed values
against the adapter's item type field definitions.
"""

import pytest
from medharness.core import MedHarnessCore
from tests.fixtures.stub_adapter import StubDHFAdapter


def _adapter_with_sys_schema() -> StubDHFAdapter:
    adapter = StubDHFAdapter()
    adapter._item_types = [{
        "name": "SYS", "code": "SYS", "prefix": "SYS-",
        "parent_types": [], "has_verification": False, "lifecycle": None,
        "fields": [
            {"name": "title", "format": "short_text", "label": "Title", "required": True},
            {"name": "content", "format": "long_text", "label": "Content", "required": True},
            {"name": "category", "format": "select", "required": True,
             "options": ["Functional", "Performance", "Security"], "default": "Functional"},
            {"name": "verification_method", "format": "multiselect",
             "options": ["Test", "Inspection", "Analysis"]},
        ],
    }]
    adapter._lifecycle_states = [{"id": "draft", "label": "Draft", "is_stable": False}]
    return adapter


def test_valid_item_passes(stub_adapter):
    core = MedHarnessCore(stub_adapter)
    result = core.validate_draft(
        {"id": "SYS-001", "title": "T", "content": "C", "category": "Functional",
         "verification_method": ["Test"]}
    )
    assert result["valid"] is True, result.get("errors")

def test_missing_required_field_fails():
    adapter = _adapter_with_sys_schema()
    core = MedHarnessCore(adapter)
    result = core.validate_draft({"id": "SYS-001", "title": "T", "content": "C"})
    assert result["valid"] is False

def test_invalid_select_value_fails():
    adapter = _adapter_with_sys_schema()
    core = MedHarnessCore(adapter)
    result = core.validate_draft(
        {"id": "SYS-001", "title": "T", "content": "C", "category": "InvalidCategory"}
    )
    assert result["valid"] is False

def test_invalid_multiselect_value_fails():
    adapter = _adapter_with_sys_schema()
    core = MedHarnessCore(adapter)
    result = core.validate_draft(
        {"id": "SYS-001", "title": "T", "content": "C", "category": "Functional",
         "verification_method": ["InvalidMethod"]}
    )
    assert result["valid"] is False

def test_valid_multiselect_values_pass():
    adapter = _adapter_with_sys_schema()
    core = MedHarnessCore(adapter)
    result = core.validate_draft(
        {"id": "SYS-001", "title": "T", "content": "C", "category": "Functional",
         "verification_method": ["Test", "Inspection"]}
    )
    assert result["valid"] is True

def test_type_inferred_from_id_prefix():
    adapter = _adapter_with_sys_schema()
    core = MedHarnessCore(adapter)
    result = core.validate_draft({"id": "SYS-042", "title": "T", "content": "C", "category": "Functional"})
    assert result["valid"] is True

def test_explicit_type_overrides_prefix():
    adapter = _adapter_with_sys_schema()
    core = MedHarnessCore(adapter)
    result = core.validate_draft(
        {"id": "CR-001", "type": "SYS", "title": "T", "content": "C", "category": "Functional"}
    )
    assert result["valid"] is True

def test_unknown_type_warns_not_errors(stub_adapter):
    core = MedHarnessCore(stub_adapter)
    result = core.validate_draft({"id": "UNKNOWN-001", "title": "T", "content": "C"})
    assert isinstance(result, dict)
    assert "valid" in result

def test_stub_adapter_no_fields_always_passes(stub_adapter):
    core = MedHarnessCore(stub_adapter)
    result = core.validate_draft({"id": "ANY-001", "any_field": "anything"})
    assert result["valid"] is True
