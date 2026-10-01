"""What an AI agent reads before working on a CR.

One definition, which `build plan` and `build code` render into their prompts,
so the two stages cannot be told different things about the same CR.

The CR's own state sets the scope. Before `build plan` records
`affected_items`, choosing what to change needs every item; after, the agent
needs only what the CR affects, in full.
"""

from __future__ import annotations

from typing import Any

from medharness.services.traceability import build_module_map, default_coverage_chains

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
             "role": dt.get("role") or "", "links": _link_fields(dt)}
            for dt in adapter.list_item_types()
        ],
        "chains": [m.path for m in (adapter.config.traceability_matrices or default_coverage_chains())],
        "items": chosen,
        "modules": modules,
        "risks": _risks(items, adapter.config),
    }


def _link_fields(item_type: dict) -> list[dict]:
    """The link fields a type declares: where they point, and what they mean."""
    return [
        {"field": f["name"], "targets": list(f.get("target_types") or []),
         "meaning": f.get("description") or f.get("label") or ""}
        for f in item_type.get("fields") or []
        if isinstance(f, dict) and f.get("format") in ("relationship", "item_multiselect") and f.get("name")
    ]


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
