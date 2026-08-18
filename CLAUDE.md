# CLAUDE.md

## Project

MedHarness — open-source tooling for design-controlled development.
Includes `dhfkit`, the DHF/document/traceability engine.

## Guiding Documents

Before proposing or implementing any significant change, read:

- [`docs/architecture.md`](docs/architecture.md) — package boundaries, CR workflow
  topology, layer responsibilities, and test organisation. Do not violate the
  `dhfkit` → `medharness` import boundary.

## CLI Boundary

| CLI | Owns |
|-----|------|
| `dhfkit` | Item CRUD, validate, doc generate, report, soup-sync, release-baseline |
| `medharness` | AI CR workflow (generate-dhf, develop-cr), CI gates, scaffolding, approval gating |

`medharness dhf` exposes only AI-harness context commands (`context implementation/for-stage/overview`).
All DHF data operations use `dhfkit --dhf DHF <command>`.

## Repo Responsibility

| Directory | Purpose |
|-----------|---------|
| `medharness/` | Harness CLI, CI gate logic, scaffolding |
| `dhfkit/` | DHF engine: items, config, traceability, doc generation, SOUP sync, release baseline |
| `dhfkit/templates/` | Starter DHF scaffold — config, specs, plans, sample items, CI workflow |
| `docs/` | Architecture docs and adopting guide |
| `tests/unit/` | Unit tests |
| `tests/integration/` | Integration tests |
| `tests/contract/` | Contract tests |
| `dhfkit/tests/` | dhfkit tests |

## Key Rules

- Product-formal docs are canonical in generated DHF repos, not here
- `dhfkit` has no dependency on `medharness` — the engine can be used standalone
- `ci test-coverage` enforces requirement-to-test coverage in consumer repos
- `ci evidence bundle` produces runtime evidence on merge to `main`
- All new `ci` commands must: output structured JSON to stdout, write
  human-readable summaries to stderr only, and exit non-zero on failure
- Do not add comments to self-explanatory code. Only comment when the WHY is
  non-obvious: a hidden constraint, a workaround, an external API contract, or
  behavior that would surprise a reader unfamiliar with the context.
- Every code change must be accompanied by tests. If a change genuinely cannot
  be tested (e.g., prompt text, LLM-dependent behavior), state explicitly why
  it is untestable and what manual verification step is required instead.
- If a change affects documented behavior, update the relevant documentation in
  the same commit or PR — docs and code ship together.
- Keep code minimal. No speculative abstractions, no over-engineering. Three
  similar lines is better than a premature abstraction.
- When encountering a bug or unexpected behavior, find the root cause and fix
  it. Do not add workarounds, fallbacks, or defensive patches that mask the
  underlying problem.

## Session Start

At the start of every new request, run `git fetch origin && git checkout main && git pull`
before reading files or making changes, unless the user specifies a different branch.

## Release Process

Releases are fully automated via `.github/workflows/release.yml` using PyPI Trusted Publishing (OIDC — no token needed).

Steps:
1. Open a PR to `main` with the version bump in `pyproject.toml` and a `CHANGELOG.md` entry
2. Merge the PR
3. **Only after the PR is merged**, push the tag:

```bash
git tag v0.X.0 && git push origin v0.X.0
```

GitHub Actions then: runs preflight checks → builds wheel + sdist → publishes to PyPI → attaches wheel to the GitHub Release.

> **Critical**: the tag must point to the current tip of `origin/main`. Pushing the tag
> before the changelog PR is merged will fail the preflight "tag == main tip" check and
> block the publish. Always merge first, tag second.

## Test Environment

The repo has a `.venv` at the root. `pytest.ini` sets `pythonpath = .` so no
`PYTHONPATH` prefix is needed.

```bash
.venv/bin/pytest dhfkit/tests/ tests/ -q --ignore=dhfkit/tests/test_cli_doc_export.py
```

`test_cli_doc_export.py` requires `libgobject` (WeasyPrint native lib) — skip it locally.
