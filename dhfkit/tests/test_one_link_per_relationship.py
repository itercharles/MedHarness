"""Between two item types, the defaults declare one link field, in one direction.

SYS carried both `satisfies` and `derives_from` pointing at CRS, and SYS and RCM
each had an `implements` pointing at the other. A project could record one
relationship two ways, and a check that read one field missed the other.
"""

from __future__ import annotations

from collections import defaultdict

from dhfkit.models.config import ProjectConfig
from dhfkit.paths import DEFAULT_CONFIG_DIR

# Links that name a record rather than trace the V-model: several may point at
# the same type for different reasons (a defect's found and fixed releases).
_RECORD_TYPES = {"CR", "DEF", "REL"}


def _links() -> dict[frozenset, list[str]]:
    pairs: dict[frozenset, list[str]] = defaultdict(list)
    for dt in ProjectConfig.load(DEFAULT_CONFIG_DIR).doc_types:
        if dt.code in _RECORD_TYPES:
            continue
        for prop in dt.properties or []:
            if isinstance(prop, dict) and prop.get("format") in ("relationship", "item_multiselect"):
                for target in prop.get("target_types") or []:
                    pairs[frozenset({dt.code, target})].append(f"{dt.code}.{prop['name']} → {target}")
    return pairs


def test_no_relationship_is_declared_twice() -> None:
    doubled = {tuple(sorted(k)): v for k, v in _links().items() if len(v) > 1}
    assert not doubled, doubled


def test_the_scan_saw_the_v_model() -> None:
    assert frozenset({"SYS", "CRS"}) in _links() and frozenset({"RCM", "SYS"}) in _links()
