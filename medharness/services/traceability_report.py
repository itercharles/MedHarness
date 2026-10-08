"""The traceability matrix and the verification evidence it reports.

Like `services.traceability`, these take items and item types as values, never
a path. `build release` renders the result into its evidence bundle.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from dhfkit.junit_parser import read_test_evidence
from medharness.services.traceability import link_targets


def _type_of(item_id: str, by_prefix: dict[str, dict]) -> dict | None:
    # rsplit matches dhfkit's Item.prefix: a doc type may configure a
    # multi-segment prefix such as TC-VER-.
    return by_prefix.get(item_id.rsplit("-", 1)[0] + "-")


def verification_evidence(
    items: list[dict],
    item_types: list[dict],
    junit_paths: Iterable[Path] = (),
) -> dict[str, dict]:
    """``{id: {verification_status, test_cases}}`` for every verifiable item.

    Derived from the JUnit files alone, never read from the item: a stale
    ``verification_status: verified`` in the YAML must not stand in for
    evidence. A test links to items through its ``JUNIT_LINKS`` property; no TC
    ID is needed. A requirement whose tests were deleted is ``not_verified``.
    """
    results: dict[str, list[dict]] = {}
    for run in read_test_evidence(junit_paths):
        if run.status == "SKIP":
            continue
        test = {"name": f"{run.suite} › {run.name}" if run.suite else run.name, "status": run.status}
        for item_id in run.links:
            results.setdefault(item_id, []).append(test)

    by_prefix = {t["prefix"]: t for t in item_types if t.get("prefix")}
    evidence: dict[str, dict] = {}
    for item in items:
        cfg = _type_of(item["id"], by_prefix)
        if not cfg or not cfg.get("has_verification"):
            continue
        tests = results.get(item["id"], [])
        if not tests:
            status = "not_verified"
        elif any(t["status"] == "FAIL" for t in tests):
            status = "failed"
        else:
            status = "verified"
        evidence[item["id"]] = {"verification_status": status, "test_cases": tests}
    return evidence


def traceability_matrix(
    items: list[dict],
    item_types: list[dict],
    doc_types: list[str],
    config: Any,
) -> dict[str, Any]:
    """Every chain down the ordered *doc_types*, one row per chain.

    ``{"columns": doc_types, "rows": [{<code>: id | None, ..., "is_orphan",
    "orphan_type", "is_complete"}]}``. A child belongs to a parent when it links
    to it through a field its type declares for that parent's type, the same
    definition `verify dhf` judges coverage by. An item no chain reaches from the top
    gets its own row, marked orphan at its level.
    """
    if not doc_types:
        return {"columns": [], "rows": []}
    prefix_by_code = {t.get("code", "OTHER"): t.get("prefix") for t in item_types}

    def code_of(item_id: str) -> str:
        for code, prefix in prefix_by_code.items():
            if prefix and item_id.startswith(prefix):
                return code
        return "OTHER"

    by_code: dict[str, list[dict]] = {}
    for item in items:
        by_code.setdefault(code_of(item["id"]), []).append(item)

    chains: list[dict] = []

    def row(chain: dict, *, orphan: str | None = None) -> dict:
        r: dict[str, Any] = {code: chain[code]["id"] if code in chain else None
                             for code in doc_types}
        r["is_orphan"] = orphan is not None
        r["orphan_type"] = orphan
        r["is_complete"] = orphan is None and len(chain) == len(doc_types)
        return r

    def walk(level: int, chain: dict) -> None:
        if level >= len(doc_types) - 1:
            chains.append(chain)
            return
        current = chain[doc_types[level]]
        children = [
            child for child in by_code.get(doc_types[level + 1], [])
            if current["id"] in link_targets(child, config, doc_types[level])
        ]
        if not children:
            chains.append(chain)
        for child in children:
            walk(level + 1, {**chain, doc_types[level + 1]: child})

    for top in by_code.get(doc_types[0], []):
        walk(0, {doc_types[0]: top})

    reached = {chain[code]["id"] for chain in chains for code in chain}
    rows = [row(chain) for chain in chains]
    for code in doc_types:
        for item in by_code.get(code, []):
            if item["id"] not in reached:
                rows.append(row({code: item}, orphan=code))
    return {"columns": list(doc_types), "rows": rows}


def traceability_report(
    items: list[dict],
    item_types: list[dict],
    doc_types: list[str],
    config: Any,
    junit_paths: Iterable[Path] = (),
) -> dict[str, Any]:
    """The matrix, each row's verification status, and coverage by level."""
    matrix = traceability_matrix(items, item_types, doc_types, config)
    evidence = verification_evidence(items, item_types, junit_paths)
    by_prefix = {t["prefix"]: t for t in item_types if t.get("prefix")}
    titles = {item["id"]: item.get("title", "") for item in items}
    columns: list[str] = matrix["columns"]

    for r in matrix["rows"]:
        level_statuses = {
            col: evidence[r[col]]["verification_status"]
            for col in columns if r.get(col) in evidence
        }
        r["level_statuses"] = level_statuses
        for col in reversed(columns):
            if col in level_statuses:
                r["verification_status"] = level_statuses[col]
                break

    coverage: dict[str, list[dict]] = {}
    seen: set[str] = set()
    for col in columns:
        for r in matrix["rows"]:
            item_id = r.get(col)
            if not item_id or item_id in seen or item_id not in evidence:
                continue
            seen.add(item_id)
            # Keyed by the resolved doc-type code so it matches the columns;
            # deriving it from the ID guesses wrong for a multi-segment prefix.
            code = _type_of(item_id, by_prefix)["code"]
            coverage.setdefault(code, []).append({
                "id": item_id,
                "title": titles.get(item_id, ""),
                "status": evidence[item_id]["verification_status"],
                "tests": evidence[item_id]["test_cases"],
            })
    for level in coverage.values():
        level.sort(key=lambda x: x["id"])

    matrix["coverage"] = coverage
    return matrix
