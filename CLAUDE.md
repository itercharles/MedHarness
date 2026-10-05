# CLAUDE.md

## Project

MedHarness — open-source tooling for design-controlled development.
Includes `dhfkit`, the DHF storage and document engine.

## Guiding Documents

Before proposing or implementing any significant change, read:

- [`docs/architecture.md`](docs/architecture.md) — package boundaries, CR workflow
  topology, layer responsibilities, and test organisation. Do not violate the
  `dhfkit` → `medharness` import boundary.

## CLI Boundary

One CLI, `medharness`. `dhfkit` is its storage engine: a library with no
dependency on `medharness`, and no CLI of its own.

| Group | Touches | Commands |
|-------|---------|----------|
| `item` | one DHF item at a time | `list` · `get` · `create` · `update` · `transition` |
| `verify` | reads the DHF and the working tree | `dhf` · `tests` · `soup` · `completion` · `changes` |
| `build` | writes items, code or artifacts | `plan` · `code` · `soup` · `release` |
| `init` | scaffolds a project | — |

`tests/guards/test_cli_boundary_is_documented.py` checks this table against the
live command tree.

### What each verb means

A command is a `verify` if it only judges, a `build` if it writes. Every command
runs locally; `--pr` on `build plan|code` is the only thing that is CI-specific.

| Verb | Reads | Examples |
|------|-------|----------|
| `verify` | what is on the machine — the DHF and the working tree, never GitHub | `dhf`, `tests`, `soup`, `completion`, `changes` |
| `build` | whatever it needs; **writes** items, code, or artifacts | `plan`, `code`, `soup`, `release` |

Approval is not a command: GitHub's branch protection (required approvals,
stale approvals dismissed on push) enforces it on the server, where a PR cannot
edit the check away.

`tests/guards/test_gates_sit_where_they_belong.py` enforces the line.

`--dhf PATH` goes before the command and defaults to `DHF`; no command takes its own.

## Repo Responsibility

| Directory | Purpose |
|-----------|---------|
| `medharness/` | Harness CLI, CI gate logic, scaffolding |
| `dhfkit/` | The storage engine, a library: items, config, schema validation, doc generation, SBOM |
| `dhfkit/templates/` | The defaults every DHF reads (`config/`, `specs/`), the sample items `init` copies, and the CI recipe the docs publish |
| `docs/` | Architecture docs and adopting guide |
| `tests/unit/` | Unit tests — logic worth isolating: parsers, judges, mappings |
| `tests/guards/` | Checks on the repo itself: import boundaries, documented commands, packaging, mock contracts |
| `tests/integration/` | Interface tests — a command run against a real project, in a real repository |
| `tests/contract/` | Interface tests — the CLI and scaffold as a caller sees them |
| `dhfkit/tests/` | dhfkit tests |

## Key Rules

- Product-formal docs are canonical in generated DHF repos, not here
- `dhfkit` has no dependency on `medharness` — the engine can be used standalone
- `verify tests` enforces requirement-to-test coverage in consumer repos
- `build release` produces the release evidence, at release time
- Every command must: output structured JSON to stdout, write human-readable
  summaries to stderr only, and exit non-zero on failure. The one exception is
  `build plan|code --prompt`, which prints Markdown for an agent to follow
- Do not add comments to self-explanatory code. Only comment when the WHY is
  non-obvious: a hidden constraint, a workaround, an external API contract, or
  behavior that would surprise a reader unfamiliar with the context.
  State the constraint, do not retell the bug. A comment that narrates how a
  fault was found ("used to fall off the end of this chain and let the
  transition through") belongs in the commit message; the code needs the one
  line that says what must hold. Two lines is usually the ceiling.
- Test at the interface. A change in behavior comes with a test that runs the
  command (`CliRunner`, or a subprocess for exit codes and streams) and asserts
  stdout, the exit code and the files it changed. Spend the cases on what
  breaks: bad input, a missing or malformed DHF, empty and boundary values, git
  or network failing. A defect in a helper shows up at the interface, so that is
  where it is caught; a reader can find the helper from there.
- Unit-test only logic worth isolating: a parser, a judge, or a mapping with
  many branches, where enumerating the edge cases directly is cheaper than
  reaching them through a command. A function that mostly moves values around
  gets no unit test, and neither does a change an interface test already fails
  on. Guards (`tests/guards/`) check invariants of the repository itself.
- If a change genuinely cannot be tested (e.g., prompt text, LLM-dependent
  behavior), state explicitly why it is untestable and what manual verification
  step is required instead.
- If a change affects documented behavior, update the relevant documentation in
  the same commit or PR — docs and code ship together.
  The command reference, gate table and report fields in `docs/interface.md` are
  generated from the CLI and from the result models in `medharness/results.py`:
  after changing a command, its options or help text, or what it answers with,
  run `python scripts/generate_interface.py` (a guard fails the build otherwise).
  A new key in a report goes into its model first; tests validate real output
  against the models.
- Keep code minimal. No speculative abstractions, no over-engineering. Three
  similar lines is better than a premature abstraction.
- Do not invent what nothing uses yet. This applies to output as much as to
  code: a field returned "in case a caller wants it" is a shape that drifts,
  and every gate's `details` was wrong in three documented places by the time
  it was removed. Ship the answer, extend when something needs more.
- Before writing an algorithm, check whether a current dependency already has
  it. `networkx` is one, and cycle detection was hand-rolled twice anyway.
- Delete a field that is structurally always empty, along with everything that
  reads it. "Preserved for compat" on a value nothing can ever write is dead
  code with a reason attached, and the readers rot around it.
- When encountering a bug or unexpected behavior, find the root cause and fix
  it. Do not add workarounds, fallbacks, or defensive patches that mask the
  underlying problem.

## Session Start

At the start of every new request, run `git fetch origin && git checkout main && git pull`
before reading files or making changes, unless the user specifies a different branch.

## Release Process

Releases are fully automated via `.github/workflows/release.yml` using PyPI Trusted Publishing (OIDC — no token needed).

Steps:
1. Open a PR to `main` with the version bump in `pyproject.toml`, the pinned
   version in the README's CI snippet if it has one, and a `CHANGELOG.md` entry
2. Run `uv lock` — the version is recorded in `uv.lock` too, and CI's
   `uv lock --check` blocks the build when the two disagree
3. Merge the PR
4. **Only after the PR is merged**, pull, then push the tag:

```bash
git checkout main && git pull && git tag v0.X.0 && git push origin v0.X.0
```

   The `git pull` is not optional. Merging in the GitHub UI leaves local `main`
   behind, so tagging in the right order still puts the tag on the wrong commit
   — v0.21.0 landed on the v0.20.0 commit this way.

GitHub Actions then: runs preflight checks → builds wheel + sdist → publishes to PyPI → attaches wheel to the GitHub Release.

If the publish step fails with `ReadTimeout` on `upload.pypi.org`, that is the
OIDC token exchange timing out, before anything was uploaded: re-run only the
failed job (`gh run rerun <run-id> --failed`) rather than re-tagging.

> **Critical**: the tag must point to the current tip of `origin/main`. Pushing the tag
> before the changelog PR is merged will fail the preflight "tag == main tip" check and
> block the publish. Always merge first, tag second.

## Test Environment

The repo has a `.venv` at the root. `pytest.ini` sets `pythonpath = .` so no
`PYTHONPATH` prefix is needed.

```bash
.venv/bin/pytest dhfkit/tests/ tests/ -q
```

PDF tests skip themselves when WeasyPrint's native libraries are missing. CI installs them
and sets `MEDHARNESS_REQUIRE_PDF=1`, which turns that skip into a failure, so the PDF path cannot go
unverified there.
