"""Internal V-model type registry for DHF items.

The 12 standard types are baked into the framework. Configuration only
overrides display names, prefixes, and adds project-specific properties.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from dhfkit.models.config import RequiredTraceabilityRule, TraceabilityMatrix


@dataclass(frozen=True)
class ItemTypeMeta:
    code: str
    default_prefix: str
    display_name: str
    role: str
    has_verification: bool
    required_upstream: List[Tuple[str, str]] = field(default_factory=list)
    coverage_children: List[str] = field(default_factory=list)


class ItemType(Enum):
    """Standard V-model document types for medical device DHF.

    Each member carries the metadata needed to drive traceability and
    coverage checks without requiring YAML configuration.
    """

    UC      = ItemTypeMeta("UC",      "UC-",      "Use Case",                      "use_case",             False, [],                                           ["CRS"])
    CRS     = ItemTypeMeta("CRS",     "CRS-",     "Customer Requirement",          "customer_requirement",  True,  [("derives_from", "UC")],                    ["SYS"])
    # SYS has no required upstream: it can derive from CRS or implement RCM,
    # but both are optional per IEC 62304 — projects enforce via explicit rules.
    SYS     = ItemTypeMeta("SYS",     "SYS-",     "System Requirement",            "system_requirement",    True,  [],                                           ["SRS", "SYSARCH"])
    SRS     = ItemTypeMeta("SRS",     "SRS-",     "Software Requirement",          "software_requirement",  True,  [("derives_from", "SYS")],                   ["SWDD"])
    SWDD    = ItemTypeMeta("SWDD",    "SWDD-",    "Software Detailed Design",      "design_detail",         True,  [("implements", "SRS")],                         [])
    SYSARCH = ItemTypeMeta("SYSARCH", "SYSARCH-", "System Architecture",           "architecture",          False, [("design", "SYS")],                         [])
    MODULE  = ItemTypeMeta("MODULE",  "MODULE-",  "Software Module",               "software_module",       False, [],                                           ["SWDD"])
    RISK    = ItemTypeMeta("RISK",    "RISK-",    "Risk Analysis",                 "risk",                  False, [],                                           ["RCM"])
    RCM     = ItemTypeMeta("RCM",     "RCM-",     "Risk Control Measure",          "risk_control",          False, [("mitigates", "RISK"), ("implements", "SYS")], [])
    CR      = ItemTypeMeta("CR",      "CR-",      "Change Request",                "change_request",        False, [],                                           [])
    REL     = ItemTypeMeta("REL",     "REL-",     "Release",                       "release",               False, [],                                           [])
    SOUP    = ItemTypeMeta("SOUP",    "SOUP-",    "Software of Unknown Provenance", "soup",                 False, [],                                           [])
    DEF     = ItemTypeMeta("DEF",     "DEF-",     "Defect",                        "defect",                False, [],                                           [])

    @classmethod
    def from_code(cls, code: str) -> Optional["ItemType"]:
        for member in cls:
            if member.value.code == code:
                return member
        return None

    @classmethod
    def from_prefix(cls, prefix: str) -> Optional["ItemType"]:
        for member in cls:
            if member.value.default_prefix == prefix:
                return member
        return None


def default_traceability_rules() -> List["RequiredTraceabilityRule"]:
    """Generate required traceability rules from ItemType V-model metadata."""
    from dhfkit.models.config import RequiredTraceabilityRule
    rules = []
    for member in ItemType:
        meta = member.value
        for link_field, target_code in meta.required_upstream:
            rules.append(RequiredTraceabilityRule(
                source_type=meta.code,
                direction="upstream",
                field=link_field,
                target_type=target_code,
                min_count=1,
            ))
    return rules


def default_coverage_chains() -> List["TraceabilityMatrix"]:
    """Generate traceability matrices from ItemType coverage_children metadata."""
    from dhfkit.models.config import TraceabilityMatrix
    matrices = []
    for member in ItemType:
        meta = member.value
        for child_code in meta.coverage_children:
            matrices.append(TraceabilityMatrix(
                name=f"{meta.code} → {child_code}",
                description=f"{meta.display_name} covered by {child_code}",
                path=[meta.code, child_code],
            ))
    return matrices
