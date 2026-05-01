# CLAUDE.md

## Project

CompliantFlow — open-source design-controlled development harness for medical software.

## Repo Responsibility

| Repo | Purpose |
|------|---------|
| This repo (`CompliantFlow`) | Harness CLI, CI gate logic, scaffolding templates |
| `CompliantFlow-DHF` | AI-native DHF substrate and `dhf_util` source |

## Key Rules

- PR title must include a CR ID
- product-formal docs are canonical in the DHF repo, not here
- `ci test-coverage` enforces requirement-to-test coverage
- `ci evidence bundle` produces runtime evidence on merge to `main`
- see `DHF/documents/specs/customer_requirement_specification.md` in the DHF repo for product direction
- see `DHF/documents/specs/architecture_design_specification.md` in the DHF repo for canonical architecture
- see `DHF/documents/plans/development_plan.md` in the DHF repo for testing and process rules
