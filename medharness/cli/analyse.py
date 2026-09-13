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
    @main.group("release")
    def release() -> None:
        """Release records under IEC 62304 §9."""

    @release.command("baseline")
    @click.option("--version", "version", required=True, metavar="VERSION",
                  help="Release version string (e.g. 1.0.0)")
    @click.option("--manifest", "manifest_paths", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  metavar="PATH", help="requirements.txt or package.json for BOM (repeatable)")
    @click.option("--cr", "cr_ids", multiple=True, metavar="CR_ID",
                  help="CR to include (repeatable; auto-collected if omitted)")
    @click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path),
                  default=Path("."), show_default=True,
                  help="Directory to write release-baseline.json and software-bom.json")
    @click.option("--write", is_flag=True, default=False,
                  help="Create a REL item in the DHF (dry-run by default)")
    @click.option("--author", default="ci", show_default=True, metavar="NAME")
    @click.pass_context
    def release_baseline_cmd(
        ctx: click.Context, version: str, manifest_paths: tuple[Path, ...],
        cr_ids: tuple[str, ...], out_dir: Path, write: bool, author: str,
    ) -> None:
        """Build an IEC 62304 §9 release baseline.

        Verifies all included CRs are in `completed` state, collects a
        software BOM from DHF SOUP items and manifest packages, and writes
        release-baseline.json and software-bom.json to --out-dir.
        Pass --write to also create a REL item in the DHF.
        CRs are auto-collected (completed, not yet in any REL) when --cr is omitted.
        """
        from medharness.services.release_baseline import build_release_baseline
        dhf = ctx.obj.get("dhf")
        if dhf is None:
            raise click.ClickException("--dhf is required when not set globally")
        dhf = Path(dhf)
        result = build_release_baseline(
            dhf, version, list(manifest_paths), list(cr_ids), out_dir,
            write=write, author=author,
        )
        click.echo(json.dumps(result))
        if result.get("outcome") == "completed_with_errors":
            for err in result.get("errors") or []:
                click.echo(f"  FAIL: {err}", err=True)
            sys.exit(1)
        rel_note = f" → {result['rel_uid']}" if result.get("rel_uid") else ""
        click.echo(
            f"OK release-baseline {version}{rel_note}: "
            f"{len(result.get('cr_ids', []))} CR(s), "
            f"{result.get('soup_count', 0)} SOUP item(s), "
            f"{len(result.get('artifacts', []))} artifact(s) written.",
            err=True,
        )

    @main.command("soup-sync")
    @click.option("--manifest", "manifest_paths", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  metavar="PATH", help="Manifest to read (repeatable). Auto-discovers when omitted.")
    @click.option("--from-command", "extra_commands", multiple=True, metavar="CMD",
                  help="External tool emitting NDJSON components (repeatable).")
    @click.option("--write", is_flag=True, default=False,
                  help="Create or update SOUP items (report-only by default).")
    @click.option("--author", default="ci", show_default=True, metavar="NAME")
    @click.pass_context
    def soup_sync(ctx, manifest_paths, extra_commands, write, author) -> None:
        """Compare the SOUP register against the project's dependency manifests.

        IEC 62304 §8.1.2 wants the SOUP a release ships to be the SOUP it
        documents. A package in a lockfile with no SOUP item is an undocumented
        component; a SOUP item no manifest resolves is a record of something that
        no longer ships.
        """
        from medharness.services.soup_sync import sync_soup_items

        dhf = ctx.obj.get("dhf")
        if dhf is None:
            raise click.ClickException("--dhf is required when not set globally")
        result = sync_soup_items(
            Path(dhf), list(manifest_paths),
            write=write, author=author,
            extra_commands=list(extra_commands),
        )
        click.echo(json.dumps(result))
        written = (
            f" ({len(result.get('items_created', []))} created, "
            f"{len(result.get('items_updated', []))} updated)" if write else " (dry-run)"
        )
        click.echo(
            f"OK soup-sync{written}: +{len(result.get('to_create') or [])} new, "
            f"~{len(result.get('to_update') or [])} drift, "
            f"{len(result.get('orphans') or [])} orphan(s), "
            f"{result.get('matched_count', 0)} matched.", err=True,
        )
        if result.get("outcome") == "completed_with_errors":
            for err in result.get("errors") or []:
                click.echo(f"  FAIL: {err}", err=True)
            sys.exit(1)

