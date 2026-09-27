"""`build` — produce DHF items, code, and delivery artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from dhfkit.local_adapter import LocalDHFAdapter
from medharness.cli.options import collect_junit_paths
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

    for label, bucket in (
        ("DHF", artifacts.get("items_changed") or {}),
        ("files", artifacts.get("files_changed") or {}),
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


def register(main):
    build = main.commands["build"]

    @build.command("plan")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR to design: its item cascade and impact analysis.")
    @click.option("--pr", "pr_number", default=None, type=int, metavar="N",
                  help="PR number — revision mode: revise DHF cascade based on review comments")
    @click.pass_context
    def change_plan(ctx: click.Context, cr_id: str, pr_number: int | None) -> None:
        """Draft the DHF item cascade and impact analysis for a CR, with a model.

        Drives the V-model (CRS→SYS→SYSARCH/RISK/RCM→SRS→SWDD). The model writes
        items through the dhfkit CLI; deterministic validation and one fix pass
        run afterwards, then a design review.

        The model is MEDHARNESS_DESIGN_MODEL (and MEDHARNESS_DESIGN_REVIEW_MODEL
        for the review) as "provider:model", else Anthropic with ANTHROPIC_MODEL.
        Pass --pr N to revise the items from that PR's review comments.
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
                  help="PR number — revision mode: revise implementation based on review comments")
    @click.option("--ci-failures", "ci_failures_path", default=None,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="JSON file containing structured CI failure output to feed back to Claude")
    @click.pass_context
    def change_implement(ctx: click.Context, cr_id: str, pr_number: int | None,
                      ci_failures_path: Path | None) -> None:
        """Write the code and tests for a CR's approved design, with a model.

        Reads the CR's implementation_notes and the items it affects, and
        implements them following the repository's CLAUDE.md.

        The model is MEDHARNESS_DEVELOP_MODEL (and MEDHARNESS_CODE_REVIEW_MODEL
        for the review) as "provider:model", else Anthropic with ANTHROPIC_MODEL.
        Pass --pr N to revise the code from that PR's review comments.
        Pass --ci-failures PATH to feed structured CI failure JSON back as a
        targeted correction prompt instead of free-text PR review comments.
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
        ci_failures: dict | None = None
        if ci_failures_path is not None:
            try:
                ci_failures = json.loads(ci_failures_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise click.ClickException(f"Could not read --ci-failures file: {exc}") from exc
        result = generate_code(cr_id, dhf, pr_number=pr_number, ci_failures=ci_failures)
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
    @click.option("--junit-dir", "junit_dirs", multiple=True,
                  type=click.Path(file_okay=False, path_type=Path),
                  help="Directory of JUnit XML to include as test evidence (repeatable).")
    @click.option("--junit", "junit_files", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="A JUnit XML file to include as test evidence (repeatable).")
    @click.option("--traceability-type", "traceability_types", multiple=True, metavar="CODE",
                  help="Doc type to render a traceability matrix for (repeatable). "
                       "Default: UC, CRS, SYS, SRS, SWDD.")
    @click.option("--doc-format", type=click.Choice(["html", "pdf"]), default="html",
                  show_default=True,
                  help="Format of the bundled specifications. PDF needs "
                       "medharness[docs] plus cairo/pango.")
    @click.option("--run-id", default="", help="CI run ID, recorded in the evidence manifest.")
    @click.option("--run-url", default="", help="CI run URL, recorded in the evidence manifest.")
    @click.option("--commit", "commit_sha", default="",
                  help="Commit SHA, recorded in the evidence manifest.")
    @click.pass_context
    def build_release_cmd(ctx, version, out_dir, write, cr_ids, manifest_paths, junit_dirs,
                          junit_files, traceability_types, doc_format,
                          run_id, run_url, commit_sha) -> None:
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
            junit_paths=collect_junit_paths(junit_files, junit_dirs),
            traceability_types=traceability_types,
            run_id=run_id, run_url=run_url, commit_sha=commit_sha,
            doc_format=doc_format, write=write,
        )
        click.echo(json.dumps(result))
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

    @build.command("dhf")
    @click.option("--manifest", "manifest_paths", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  metavar="PATH", help="Manifest to read (repeatable). Auto-discovers when omitted.")
    @click.option("--from-command", "extra_commands", multiple=True, metavar="CMD",
                  help="External tool emitting NDJSON components (repeatable).")
    @click.option("--write", is_flag=True, default=False,
                  help="Create or update SOUP items (report-only by default).")
    @click.pass_context
    def build_dhf(ctx, manifest_paths, extra_commands, write) -> None:
        """Reconcile SOUP items from the project's dependency manifests.

        IEC 62304 §8.1.2 wants the SOUP a release ships to be the SOUP it
        documents. A package in a lockfile with no SOUP item is an undocumented
        component; a SOUP item no manifest resolves is a record of something that
        no longer ships.
        """
        from medharness.services.soup_sync import sync_soup_items

        result = sync_soup_items(
            ctx.obj["dhf"], list(manifest_paths),
            write=write,
            extra_commands=list(extra_commands),
        )
        click.echo(json.dumps(result))
        written = (
            f" ({len(result.get('items_created', []))} created, "
            f"{len(result.get('items_updated', []))} updated)" if write else " (dry-run)"
        )
        click.echo(
            f"OK build dhf{written}: +{len(result.get('to_create') or [])} new, "
            f"~{len(result.get('to_update') or [])} drift, "
            f"{len(result.get('orphans') or [])} orphan(s), "
            f"{result.get('matched_count', 0)} matched.", err=True,
        )
        if result.get("outcome") == "completed_with_errors":
            for err in result.get("errors") or []:
                click.echo(f"  FAIL: {err}", err=True)
            sys.exit(1)
