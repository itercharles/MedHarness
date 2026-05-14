"""Unit tests for ItemType enum and V-model helpers."""

import pytest
from dhfkit.item_type import ItemType, default_traceability_rules, default_coverage_chains
from dhfkit.models.config import DocTypeConfig, ProjectConfig


_ALL_CODES = ["UC", "CRS", "SYS", "SRS", "SWDD", "SYSARCH", "RISK", "RCM", "CR", "REL", "SOUP", "DEF"]
_ALL_PREFIXES = ["UC-", "CRS-", "SYS-", "SRS-", "SWDD-", "SYSARCH-", "RISK-", "RCM-", "CR-", "REL-", "SOUP-", "DEF-"]


def test_from_code_all_known_types():
    for code in _ALL_CODES:
        assert ItemType.from_code(code) is not None, f"from_code({code!r}) returned None"


def test_from_prefix_all_known_types():
    for prefix in _ALL_PREFIXES:
        assert ItemType.from_prefix(prefix) is not None, f"from_prefix({prefix!r}) returned None"


def test_from_code_unknown_returns_none():
    assert ItemType.from_code("CUSTOM") is None
    assert ItemType.from_code("") is None


def test_from_prefix_unknown_returns_none():
    assert ItemType.from_prefix("CUSTOM-") is None


def test_from_code_roundtrip():
    for member in ItemType:
        assert ItemType.from_code(member.value.code) is member


def test_from_prefix_roundtrip():
    for member in ItemType:
        assert ItemType.from_prefix(member.value.default_prefix) is member


def test_default_traceability_rules_non_empty():
    rules = default_traceability_rules()
    assert len(rules) > 0


def test_default_traceability_rules_are_valid():
    from dhfkit.models.config import RequiredTraceabilityRule
    rules = default_traceability_rules()
    for rule in rules:
        assert isinstance(rule, RequiredTraceabilityRule)
        assert rule.direction == "upstream"
        assert rule.field is not None
        assert rule.min_count == 1


def test_default_traceability_rules_cover_vmodel_chain():
    rules = default_traceability_rules()
    rule_keys = {(r.source_type, r.field, r.target_type) for r in rules}
    assert ("CRS", "derives_from", "UC") in rule_keys
    assert ("SRS", "derives_from", "SYS") in rule_keys
    assert ("SWDD", "implements", "SRS") in rule_keys
    assert ("SYSARCH", "design", "SYS") in rule_keys
    assert ("RCM", "mitigates", "RISK") in rule_keys
    assert ("RCM", "implements", "SYS") in rule_keys


def test_default_coverage_chains_non_empty():
    chains = default_coverage_chains()
    assert len(chains) > 0


def test_default_coverage_chains_are_valid():
    from dhfkit.models.config import TraceabilityMatrix
    for chain in default_coverage_chains():
        assert isinstance(chain, TraceabilityMatrix)
        assert len(chain.path) == 2


def test_custom_type_not_in_itemtype_gracefully_handled():
    """Custom doc types not in ItemType work without error."""
    dt = DocTypeConfig(code="CUSTOM", name="Custom Type", prefix="CUSTOM-")
    it = ItemType.from_code(dt.code)
    assert it is None
    # Adapter fallback: role → code
    role = dt.role or (it.value.role if it else dt.code)
    assert role == "CUSTOM"
    parent_types = [r[1] for r in it.value.required_upstream] if it else []
    assert parent_types == []


def test_item_type_dict_name_uses_human_readable_name():
    """_item_type_dict should use dt.name (human-readable) not dt.code."""
    from dhfkit.local_adapter import LocalDHFAdapter
    from dhfkit.models.config import ProjectConfig
    from dhfkit.tests.fixtures import create_test_dhf

    dhf_path = create_test_dhf()
    adapter = LocalDHFAdapter(dhf_path)
    types = {t["code"]: t for t in adapter.list_item_types()}
    sys_type = types.get("SYS")
    assert sys_type is not None
    assert sys_type["name"] != "SYS", "name should be human-readable, not the code"


def test_has_verification_defaults():
    assert ItemType.SYS.value.has_verification is True
    assert ItemType.SRS.value.has_verification is True
    assert ItemType.CRS.value.has_verification is True
    assert ItemType.SWDD.value.has_verification is True
    assert ItemType.UC.value.has_verification is False
    assert ItemType.RISK.value.has_verification is False
    assert ItemType.CR.value.has_verification is False
