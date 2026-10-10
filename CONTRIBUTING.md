# Contributing to MedHarness

Open a standard GitHub issue or PR. The repository's own history and
`CHANGELOG.md` are the record of what changed and why; the DHF a project keeps is
what `medharness init` writes, from `dhfkit/templates/`.

## Development Setup

```bash
git clone https://github.com/itercharles/MedHarness
cd MedHarness
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/ dhfkit/tests/ -q
```

`pip install -e ".[dev]"` installs `medharness` from this repo with test dependencies.
No separate clone or install is needed.

## PR Conventions

- Branch naming: `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`
- PR title follows [Conventional Commits](https://www.conventionalcommits.org/):
  `type: description` — for example `fix: detect dangling traceability links`.
  Maintainers working a CR may scope it as `feat(CR-042): description`; external
  contributors do not need a CR ID.
- Body: change summary, DHF files updated, validation run, manual testing remaining

### PR Type Labels

Maintainers apply one of these labels before merging:

| Label | Version impact | When to use |
|-------|---------------|-------------|
| `breaking` | MAJOR | CLI, templates, scaffold output, or public API changes |
| `feature` | MINOR | New backward-compatible capability |
| `fix` | PATCH | Bug fixes, doc corrections |
| `internal` | None | Refactoring, test improvements, no user-visible change |

## When to Write a Design Doc

An ADR (using [docs/adr/ADR-TEMPLATE.md](docs/adr/ADR-TEMPLATE.md)) is required when:

- Adding or removing a CLI subcommand
- Modifying the scaffold output structure
- Modifying template directories or template variable contracts
- Modifying `dhfkit`'s public import API
- Modifying config schema compatibility
- Modifying release artifact structure
- Changing the role or usage patterns of the reference example project

Bug fixes, doc corrections, and pure internal refactoring do not require a design
doc but still require test coverage.

## Before Submitting

```bash
.venv/bin/pytest tests/ dhfkit/tests/ -q
```
