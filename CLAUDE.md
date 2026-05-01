# CLAUDE.md

## Project

CompliantFlow — open-source design-controlled development harness for medical software.

## Repo Responsibility

| Repo | Purpose |
|------|---------|
| This repo (`CompliantFlow`) | Harness CLI, CI gate logic, scaffolding templates |
| [`CompliantFlow-DHF`](https://github.com/compliantflow/compliantflow-dhf) | AI-native DHF substrate |

## Key Rules

- PR title must include a CR ID
- Shared types first — define model before feature
- `ci test-coverage` enforces requirement→test coverage
- `ci evidence bundle` produces audit evidence on merge to main
- See [README.md](README.md) for product overview
- See [ARCHITECTURE.md](ARCHITECTURE.md) for regulated vs execution layer boundaries
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow
