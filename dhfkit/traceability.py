"""Referential integrity of the stored links.

A link naming an item that does not exist is a question about whether the data
is well-formed, which is the store's to answer — and each adapter answers it its
own way, since a Jira issue link cannot point at a missing issue in the first
place.

Whether the V-model *holds* — coverage between layers, cycles, risk chains — is
analysis over the whole set and lives in `medharness.services.traceability`.
"""

from __future__ import annotations

from collections.abc import Iterable

def find_dangling_links(items: list[dict], link_fields: Iterable[str]) -> list[dict]:
    """Find traceability links pointing at IDs that do not exist in the DHF.

    A dangling link is not the same failure as missing coverage: the author did
    write a link, it just resolves to nothing. Reported separately so the fix
    ("correct the target ID") is not confused with the coverage remediation
    ("add a link"), and so a typo cannot hide as a downstream coverage gap.

    Returns [{"source", "field", "target"}] sorted for stable output.
    """
    known = {item["id"] for item in items}
    fields = sorted(set(link_fields))
    dangling: list[dict] = []
    for item in items:
        source = item.get("id", "")
        for field in fields:
            for target in item.get(field) or []:
                if target and target not in known:
                    dangling.append({"source": source, "field": field, "target": target})
    return sorted(dangling, key=lambda d: (d["source"], d["field"], d["target"]))
