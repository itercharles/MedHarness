"""DHF commands — Click declarations + presentation.

Calls dhfkit.api and _helpers directly. No commands/dhf.py intermediate layer.
"""

import json
from pathlib import Path
import click
import medharness._helpers as _h
import dhfkit.api as _api
from medharness.services.git import commit_dhf_item
from medharness.services.spec_validation import parse_spec_frontmatter


def register(main):

    @main.group("dhf")
    def dhf() -> None:
        """DHF operations — items, validate, docs, tests, config."""

    # ── Item ──

    @dhf.group("item")
    def dhf_item() -> None:
        """Read and mutate DHF items."""

    def _resolve(ctx: click.Context) -> Path:
        return ctx.obj["dhf"]

    @dhf_item.command("list")
    @click.option("--type", "doc_type", default=None, metavar="CODE")
    @click.pass_context
    def dhf_item_list(ctx: click.Context, doc_type: str | None) -> None:
        for item in _api.list_items(_resolve(ctx), doc_type):
            click.echo(json.dumps(item, default=str))

    @dhf_item.command("get")
    @click.argument("item_id")
    @click.pass_context
    def dhf_item_get(ctx: click.Context, item_id: str) -> None:
        item = _api.get_item(_resolve(ctx), item_id)
        if item is None:
            raise click.ClickException(f"Item '{item_id}' not found.")
        click.echo(json.dumps(item, default=str))

    @dhf_item.command("create")
    @click.option("--type", "doc_type", required=True, metavar="CODE")
    @click.option("--data", required=True, metavar="JSON")
    @click.option("--author", default="system", show_default=True)
    @click.option("--cr", "cr_id", default=None, metavar="CR_ID")
    @click.pass_context
    def dhf_item_create(ctx: click.Context, doc_type: str, data: str,
                        author: str, cr_id: str | None) -> None:
        payload = _h._parse_json_object(data)
        payload["type"] = doc_type
        click.echo(json.dumps(_api.create_item(_resolve(ctx), payload, author, cr_id), default=str))

    @dhf_item.command("update")
    @click.argument("item_id")
    @click.option("--data", required=True, metavar="JSON")
    @click.option("--author", default="system", show_default=True)
    @click.option("--cr", "cr_id", default=None, metavar="CR_ID")
    @click.pass_context
    def dhf_item_update(ctx: click.Context, item_id: str, data: str,
                        author: str, cr_id: str | None) -> None:
        payload = _h._parse_json_object(data)
        result = _api.update_item(_resolve(ctx), item_id, payload, author, cr_id)
        if result is None:
            raise click.ClickException(f"Item '{item_id}' not found.")
        click.echo(json.dumps(result, default=str))

    @dhf_item.command("delete")
    @click.argument("item_id")
    @click.option("--author", default="system", show_default=True)
    @click.pass_context
    def dhf_item_delete(ctx: click.Context, item_id: str, author: str) -> None:
        if not _api.delete_item(_resolve(ctx), item_id, author):
            raise click.ClickException(f"Item '{item_id}' not found or could not be deleted.")
        click.echo(json.dumps({"deleted": item_id}))

    @dhf_item.command("transitions")
    @click.argument("item_id")
    @click.pass_context
    def dhf_item_transitions(ctx: click.Context, item_id: str) -> None:
        click.echo(json.dumps(_api.get_item_transitions(_resolve(ctx), item_id), default=str))

    @dhf_item.command("transition")
    @click.argument("item_id")
    @click.argument("to_state")
    @click.option("--by", "performed_by", default="medharness", show_default=True)
    @click.option("--commit", is_flag=True, default=False)
    @click.option("--push", "do_push", is_flag=True, default=False)
    @click.option("--commit-message", default=None, metavar="TEXT")
    @click.pass_context
    def dhf_item_transition(ctx: click.Context, item_id: str, to_state: str,
                            performed_by: str, commit: bool, do_push: bool,
                            commit_message: str | None) -> None:
        result = _api.transition_item(_resolve(ctx), item_id, to_state, performed_by)
        click.echo(json.dumps(result, default=str))

        if commit:
            dhf_path = _resolve(ctx)
            msg = commit_message or f"chore: transition {item_id} to {to_state} [skip ci]"
            git_result = commit_dhf_item(dhf_path, item_id, msg, push=do_push)
            click.echo(json.dumps({"git": git_result}, default=str))

    # ── Validate ──

    @dhf.group("validate")
    def dhf_validate() -> None:
        """DHF data validation."""

    @dhf_validate.command("schema")
    @click.pass_context
    def dhf_validate_schema(ctx: click.Context) -> None:
        click.echo(json.dumps(_api.validate_schema(_resolve(ctx)), default=str))

    @dhf_validate.command("traceability")
    @click.pass_context
    def dhf_validate_traceability(ctx: click.Context) -> None:
        click.echo(json.dumps(_api.validate_traceability(_resolve(ctx)), default=str))

    # ── Doc ──

    @dhf.group("doc")
    def dhf_doc() -> None:
        """Document generation and export."""

    @dhf_doc.command("list")
    @click.pass_context
    def dhf_doc_list(ctx: click.Context) -> None:
        click.echo(json.dumps({"doc_types": _api.list_doc_types(_resolve(ctx))}))

    @dhf_doc.command("generate")
    @click.argument("doc_type_code")
    @click.pass_context
    def dhf_doc_generate(ctx: click.Context, doc_type_code: str) -> None:
        click.echo(json.dumps(_api.generate_doc(_resolve(ctx), doc_type_code), default=str))

    @dhf_doc.command("export")
    @click.argument("doc_type_code")
    @click.pass_context
    def dhf_doc_export(ctx: click.Context, doc_type_code: str) -> None:
        click.echo(json.dumps(_api.export_pdf(_resolve(ctx), doc_type_code), default=str))

    # ── Test ──

    @dhf.group("test")
    def dhf_test() -> None:
        """Test result queries."""

    @dhf_test.command("list")
    @click.option("--status", "status_filter", default=None, metavar="STATUS")
    @click.pass_context
    def dhf_test_list(ctx: click.Context, status_filter: str | None) -> None:
        results = _api.list_test_results(_resolve(ctx), status_filter)
        for rec in results.values():
            click.echo(json.dumps(rec, default=str))
        click.echo(f"({len(results)} result(s))", err=True)

    # ── Config ──

    @dhf.group("config")
    def dhf_config() -> None:
        """Inspect DHF configuration."""

    @dhf_config.command("doc-types")
    @click.pass_context
    def dhf_config_doc_types(ctx: click.Context) -> None:
        click.echo(json.dumps(_api.list_doc_type_configs(_resolve(ctx)), default=str))

    # ── Context (AI harness) ──

    @dhf.group("context")
    def dhf_context() -> None:
        """DHF context for AI agents and CI pipelines."""

    @dhf_context.command("implementation")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--out-dir", required=True, type=click.Path(file_okay=False, path_type=Path))
    @click.pass_context
    def dhf_context_implementation(ctx: click.Context, cr_id: str, out_dir: Path) -> None:
        """Write CR item, spec, and DHF overview to out-dir for CI/agent consumption.

        Outputs JSON with paths to the written files: {"cr": "...", "implementation_spec": "...", "context": "..."}.
        """
        adapter = _h._make_adapter(ctx)
        dhf_path: Path = ctx.obj["dhf"]
        out_dir.mkdir(parents=True, exist_ok=True)

        cr = adapter.get_item(cr_id)
        cr_path = out_dir / f"{cr_id}.json"
        if cr:
            cr_path.write_text(json.dumps(cr, default=str) + "\n", encoding="utf-8")
        else:
            cr_path.write_text(json.dumps({"id": cr_id, "found": False}) + "\n", encoding="utf-8")

        spec = adapter.get_document(f"{cr_id}-Spec")
        spec_path = out_dir / f"{cr_id}-Spec.md"
        if spec:
            spec_path.write_text(spec, encoding="utf-8")
        else:
            spec_path.write_text("", encoding="utf-8")

        items = adapter.list_items()
        trace = adapter.validate_traceability()
        coverage_summary = [
            {"parent": c["parent_type"], "child": c["child_type"],
             "covered": c["covered"], "total": c["total"]}
            for c in trace.get("coverage", [])
        ]
        overview = {
            "project": dhf_path.parent.name,
            "cr": ({"id": cr_id, "title": cr.get("title", ""), "status": cr.get("status", "")}
                   if cr else {"id": cr_id, "found": False}),
            "item_count": len(items),
            "items": [
                {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
                 "status": it.get("status", ""), "tracelinks": it.get("all_linked_uids", [])}
                for it in sorted(items, key=lambda x: x["id"])
            ],
            "traceability": {
                "valid": all(c["covered"] == c["total"] for c in trace.get("coverage", [])),
                "coverage": coverage_summary,
                "orphan_count": len(trace.get("orphans", [])),
            },
            "test_coverage": {"computed": False},
        }
        context_path = out_dir / "implementation-context.json"
        context_path.write_text(json.dumps(overview, default=str) + "\n", encoding="utf-8")

        click.echo(json.dumps({
            "cr": str(cr_path),
            "implementation_spec": str(spec_path),
            "context": str(context_path),
        }))

    @dhf_context.command("for-stage")
    @click.argument("stage", type=click.Choice(["analyze", "design", "develop"]))
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--spec", "spec_path", default=None, type=click.Path(path_type=Path),
                  metavar="PATH", help="Path to spec file (auto-detected if omitted).")
    @click.pass_context
    def dhf_context_for_stage(ctx: click.Context, stage: str, cr_id: str,
                               spec_path: Path | None) -> None:
        """Output scoped DHF context for a specific workflow stage.

        Returns only the information relevant to the current stage:
          analyze — CR item, all items summarized, traceability gaps, test coverage
          design  — CR item, approved spec plan, affected items only
          develop — CR item, spec plan, affected items, full spec text
        """
        adapter = _h._make_adapter(ctx)
        dhf_path: Path = ctx.obj["dhf"]

        cr = adapter.get_item(cr_id)
        cr_summary = ({"id": cr_id, "title": cr.get("title", ""), "status": cr.get("status", "")}
                      if cr else {"id": cr_id, "found": False})

        # Locate spec
        if spec_path is None:
            spec_path = dhf_path / "documents" / "specs" / f"{cr_id}-Spec.md"
        fm = parse_spec_frontmatter(spec_path)

        if stage == "analyze":
            items = adapter.list_items()
            trace = adapter.validate_traceability()
            orphans = trace.get("orphans", [])
            coverage = trace.get("coverage", [])
            gaps = [c for c in coverage if c.get("covered", 0) < c.get("total", 0)]
            result: dict = {
                "stage": "analyze",
                "cr": cr_summary,
                "item_count": len(items),
                "items": [
                    {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
                     "status": it.get("status", ""), "tracelinks": it.get("all_linked_uids", [])}
                    for it in sorted(items, key=lambda x: x["id"])
                ],
                "traceability_gaps": {
                    "orphan_count": len(orphans),
                    "orphans": [o.get("id") for o in orphans[:20]],
                    "uncovered_pairs": [
                        {"parent": g["parent_type"], "child": g["child_type"],
                         "covered": g["covered"], "total": g["total"]}
                        for g in gaps
                    ],
                },
            }

        elif stage == "design":
            affected_ids: list[str] = fm.get("affected_items", []) if fm else []
            affected_items = [
                adapter.get_item(uid) for uid in affected_ids
            ]
            result = {
                "stage": "design",
                "cr": cr_summary,
                "spec_plan": fm,
                "affected_items": [
                    {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
                     "status": it.get("status", ""), "tracelinks": it.get("all_linked_uids", [])}
                    for it in affected_items if it is not None
                ],
            }

        else:  # develop
            affected_ids = fm.get("affected_items", []) if fm else []
            affected_items = [adapter.get_item(uid) for uid in affected_ids]
            spec_text = adapter.get_document(f"{cr_id}-Spec") or ""
            if not spec_text and spec_path.exists():
                spec_text = spec_path.read_text(encoding="utf-8")
            result = {
                "stage": "develop",
                "cr": cr_summary,
                "spec_plan": fm,
                "spec_text": spec_text,
                "affected_items": [
                    {"id": it["id"], "type": it.get("type", ""), "title": it.get("title", ""),
                     "status": it.get("status", ""), "tracelinks": it.get("all_linked_uids", [])}
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
        adapter = _h._make_adapter(ctx)
        dhf_path: Path = ctx.obj["dhf"]
        result: dict = {"project": dhf_path.parent.name}

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

        trace = adapter.validate_traceability()
        coverage_summary = [
            {"parent": c["parent_type"], "child": c["child_type"],
             "covered": c["covered"], "total": c["total"]}
            for c in trace.get("coverage", [])
        ]
        result["traceability"] = {
            "valid": all(c["covered"] == c["total"] for c in trace.get("coverage", [])),
            "coverage": coverage_summary,
            "orphan_count": len(trace.get("orphans", [])),
        }

        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        if junit_paths:
            from medharness.services.ci import compute_item_coverage
            result["test_coverage"] = compute_item_coverage(junit_paths, adapter)
        else:
            result["test_coverage"] = {"computed": False}

        click.echo(json.dumps(result, default=str))


