"""DHF commands — AI harness context assembly only.

Data-layer operations (item CRUD, validate, doc, test, config) live in
`dhfkit` — use `dhfkit --dhf DHF item ...` etc. from CI scripts and
AI agents.
"""

from __future__ import annotations

import json
from pathlib import Path
import click
import medharness._helpers as _h
from medharness.services.traceability import analyse


_DEVELOP_ITEM_FIELDS = (
    "id", "type", "title", "status",
    "description", "content", "verification_criteria",
)


def _traceability_summary(trace: dict) -> dict:
    """Summarise `analyse()` for an agent.

    `valid` must be the whole verdict. Deriving it from coverage alone told an
    agent the DHF was sound while `verify dhf` was failing the same DHF on a
    link cycle.
    """
    return {
        "valid": trace.get("passed", False),
        "coverage": [
            {"parent": c["parent_type"], "child": c["child_type"],
             "covered": c["covered"], "total": c["total"],
             "uncovered": c.get("uncovered", [])}
            for c in trace.get("coverage", [])
        ],
        "cycles": trace.get("cycles", []),
        "dangling": trace.get("dangling", []),
        "required_failures": trace.get("required", {}).get("failures", []),
    }


def register(main):

    @main.group("context")
    def dhf_context() -> None:
        """Design context for an AI agent or a CI step."""

    @dhf_context.command("implementation")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.pass_context
    def dhf_context_implementation(ctx: click.Context, cr_id: str) -> None:
        """What an agent needs to implement a CR: the CR, the item set, the modules.

        JSON on stdout: {project, cr, item_count, items, traceability, module_map},
        where `cr` is the full CR item. `traceability` carries the same verdict
        `verify dhf` reaches, so the agent is not told the DHF is sound while the
        gate is failing it.
        """
        from medharness.services.traceability import build_module_map

        adapter = _h._make_adapter(ctx.obj["dhf"])
        cr = adapter.get_item(cr_id)
        items = adapter.list_items()
        trace = analyse(adapter)

        click.echo(json.dumps({
            "project": adapter.config.project_name,
            "cr": cr if cr else {"id": cr_id, "found": False},
            "item_count": len(items),
            "items": [
                {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
                 "status": it.get("status", ""), "tracelinks": it.get("all_linked_uids", [])}
                for it in sorted(items, key=lambda x: x["id"])
            ],
            "traceability": _traceability_summary(trace),
            "module_map": build_module_map(items, adapter.config),
        }, default=str))

    @dhf_context.command("for-stage")
    @click.argument("stage", type=click.Choice(["analyze", "design", "develop"]))
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.pass_context
    def dhf_context_for_stage(ctx: click.Context, stage: str, cr_id: str) -> None:
        """Output scoped DHF context for a specific workflow stage.

        Returns only the information relevant to the current stage:
          analyze — CR item, all items summarized, traceability gaps
          design  — CR item, affected items
          develop — CR item, affected items
        """
        adapter = _h._make_adapter(ctx.obj["dhf"])

        cr = adapter.get_item(cr_id)
        cr_summary = ({"id": cr_id, "title": cr.get("title", ""), "status": cr.get("status", "")}
                      if cr else {"id": cr_id, "found": False})

        if stage == "analyze":
            items = adapter.list_items()
            trace = analyse(adapter)
            coverage = trace.get("coverage", [])
            gaps = [c for c in coverage if c.get("covered", 0) < c.get("total", 0)]
            result: dict = {
                "stage": "analyze",
                "cr": cr or {"id": cr_id, "found": False},
                "item_count": len(items),
                "items": [
                    {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
                     "status": it.get("status", ""), "tracelinks": it.get("all_linked_uids", [])}
                    for it in sorted(items, key=lambda x: x["id"])
                ],
                "traceability_gaps": {
                    "uncovered_pairs": [
                        {"parent": g["parent_type"], "child": g["child_type"],
                         "covered": g["covered"], "total": g["total"]}
                        for g in gaps
                    ],
                    "cycles": trace.get("cycles", []),
                    "dangling": trace.get("dangling", []),
                },
            }

        elif stage == "design":
            items = adapter.list_items()
            result = {
                "stage": "design",
                "cr": cr or {"id": cr_id, "found": False},
                "item_count": len(items),
                "items": [
                    {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
                     "status": it.get("status", ""), "tracelinks": it.get("all_linked_uids", [])}
                    for it in sorted(items, key=lambda x: x["id"])
                ],
            }

        else:  # develop
            affected_ids: list[str] = list(cr.get("affected_items") or []) if cr else []
            affected_items = [adapter.get_item(uid) for uid in affected_ids]
            cr_develop: dict = (
                {
                    "id": cr_id,
                    "title": cr.get("title", ""),
                    "status": cr.get("status", ""),
                    "implementation_notes": cr.get("implementation_notes") or "",
                    "proposed_new_items": cr.get("proposed_new_items") or [],
                    "triage_result": cr.get("triage_result") or {},
                    "affected_risk_items": cr.get("affected_risk_items") or [],
                }
                if cr else {"id": cr_id, "found": False}
            )
            result = {
                "stage": stage,
                "cr": cr_develop,
                "affected_items": [
                    {
                        **{f: it.get(f, "") for f in _DEVELOP_ITEM_FIELDS},
                        "tracelinks": it.get("all_linked_uids", []),
                    }
                    for it in affected_items if it is not None
                ],
            }

        click.echo(json.dumps(result, default=str))

    @dhf_context.command("overview")
    @click.option("--cr", "cr_id", default=None, metavar="CR_ID")
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path))
    @click.pass_context
    def dhf_context_overview(ctx: click.Context, cr_id: str | None,
                              junit_files: tuple[Path, ...], junit_dirs: tuple[Path, ...]) -> None:
        """Output DHF overview as JSON for AI agents (item summaries, traceability gaps)."""
        adapter = _h._make_adapter(ctx.obj["dhf"])
        result: dict = {"project": adapter.config.project_name}

        if cr_id:
            cr = adapter.get_item(cr_id)
            if cr:
                result["cr"] = {"id": cr_id, "title": cr.get("title", ""), "status": cr.get("status", "")}
            else:
                result["cr"] = {"id": cr_id, "found": False}

        items = adapter.list_items()
        result["item_count"] = len(items)
        result["items"] = [
            {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
             "status": it.get("status", ""), "tracelinks": it.get("all_linked_uids", [])}
            for it in sorted(items, key=lambda x: x["id"])
        ]

        trace = analyse(adapter)
        result["traceability"] = _traceability_summary(trace)

        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        if junit_paths:
            from medharness.services.ci import compute_item_coverage
            result["test_coverage"] = compute_item_coverage(junit_paths, adapter)
        else:
            result["test_coverage"] = {"computed": False}

        click.echo(json.dumps(result, default=str))
