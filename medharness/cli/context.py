"""`medharness context` — what an AI agent needs to know about the DHF.

Storage operations live in `dhfkit`.
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


def _summary(item: dict) -> dict:
    return {"id": item["id"], "type": item.get("type", ""), "title": item.get("title", ""),
            "status": item.get("status", ""), "tracelinks": item.get("all_linked_uids", [])}


def register(main):

    @main.command("context")
    @click.option("--cr", "cr_id", default=None, metavar="CR_ID",
                  help="Scope the answer to one CR: the CR, the items it affects, "
                       "and the modules that own them.")
    @click.option("--junit", "junit_files", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="A JUnit XML results file (repeatable). Adds test coverage.")
    @click.option("--junit-dir", "junit_dirs", multiple=True,
                  type=click.Path(file_okay=False, path_type=Path),
                  help="Directory of JUnit XML results (repeatable). Adds test coverage.")
    @click.pass_context
    def context(ctx: click.Context, cr_id: str | None,
                junit_files: tuple[Path, ...], junit_dirs: tuple[Path, ...]) -> None:
        """What an AI agent needs to know about the DHF, as JSON.

        \b
        Without --cr: every item summarized, and the traceability verdict.
        With --cr:    the CR in full, the items it affects in full, and the
                      modules that own them. A CR that has not yet recorded
                      affected_items — before `build plan` — gets every item
                      summarized instead, since choosing what to change needs
                      the whole DHF.

        `traceability.valid` is the verdict `verify dhf` reaches.
        """
        from medharness.services.traceability import build_module_map

        adapter = _h._make_adapter(ctx.obj["dhf"])
        items = sorted(adapter.list_items(), key=lambda it: it["id"])
        result: dict = {"project": adapter.config.project_name}

        if cr_id is None:
            result["item_count"] = len(items)
            result["items"] = [_summary(it) for it in items]
            result["traceability"] = _traceability_summary(analyse(adapter))
        else:
            cr = adapter.get_item(cr_id)
            result["cr"] = cr if cr else {"id": cr_id, "found": False}
            affected = set((cr or {}).get("affected_items") or [])
            module_map = build_module_map(items, adapter.config)
            if affected:
                result["affected_items"] = [
                    {**{f: it.get(f, "") for f in _DEVELOP_ITEM_FIELDS},
                     "tracelinks": it.get("all_linked_uids", [])}
                    for it in items if it["id"] in affected
                ]
                module_map = [
                    m for m in module_map
                    if m["module_id"] in affected
                    or affected & {s["swdd_id"] for s in m["swdds"]}
                    or affected & set(m["all_requirements"])
                ]
            else:
                result["items"] = [_summary(it) for it in items]
            result["module_map"] = module_map

        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        if junit_paths:
            from medharness.services.ci import compute_item_coverage
            result["test_coverage"] = compute_item_coverage(junit_paths, adapter)

        click.echo(json.dumps(result, default=str))
