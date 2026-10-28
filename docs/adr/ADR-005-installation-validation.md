# ADR-005: Validating an Installation Where It Is Used

**Status:** Accepted
**Date:** 2026-10-26 (proposed), 2026-10-27 (accepted)

## Context

Step 4 of [iteration 4](../charter.md#iterations). A manufacturer that relies on
MedHarness in its quality system validates it for that use (ISO 13485 §4.1.6), and
IEC/TR 80002-2 expects part of that evidence to come from the environment the tool
runs in, not only from the vendor's. MedHarness now has the vendor's half:

- its own DHF, `DHF/`, with 49 requirements and 171 test points for the high-risk gates
  (20 more, with 83 points, for the medium-risk commands are proposed in #465), which the
  suite verifies and CI checks with `verify dhf --strict` and `verify tests --strict`
  ([validation.md](../validation.md));
- a release that runs the suite on its tag and attaches the JUnit results, a test summary
  and `medharness-<version>-tested-with.txt`, the dependency versions the suite passed
  with (#463).

What a user cannot do is show that **their** install behaves the same. The tests are not
in the wheel (`pyproject.toml` excludes `tests*`), most of them need `pytest`, a
checkout and `dev` extras, and nothing compares what is installed with what was tested.
The inventory's "Validation where it is used" row is still **Missing**.

The [seeded-omission](../../tests/integration/test_seeded_omissions_are_stopped.py)
fixture is the closest thing to what a user needs: one honest change request, in a
scratch git repository, that passes every pre-merge gate, and one case per omission
that a gate must stop. It answers the question a user's validation asks, "does this tool
stop what it is relied on to stop, here", in seconds and without the user's data.

## Decision

### One command: `medharness build validation`

```
medharness build validation --out-dir DIR [--doc-format html|pdf]
```

It runs a fixed validation set against a scratch project in a temporary directory,
writes a report to `--out-dir`, answers with the report's fields as JSON on stdout, and
exits 1 when any point fails or cannot run.

It goes in **`build`**, not `verify`, and no fifth group is added:

- **It writes an artifact.** The verb rule in `CLAUDE.md` is that a command which writes
  items, code or artifacts is a `build`; the report is a record the user files, like the
  approval sheet `build approvals` writes.
- **It is not a gate on the project.** A `verify` command judges the user's DHF and
  working tree and answers with the five-key envelope; this reads neither, and its answer
  (a result per requirement and test point, versions, platform) does not fit the
  envelope.
- **A new group costs more than it buys.** `validate` would be one command in a group of
  its own, and the four groups are a guarded contract
  (`tests/guards/test_cli_boundary_is_documented.py`, the table in `CLAUDE.md`,
  `docs/interface.md`).

`--dhf` is accepted, as by every command, and ignored by this one; the report says so,
since a user may expect it to validate their DHF.

### What it runs: a curated validation set, shipped in the package

A new package, `medharness/validation/`, holds the set. It ships in the wheel; the test
suite does not.

- **Cases, not the suite.** Each case is a plain function that builds or reuses a
  scratch project and runs the real CLI through `CliRunner`, as the interface tests do,
  and declares the requirement and test points it exercises (`SRS-016`, `T1`). No case
  needs `pytest` or the `dev` extras, so the command works on a plain
  `pip install medharness`.
- **Built on the seeded-omission fixture.** The honest change request, and the omissions
  the gates stop, move into the package as the set's scratch project. The integration
  test keeps running them, so the fixture has one definition.
- **High-risk points first.** The set covers the test points of the 49 high-risk
  requirements whose cases need nothing the user may not have: git always; `ssh-keygen`
  for the signing points (SRS-016 to SRS-023); WeasyPrint's native libraries only with
  `--doc-format pdf`. Medium-risk points are a later addition (open question 2).
- **One source of truth.** A guard runs every case under pytest, with `dhf_links` and
  `dhf_testing` taken from the case, so the release's JUnit contains each validation
  point and `verify tests --strict` holds it to the requirement. A case that drifts from
  its requirement fails CI, not a user's validation.
- **Never the user's project.** Everything happens in a temporary directory that is
  removed afterwards; `osv.dev` and GitHub are never contacted.

A point whose tool is missing is reported as `not_run`, with the tool named, and the
overall result is `incomplete`: a validation that skipped the signing points has not
validated signing.

### What the report holds

`validation-report.html` (or `.pdf`), rendered from a new specification template through
the same path as the specifications and the approval sheet, and the same content as JSON
on stdout, declared as a model in `medharness/results.py`:

| Section | Content |
|---|---|
| Result | `passed`, `failed` or `incomplete`; when and where it ran |
| Installation | `medharness` version; each file of the installed distribution checked against the hashes in its `RECORD` |
| Configuration | each installed dependency's version beside the version in the release's `tested-with` list, marked equal, different or missing |
| Environment | OS and version, architecture, Python version and implementation, `git` and `ssh-keygen` versions, whether WeasyPrint's libraries load |
| Results | per requirement: its ID, title and risk; per test point: its text, the case that exercised it, `passed` / `failed` / `not_run`, and the failure message |
| Release evidence | the release's version and commit, and the names of the evidence files attached to its GitHub Release |
| Record | a hash of the report, and blank fields for who performed and reviewed the validation |

A dependency at another version than the tested one does not fail the command; it is
listed as a deviation. Whether a deviation matters is the user's assessment, and the
points still show whether the tool behaves with it.

### How it ties to the release evidence

The release build writes `medharness/validation/release.json` into the wheel: the
version, the tagged commit, and the contents of `medharness-<version>-tested-with.txt`,
which `uv export` produces from the lockfile in the job that builds the wheel. The command
therefore compares against the configuration the release was tested with without
downloading anything, and the requirement text in the report comes from the release's own
`DHF/`, exported into the same file. A user who keeps the release's JUnit file can match
each point in their report with the same point in the vendor's run: same ID, same test
point, same case name.

### What it deliberately does not do

- It does not check the user's DHF, configuration, CI pipeline or approvers list; the
  `verify` commands do that every day.
- It does not validate `build plan` or `build code`, which are out of scope
  ([validation.md](../validation.md)).
- It does not run the full suite, and it is not the vendor's verification. It shows the
  installed tool stops what it is relied on to stop in this environment.
- It does not decide that the tool is validated for the user's intended use. The report
  is the user's evidence; the risk assessment, the decision and the signature are theirs.
- It does not reach the network, and it does not install, pin or upgrade anything.

## Consequences

- A user can produce validation evidence for the installed version, in their
  environment, with one command and no checkout, and re-run it on every upgrade, where
  the changelog and the requirement IDs show which gates changed.
- The seeded-omission fixture and the validation cases move from `tests/` into the
  package. They become shipped code, held to the import boundary (`dhfkit` does not import
  them) and covered by the guards on what a command prints.
- The wheel grows by the cases, a template and `release.json`; the build job gains a step
  that writes `release.json`, and a release built without it has no configuration to
  compare against, which the command reports rather than guesses.
- `docs/interface.md`, the `CLAUDE.md` command table and `docs/validation.md` gain the
  command; `docs/adopting.md` gains how to run it and file the report.
- Each validation point is maintained twice over: as a requirement test point in `DHF/`
  and as a case. The guard keeps them in step, at the cost that changing a high-risk
  behaviour means changing its case in the same pull request.

## Decisions on the open questions

Proposed with six open questions; accepted with these answers.

1. **Name.** `build validation`. It writes a report, so it is a `build`, and the four
   groups stay as they are.
2. **Scope of the set.** Every test point of the high-risk requirements (SRS-002 to
   SRS-050, 171 points), each exercised through the CLI. A point that the suite verifies
   only below the CLI today gets a case that runs the command. Medium-risk points are a
   later addition. The set is built over several pull requests: the command, the report,
   `release.json` and the seeded-omission cases first, then the remaining points gate by
   gate. Until the last of them lands, the report lists the points the set does not
   exercise yet, and a result can be `passed` only when it exercised them all.
3. **Tested configuration.** Embedded in the wheel as `release.json`. The release job that
   runs the suite writes it, beside the `tested-with` file it comes from, and the job that
   builds the wheel puts it into the package before building.
4. **Missing tools.** A point whose tool is missing is `not_run` and the result is
   `incomplete`, which exits 1.
5. **Report format.** HTML by default, PDF with `--doc-format pdf` and the `docs` extra, as
   for the specifications and the approval sheet.
6. **Requirement text in the wheel.** Exported into `release.json`: each high-risk
   requirement's ID, title, risk and test points. `DHF/` stays out of the package.

Two details follow from shipping the cases as code. A case checks with an explicit
`check()` that raises, never with `assert`, which `python -O` removes. And the cases run
under pytest from `tests/integration/test_the_validation_set_passes.py`, which carries
each case's `dhf_links` and `dhf_testing`, so `verify tests --strict` holds the set to the
requirements and the release's JUnit contains every validation point.
