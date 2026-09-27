"""Analysis over a set — the questions a single-item store cannot answer.

`dhfkit` holds records. These commands take them together and compare them
against something else: the links against each other, a change against the risk
graph, the SOUP register against the manifests a build actually resolves.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


def register(main):
    build = main.commands["build"]

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
        import medharness._helpers as _h
        from medharness.services.release_baseline import build_release

        result = build_release(
            ctx.obj["dhf"], version, out_dir,
            manifest_paths=list(manifest_paths), cr_ids=list(cr_ids),
            junit_paths=_h._collect_junit_paths(junit_files, junit_dirs),
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

