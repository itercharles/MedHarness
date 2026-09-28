"""`build` — produce DHF items, code, and delivery artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from dhfkit.local_adapter import LocalDHFAdapter
from medharness.cli.options import collect_junit_paths, junit_option
from medharness.cli.output import emit


def _format_summary(stage_label: str, verb: str, cr_id: str, result: dict) -> str:
    """Compose the human-readable stderr summary for CI generate-* commands.

    Surfaces client-facing outcome, fix attempts, residual error count,
    elapsed time, and changed-item / changed-file counts when present.
    """
    diagnostics = result.get("diagnostics") or {}
    artifacts = result.get("artifacts") or {}
    timing = result.get("timing") or {}
    details = [
        f"outcome: {result.get('outcome', 'unknown')}",
    ]
    if diagnostics.get("fix_attempted"):
        details.append("fix attempted")
    err_count = len(result.get("errors") or [])
    if err_count:
        details.append(f"errors: {err_count}")
    elapsed_ms = timing.get("elapsed_ms")
    if elapsed_ms is not None:
        details.append(f"{elapsed_ms} ms")

    # The branch's change set against origin/main, across every run — not this run's.
    for label, bucket in (
        ("DHF on the branch", artifacts.get("items_changed") or {}),
        ("files on the branch", artifacts.get("files_changed") or {}),
    ):
        created = len(bucket.get("created") or [])
        updated = len(bucket.get("updated") or [])
        deleted = len(bucket.get("deleted") or [])
        if created or updated or deleted:
            details.append(f"{label}: +{created} ~{updated} -{deleted}")

    prefix = "ERROR" if result.get("outcome") == "tool_error" else "OK"
    return f"{prefix} {stage_label} {verb} for {cr_id} ({', '.join(details)})."


def _raise_for_outcome_error(result: dict) -> None:
    """Exit non-zero for tool_error and completed_with_errors outcomes."""
    if result.get("outcome") in ("tool_error", "completed_with_errors"):
        raise click.exceptions.Exit(1)


def _print_prompt(assemble, cr_id: str, dhf: Path) -> None:
    """Markdown, not JSON: the reader is an agent following it, not a parser."""
    warnings: list[dict] = []
    click.echo(assemble(cr_id, dhf_path=dhf, warnings=warnings))
    for w in warnings:
        click.echo(f"WARN [prompt] {w.get('message', w)}", err=True)


def register(main):
    build = main.commands["build"]

    @build.command("plan")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR to design: its item cascade and impact analysis.")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="The PR this run belongs to, in CI: revise if a reviewer asked for changes, then "
                       "commit and push the result to its branch. Without it, local files "
                       "change and nothing is committed.")
    @click.option("--prompt", "print_prompt", is_flag=True, default=False,
                  help="Print the stage's instructions, with this CR's DHF context, for an "
                       "agent that is already running, instead of starting a model.")
    @click.pass_context
    def change_plan(ctx: click.Context, cr_id: str, pr_number: int | None,
                    print_prompt: bool) -> None:
        """Draft the DHF item cascade and impact analysis for a CR, with a model.

        Drives the V-model (CRS→SYS→SYSARCH/RISK/RCM→SRS→SWDD). The model writes
        items with `medharness item`; deterministic validation and one fix pass
        run afterwards, then a design review.

        The model is MEDHARNESS_DESIGN_MODEL (and MEDHARNESS_DESIGN_REVIEW_MODEL
        for the review) as "provider:model", else Anthropic with ANTHROPIC_MODEL.
        Locally it edits files and commits nothing; in CI, --pr N commits and
        pushes to that PR, revising when a reviewer asked for changes.
        """
        from medharness.services.cr_generation import generate_dhf  # noqa: PLC0415
        from medharness.workflows.cr_state import assert_cr_active  # noqa: PLC0415
        dhf: Path = ctx.obj["dhf"]
        try:
            assert_cr_active(LocalDHFAdapter(ctx.obj["dhf"]), cr_id)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        except (FileNotFoundError, OSError):
            pass  # DHF config not loadable yet; generate_dhf will surface the error
        if print_prompt:
            from medharness.services.prompt_assembly import _assemble_generate_dhf_prompt
            _print_prompt(_assemble_generate_dhf_prompt, cr_id, dhf)
            return
        result = generate_dhf(cr_id, dhf, pr_number=pr_number)
        emit(result)
        click.echo(
            _format_summary("DHF cascade", "revised" if pr_number else "generated", cr_id, result),
            err=True,
        )
        for error in result.get("errors") or []:
            click.echo(f"  FAIL ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        _raise_for_outcome_error(result)

    @build.command("code")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR whose approved design to implement.")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="The PR this run belongs to, in CI: revise if a reviewer asked for changes, then "
                       "commit and push the result to its branch. Without it, local files "
                       "change and nothing is committed.")
    @click.option("--prompt", "print_prompt", is_flag=True, default=False,
                  help="Print the stage's instructions, with this CR's DHF context, for an "
                       "agent that is already running, instead of starting a model.")
    @click.pass_context
    def change_implement(ctx: click.Context, cr_id: str, pr_number: int | None,
                         print_prompt: bool) -> None:
        """Write the code and tests for a CR's approved design, with a model.

        Reads the CR's implementation_notes and the items it affects, and
        implements them following the repository's CLAUDE.md.

        The model is MEDHARNESS_DEVELOP_MODEL (and MEDHARNESS_CODE_REVIEW_MODEL
        for the review) as "provider:model", else Anthropic with ANTHROPIC_MODEL.
        Locally it edits files and commits nothing; in CI, --pr N commits and
        pushes to that PR, revising when a reviewer asked for changes.
        """
        from medharness.services.cr_generation import generate_code  # noqa: PLC0415
        from medharness.workflows.cr_state import assert_cr_active  # noqa: PLC0415
        dhf: Path = ctx.obj["dhf"]
        try:
            assert_cr_active(LocalDHFAdapter(ctx.obj["dhf"]), cr_id)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        except (FileNotFoundError, OSError):
            pass  # DHF config not loadable yet; generate_code will surface the error
        if print_prompt:
            from medharness.services.prompt_assembly import _assemble_develop_prompt
            _print_prompt(_assemble_develop_prompt, cr_id, dhf)
            return
        result = generate_code(cr_id, dhf, pr_number=pr_number)
        emit(result)
        click.echo(_format_summary("Implementation", "revised" if pr_number else "generated", cr_id, result), err=True)
        for error in result.get("errors") or []:
            click.echo(f"  FAIL ({error['field']}): {error['issue']}", err=True)
            click.echo(f"    Fix: {error['fix']}", err=True)
        _raise_for_outcome_error(result)

    @build.command("release")
    @click.option("--version", "version", required=True, metavar="VERSION",
                  help="The version being released, e.g. 1.2.0.")
    @click.option("--out-dir", required=True, type=click.Path(file_okay=False, path_type=Path),
                  help="Where to write the baseline, BOM, SBOM and evidence bundle.")
    @click.option("--write", is_flag=True, default=False,
                  help="Record a REL item in the DHF. Happens only when every check "
                       "passed; without it the DHF is not changed.")
    @click.option("--cr", "cr_ids", multiple=True, metavar="CR_ID",
                  help="A CR to include (repeatable). Default: every completed CR "
                       "not yet in a release.")
    @click.option("--manifest", "manifest_paths", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path), metavar="PATH",
                  help="Dependency manifest whose packages the BOM lists beside the "
                       "SOUP register (repeatable).")
    @junit_option("JUnit XML to include as test evidence: a file, or a directory "
                  "searched for *.xml (repeatable).")
    @click.option("--doc-format", type=click.Choice(["html", "pdf"]), default="html",
                  show_default=True,
                  help="Format of the bundled specifications. PDF needs "
                       "medharness[docs] plus cairo/pango.")
    @click.pass_context
    def build_release_cmd(ctx, version, out_dir, write, cr_ids, manifest_paths,
                          junit_paths, doc_format) -> None:
        """Build everything one release needs (IEC 62304 §9).

        Checks the DHF — coverage gaps fail here — and that every included CR is
        completed and every open defect assessed. Writes to --out-dir the release
        baseline, the software BOM, a CycloneDX SBOM, the specifications,
        traceability, test evidence, and a manifest hashing every file.

        With --write, and only if all of that passed, records the REL item.
        """
        from medharness.services.release_baseline import build_release

        result = build_release(
            ctx.obj["dhf"], version, out_dir,
            manifest_paths=list(manifest_paths), cr_ids=list(cr_ids),
            junit_paths=collect_junit_paths(junit_paths),
            doc_format=doc_format, write=write,
        )
        click.echo(json.dumps(result))
        for warning in result["warnings"]:
            click.echo(f"WARN [release] {warning}", err=True)
        for err in result["errors"]:
            click.echo(f"FAIL [release] {err}", err=True)
        if result["errors"]:
            note = " No REL item was recorded." if write else ""
            click.echo(f"Release {version} is not ready: {len(result['errors'])} "
                       f"problem(s).{note}", err=True)
            sys.exit(1)
        rel_note = f", recorded as {result['rel_uid']}" if result["rel_uid"] else " (dry run)"
        click.echo(
            f"OK build release {version}{rel_note}: {len(result['cr_ids'])} CR(s), "
            f"{result['soup_count']} SOUP item(s), {len(result['artifacts'])} file(s) "
            f"in {out_dir}.",
            err=True,
        )

    @build.command("soup")
    @click.option("--manifest", "manifest_paths", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  metavar="PATH", help="Manifest to read (repeatable). Auto-discovers when omitted.")
    @click.option("--from-command", "extra_commands", multiple=True, metavar="CMD",
                  help="External tool emitting NDJSON components (repeatable).")
    @click.pass_context
    def build_soup(ctx, manifest_paths, extra_commands) -> None:
        """Reconcile SOUP items from the project's dependency manifests.

        IEC 62304 §8.1.2 wants the SOUP a release ships to be the SOUP it
        documents. A package in a lockfile with no SOUP item is an undocumented
        component; a SOUP item no manifest resolves is a record of something that
        no longer ships.
        """
        from medharness.services.soup_sync import sync_soup_items

        result = sync_soup_items(
            ctx.obj["dhf"], list(manifest_paths),
            extra_commands=list(extra_commands),
        )
        click.echo(json.dumps(result))
        written = (f" ({len(result.get('items_created', []))} created, "
                   f"{len(result.get('items_updated', []))} updated)")
        click.echo(
            f"OK build soup{written}: +{len(result.get('to_create') or [])} new, "
            f"~{len(result.get('to_update') or [])} drift, "
            f"{len(result.get('orphans') or [])} orphan(s), "
            f"{result.get('matched_count', 0)} matched.", err=True,
        )
        if result.get("outcome") == "completed_with_errors":
            for err in result.get("errors") or []:
                click.echo(f"  FAIL: {err}", err=True)
            sys.exit(1)
