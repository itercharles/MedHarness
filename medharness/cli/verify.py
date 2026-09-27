"""`verify` — ask the DHF whether a change is sound. Reads the DHF, nothing else."""

from __future__ import annotations

import re
from pathlib import Path

import click

import medharness._helpers as _h
from medharness.cli.output import details, emit, render_envelope
from medharness.services.ci import ci_structural_gate, ci_test_coverage_gate

_ITEM_ID_RE = re.compile(r"^([A-Z]+-\d+)")


def register(main):
    verify = main.commands["verify"]

    @verify.command("dhf")
    @click.option("--fail-on-uncovered", is_flag=True, default=False,
                  help="Exit non-zero when items lack downstream coverage. "
                       "Without it, coverage gaps are reported as WARN only.")
    @click.pass_context
    def verify_dhf(ctx: click.Context, fail_on_uncovered: bool) -> None:
        """Check the DHF holds together: schema, links, cycles, coverage.

        Always blocking: schema errors, required-traceability failures, and
        dangling links (a link whose target ID does not exist).

        Advisory by default: coverage gaps — pass --fail-on-uncovered to enforce.
        """
        effective_dhf = ctx.obj["dhf"]
        result = ci_structural_gate(dhf_path=effective_dhf,
                                     fail_on_uncovered=fail_on_uncovered)
        emit(result)
        r = details(result)["results"]
        dhf_arg = f"--dhf {effective_dhf}"
        if "schema" in r:
            s = r["schema"]
            if s["passed"]:
                click.echo(f"PASS [schema]: {s.get('item_count', 0)} items valid", err=True)
            else:
                click.echo("FAIL [schema]: validation errors found", err=True)
                for err in s.get("errors", []):
                    click.echo(f"  ✗ {err}", err=True)
                    m = _ITEM_ID_RE.match(str(err))
                    if m:
                        iid = m.group(1)
                        click.echo(f"    Fix: dhfkit {dhf_arg} item update {iid}"
                                   f" --data '{{\"<field>\": \"<value>\"}}'", err=True)
        for gap in r.get("verification_gaps", []):
            click.echo(f"WARN [verification] {gap['id']}: {gap['issue']}", err=True)
            click.echo(f"      Fix: dhfkit {dhf_arg} item update {gap['id']}"
                       f" --data '{{\"verification_criteria\": \"<how this is verified>\"}}'",
                       err=True)
        if "traceability" in r:
            t = r["traceability"]
            req = t.get("required", {})
            if not req.get("passed", True):
                for f in req.get("failures", []):
                    click.echo(f"FAIL [required] {f['id']}: {f['issue']}", err=True)
                    click.echo(f"    Fix: add 'dhf_links: [<parent-id>]' to"
                               f" {f['id']}.yaml, or:", err=True)
                    click.echo(f"         dhfkit {dhf_arg} item update {f['id']}"
                               f" --data '{{\"dhf_links\": [\"<parent-id>\"]}}'", err=True)
            for message in [e for e in result["errors"] if "target does not exist" in e]:
                click.echo(f"FAIL [dangling] {message}", err=True)
                click.echo("    Fix: correct the ID in the source item, or create the "
                           "target. The link exists but resolves to nothing.", err=True)
            for message in [e for e in result["errors"] if e.startswith("Traceability cycle:")]:
                # The gate's own wording, not a second rendering of it: two
                # spellings of one finding is two findings to a reader.
                click.echo(f"FAIL [cycle] {message}", err=True)
                click.echo("    Fix: the V-model is directed. Remove whichever link "
                           "reverses the chain so each item has an origin.", err=True)

            # Uncovered items are advisory unless --fail-on-uncovered is set; label
            # them WARN so a green build never prints FAIL.
            gap_label = "FAIL" if fail_on_uncovered else "WARN"
            for c in t.get("coverage", []):
                click.echo(f"{'PASS' if c['passed'] else gap_label} [coverage] "
                           f"{c['parent_type']}→{c['child_type']}: "
                           f"{c['covered']}/{c['total']} covered", err=True)
                if not c["passed"]:
                    click.echo(f"    Fix: dhfkit {dhf_arg} item list"
                               f" --type {c['child_type']} to find uncovered items,"
                               f" then add dhf_links to their YAML.", err=True)
                    if not fail_on_uncovered:
                        click.echo("         Advisory only — pass --fail-on-uncovered"
                                   " to block the build on this.", err=True)
        if "coverage" in r:
            for row in r["coverage"].get("pairs", []):
                if row.get("error"):
                    # Without this the line read as a coverage shortfall, which
                    # sent people looking for missing items rather than a typo.
                    click.echo(f"FAIL [gate] {row['parent_type']}→{row['child_type']}: "
                               f"{row['error']}", err=True)
                    continue
                if row.get("skipped"):
                    click.echo(f"SKIP [gate] {row['parent_type']}→{row['child_type']}: "
                               f"{row['skipped']}", err=True)
                    continue
                click.echo(f"{'PASS' if row.get('passed') else 'FAIL'} [gate] "
                           f"{row['parent_type']}→{row['child_type']}: "
                           f"{row['covered']}/{row['total']} covered", err=True)
        if not result["passed"]:
            raise click.ClickException("DHF validation failed.")

    @verify.command("tests")
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path),
                  help="Directory of JUnit XML results (repeatable).")
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="A JUnit XML results file (repeatable).")
    @click.option("--require-method", is_flag=True, default=False,
                  help="Make a requirement with no declared verification_method fail. "
                       "Warns by default, so a project adding the field is not blocked.")
    @click.pass_context
    def verify_tests(ctx: click.Context,
                         junit_dirs: tuple[Path, ...], junit_files: tuple[Path, ...],
                         require_method: bool = False) -> None:
        """Check each requirement is verified by the method it declares.

        A requirement declaring Test needs a passing JUnit case linked to it;
        declared test points each need a covering case.
        """
        effective_dhf = ctx.obj["dhf"]
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = ci_test_coverage_gate(dhf_path=effective_dhf, junit_paths=junit_paths,
                                       require_method=require_method)
        emit(result)
        dhf_arg = f"--dhf {effective_dhf}"
        # The rows below print per-type coverage; the envelope's warnings are
        # about the gate as a whole and have no row to be printed beside.
        for message in result.get("warnings") or []:
            click.echo(f"WARN [test-coverage] {message}", err=True)
        rows = details(result)["results"]
        if not rows:
            # Every detail loop below iterates `results`; with none, the envelope
            # is the only place the reason exists. Without this, a missing
            # --junit-dir failed with "Test coverage gaps found." — pointing at
            # coverage when nothing had been read.
            render_envelope(result, "test-coverage")
        for row in rows:
            if row["passed"]:
                click.echo(f"PASS [test-coverage] {row['type']}: "
                           f"{row['covered']}/{row['total']} requirements covered", err=True)
            else:
                click.echo(f"FAIL [test-coverage] {row['type']}: "
                           f"{row['covered']}/{row['total']} requirements covered", err=True)
                for uid in row.get("uncovered", []):
                    click.echo(f"      ↳ uncovered: {uid}", err=True)
                    click.echo(f"        Fix: add 'dhf_links: [{uid}]' to a test case, or:", err=True)
                    click.echo(f"             dhfkit {dhf_arg} item create --type TC"
                               f" --data '{{\"title\": \"Test {uid}\", \"dhf_links\": [\"{uid}\"]}}'", err=True)
        for row in details(result).get("testing_points", []):
            if row["passed"]:
                click.echo(
                    f"PASS [test-coverage] {row['req_id']} test points: {row['covered']}/{row['total']} covered",
                    err=True,
                )
            else:
                click.echo(
                    f"FAIL [test-coverage] {row['req_id']} test points: {row['covered']}/{row['total']} covered",
                    err=True,
                )
                for pt in row.get("uncovered", []):
                    click.echo(f"      ↳ uncovered test point: {pt}", err=True)
        if not result["passed"]:
            raise click.ClickException("Test coverage gaps found.")


    @verify.command("completion")
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID",
                  help="The CR to close.")
    @click.option("--junit-dir", "junit_dirs", multiple=True, type=click.Path(file_okay=False, path_type=Path),
                  help="Directory of JUnit XML results for the items this CR touched (repeatable).")
    @click.option("--junit", "junit_files", multiple=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  help="A JUnit XML results file for the items this CR touched (repeatable).")
    @click.pass_context
    def verify_completion(
        ctx: click.Context,
        cr_id: str,
        junit_dirs: tuple[Path, ...],
        junit_files: tuple[Path, ...],
    ) -> None:
        """Check a CR delivered what it proposed: its items created and verified.

        Reads proposed_new_items from the CR item, checks each proposed type was
        created in the DHF, then runs the verification completeness gate over the
        items this CR touched — its affected_items and the items matching its
        proposals — so a CR is not charged with the DHF's existing gaps.

        Reads only the working tree, so it runs on the branch as well as on main.
        Run it on the branch to block the merge: the CR fields and the proposed
        items settle there. Run it again on main for the half that
        can differ — the tests re-run against whatever else landed meanwhile.

        Exits non-zero when any proposed items are missing or unverified.
        """
        from medharness.services.ci import cr_closure_gate

        effective_dhf = ctx.obj["dhf"]
        junit_paths = _h._collect_junit_paths(junit_files, junit_dirs)
        result = cr_closure_gate(cr_id=cr_id, dhf_path=effective_dhf,
                                 junit_paths=junit_paths)
        emit(result)

        for field in details(result).get("incomplete_cr_fields", []):
            click.echo(f"FAIL [completion] {field['issue']}", err=True)
        for item in details(result).get("missing_items", []):
            click.echo(
                f"FAIL [completion] {item['type']}: {item.get('issue', 'proposed item not found')}",
                err=True,
            )
        for item in details(result).get("verification_gaps", []):
            click.echo(f"FAIL [completion] {item['id']}: no verification_method declared", err=True)
        for item in details(result).get("unverified_test", []):
            click.echo(f"FAIL [completion] {item['id']}: Test method declared but no passing TC linked", err=True)
        for item in details(result).get("manual_review_required", []):
            methods = ", ".join(item.get("methods", []))
            click.echo(f"WARN [completion] {item['id']}: {methods} — requires manual sign-off record", err=True)

        click.echo(result["summary"], err=True)
        if not result["passed"]:
            raise click.ClickException(f"CR {cr_id} closure verification failed.")

    @verify.command("soup")
    @click.option("--manifest", "manifest_paths", multiple=True,
                  type=click.Path(exists=True, dir_okay=False, path_type=Path),
                  metavar="PATH",
                  help="Dependency manifest to compare the register against (repeatable). "
                       "Auto-discovers when omitted.")
    @click.option("--fail-on-drift", is_flag=True, default=False,
                  help="Make an undocumented or misversioned component fail the gate. "
                       "Warns by default, so a project backfilling its register is not blocked.")
    @click.option("--offline-mode", type=click.Choice(["fail", "warn"]), default="fail",
                  help="Behaviour when osv.dev is unreachable. 'warn' keeps the gate "
                       "passing for air-gapped or proxy-restricted pipelines.")
    @click.pass_context
    def verify_soup(
        ctx: click.Context,
        manifest_paths: tuple[Path, ...],
        fail_on_drift: bool,
        offline_mode: str,
    ) -> None:
        """Check the SOUP register matches what ships, and is not known-vulnerable.

        Compares the register against the dependency manifests, then each item
        against the OSV database. A package in a manifest with no SOUP item, or
        at a different version, warns unless --fail-on-drift is passed.

        SOUP items must have an 'ecosystem' field (e.g. PyPI, npm) to be checked.
        Exits non-zero if any unresolved vulnerabilities are found.

        A vulnerability the team has assessed can be recorded on the SOUP item so it
        no longer blocks, per IEC 62304 §8.1.2 — both 'id' and 'rationale' are required:

            accepted_vulns:
              - id: GHSA-xxxx-yyyy-zzzz
                rationale: "Affected API is not reachable from our code paths."

        Newly published vulnerabilities still block, because acceptance is per-ID.

        Outputs structured JSON to stdout; human-readable messages to stderr.
        """
        from medharness.services.ci import soup_gate

        effective_dhf = ctx.obj["dhf"]
        result = soup_gate(effective_dhf, offline_mode=offline_mode,
                           manifest_paths=list(manifest_paths), fail_on_drift=fail_on_drift)
        emit(result)

        for entry in details(result).get("accepted", []):
            click.echo(
                f"ACCEPTED [soup-vuln] {entry['soup_id']} ({entry['name']}@{entry['version']}): "
                f"{entry['vuln_id']} — {entry['rationale']}",
                err=True,
            )

        render_envelope(result, "soup-vuln")
        if details(result).get("drift", {}).get("undocumented") or \
                details(result).get("drift", {}).get("misversioned"):
            click.echo("    Fix: medharness --dhf DHF build dhf --write, then commit. "
                       "Pass --fail-on-drift to block the build on this.", err=True)
        click.echo(result["summary"], err=True)
        if not result["passed"]:
            raise click.ClickException("SOUP check failed.")
