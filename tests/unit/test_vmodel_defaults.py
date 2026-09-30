"""The V-model defaults: which layer links to which, and which covers which.

These moved out of `dhfkit.item_type` with the analysis they serve. They are
modelling decisions about the process — a project overrides them in
`global.yaml` — not constraints a store enforces, and a team whose DHF lives in
Jira needs them just as much.
"""

from __future__ import annotations

from medharness.services.traceability import (
    default_coverage_chains,
    default_traceability_rules,
)




def test_default_traceability_rules_cover_vmodel_chain():
    rules = default_traceability_rules()
    rule_keys = {(r.source_type, r.field, r.target_type) for r in rules}
    assert ("CRS", "derives_from", "UC") in rule_keys
    assert ("SRS", "derives_from", "SYS") in rule_keys
    assert ("SWDD", "implements", "SRS") in rule_keys
    assert ("SYSARCH", "design", "SYS") in rule_keys
    assert ("RCM", "mitigates", "RISK") in rule_keys
    assert ("RCM", "implements", "SYS") in rule_keys



def test_module_in_default_coverage_chains():
    chains = default_coverage_chains()
    paths = [tuple(c.path) for c in chains]
    assert ("MODULE", "SWDD") in paths

def test_default_traceability_rules_cover_swdd_implements_and_module():
    rules = default_traceability_rules()
    rule_keys = {(r.source_type, r.field, r.target_type) for r in rules}
    assert ("SWDD", "implements", "SRS") in rule_keys
    assert ("SWDD", "module", "MODULE") in rule_keys
