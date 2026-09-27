"""What an AI agent reads before working on a CR.

One definition: `medharness context --cr` prints it as JSON, and `build plan`
and `build code` render the same dict into their prompts, so an outside agent
and the built-in stages cannot be told different things.

The CR's own state sets the scope. Before `build plan` records
`affected_items`, choosing what to change needs every item; after, the agent
needs only what the CR affects, in full.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from medharness.services.traceability import build_module_map

_FULL_ITEM_FIELDS = (
    "id", "type", "title", "status",
    "description", "content", "verification_criteria",
)


def cr_context(adapter: Any, cr_id: str) -> dict:
    """``{project, cr, scope, types, items, modules, risks}`` for one CR.

    ``scope`` is ``"affected"`` when the CR records ``affected_items`` — then
    ``items`` holds those items in full and ``modules`` only the modules that
    own them — and ``"whole_dhf"`` otherwise, with every item summarized and
    every module.
    """
    items = sorted(adapter.list_items(), key=lambda it: it["id"])
    cr = adapter.get_item(cr_id)
    affected = set((cr or {}).get("affected_items") or [])
    modules = build_module_map(items, adapter.config)

    if affected:
        scope = "affected"
        chosen = [
            {**{f: it.get(f, "") for f in _FULL_ITEM_FIELDS},
             "tracelinks": it.get("all_linked_uids", [])}
            for it in items if it["id"] in affected
        ]
        modules = [
            m for m in modules
            if m["module_id"] in affected
            or affected & {s["swdd_id"] for s in m["swdds"]}
            or affected & set(m["all_requirements"])
        ]
    else:
        scope = "whole_dhf"
        chosen = [
            {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
             "status": it.get("status", ""), "tracelinks": it.get("all_linked_uids", [])}
            for it in items
        ]

    return {
        "project": adapter.config.project_name,
        "cr": cr if cr else {"id": cr_id, "found": False},
        "scope": scope,
        "types": [
            {"code": dt["code"], "display_name": dt.get("display_name", ""),
             "role": dt.get("role") or ""}
            for dt in adapter.list_item_types()
        ],
        "items": chosen,
        "modules": modules,
        "risks": _risks(items, adapter.config),
    }


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return [value] if value else []


def _risks(items: list[dict], config: Any) -> list[dict]:
    """Every RISK with the RCMs that mitigate it; empty when either type is omitted."""
    risk_dt = config.get_doc_type("RISK")
    rcm_dt = config.get_doc_type("RCM")
    if not risk_dt or not rcm_dt:
        return []
    rcms = [it for it in items if it["id"].startswith(rcm_dt.prefix)]
    return [
        {
            "id": risk["id"],
            "title": risk.get("title", ""),
            "severity": risk.get("severity", ""),
            "risk_level": risk.get("risk_level", ""),
            "controls": [
                {"id": rcm["id"], "title": rcm.get("title", ""),
                 "implements": _as_list(rcm.get("implements"))}
                for rcm in rcms if risk["id"] in _as_list(rcm.get("mitigates"))
            ],
        }
        for risk in items if risk["id"].startswith(risk_dt.prefix)
    ]


def compute_item_coverage(
    junit_paths: list[Path],
    adapter=None,
) -> dict:
    """Parse JUnit XML files and return coverage plus manual-verification hints.

    An item becomes a manual-verification candidate when any of these DHF item
    fields are set: ``critical_safety == True``, ``verification_method`` contains
    ``"Inspection"`` or ``"Demonstration"``, or ``category == "Usability"``.

    Returns:
        {
          "computed": True,
          "coverage_by_item": dict,
          "uncovered_requirements": dict,
          "manual_verification_candidates": dict,
          "manual_verification_criteria": dict,
        }
    """
    from dhfkit.junit_parser import parse_junit_xml

    coverage_by_item: dict[str, list[str]] = {}
    for jp in junit_paths:
        if not jp.is_file():
            continue
        for result in parse_junit_xml(jp):
            if result.testing_status != "PASS":
                continue
            for link in result.links or []:
                coverage_by_item.setdefault(link.strip(), []).append(result.id)

    uncovered: dict[str, list[str]] = {}
    item_type_map: dict[str, str] = {}
    manual_candidates: dict[str, dict[str, list[str] | str]] = {}
    manual_candidates_error = ""
    if adapter is not None:
        try:
            all_items = adapter.list_items()
            item_type_map = {it["id"]: it.get("type", "") for it in all_items}
            for item in all_items:
                reasons: list[str] = []
                if item.get("critical_safety") is True:
                    reasons.append("critical_safety")

                verification_method = item.get("verification_method")
                if isinstance(verification_method, list):
                    for method in verification_method:
                        if method in {"Inspection", "Demonstration"}:
                            reasons.append(f"verification_method:{method}")

                category = item.get("category")
                if category == "Usability":
                    reasons.append("category:Usability")

                if reasons:
                    manual_candidates[item["id"]] = {
                        "type": item.get("type", ""),
                        "reasons": reasons,
                    }
        except Exception as exc:  # noqa: BLE001
            # An empty manual_candidates and an unreadable DHF looked identical
            # to a caller. They are not the same answer.
            manual_candidates_error = f"manual-review candidates unavailable: {exc}"

    for rt in (adapter.config.requirement_types() if adapter else ("SRS", "SYS", "CRS")):
        prefix = f"{rt}-"
        uncovered[rt] = []
        for item_id in item_type_map:
            if item_id.startswith(prefix) and item_id not in coverage_by_item:
                uncovered[rt].append(item_id)

    return {
        "computed": len(junit_paths) > 0,
        "coverage_by_item": coverage_by_item,
        "uncovered_requirements": {k: v for k, v in uncovered.items() if v},
        "manual_verification_candidates": manual_candidates,
        # Empty because there are none, or empty because the DHF would not
        # load? A caller cannot tell from the list alone.
        "manual_verification_candidates_error": manual_candidates_error,
        "manual_verification_criteria": {
            "critical_safety": True,
            "verification_methods": ["Inspection", "Demonstration"],
            "categories": ["Usability"],
        },
    }
