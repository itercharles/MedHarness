"""Init and upgrade commands — Click declarations only."""

import json
import click
from pathlib import Path


def register(main):
    @main.command("init")
    def init_cmd() -> None:
        """Scaffold a DHF and AI-harness structure in the current directory.

        Takes no prompts — the project name is derived from the directory name.
        Existing files are not overwritten.
        """
        from medharness.workflows.init import run_init
        run_init()

    @main.command("upgrade")
    @click.option("--apply", is_flag=True, default=False,
                  help="Write updated files. Without this flag, only reports differences.")
    @click.option("--project-dir", "project_dir", default=".",
                  type=click.Path(file_okay=False, path_type=Path),
                  help="Project root directory (default: current directory).")
    def upgrade_cmd(apply: bool, project_dir: Path) -> None:
        """Show or apply scaffold template updates for an existing project.

        Compares CI workflow, AI prompts, spec templates, and doc-type configs
        against the installed MedHarness version. DHF items, global.yaml, and
        AI-harness/context.md are never modified.

        Outputs structured JSON to stdout; human-readable messages to stderr.
        Exits non-zero when there are outdated or missing files (even without --apply).
        """
        from medharness.workflows.upgrade import apply_upgrade, check_upgrade

        result = apply_upgrade(project_dir) if apply else check_upgrade(project_dir)
        click.echo(json.dumps(result))

        for f in result.get("outdated", []):
            click.echo(f"OUTDATED {f['file']} (+{f['added_lines']}/-{f['removed_lines']} lines)", err=True)
        for f in result.get("missing", []):
            click.echo(f"MISSING  {f['file']}", err=True)
        for f in result.get("unavailable", []):
            click.echo(f"UNAVAILABLE {f['file']} — template {f['template']} is not in this"
                       f" medharness installation", err=True)
        for f in result.get("applied", []):
            click.echo(f"UPDATED  {f}", err=True)

        click.echo(result["summary"], err=True)
        if result.get("outdated") or result.get("missing"):
            if not apply:
                raise click.ClickException("Scaffold files are out of date. Run 'medharness upgrade --apply' to update.")
