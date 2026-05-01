# CompliantFlow

**An open-source design-controlled development harness for medical software.**

CompliantFlow is the harness layer in a two-repo delivery model. It scaffolds
product-side CI, evaluates requirement-to-test coverage from JUnit evidence,
and assembles runtime evidence bundles from normal engineering activity.

`CompliantFlow-DHF` is the companion DHF substrate. It owns the controlled DHF
templates, item schemas, lifecycle rules, traceability structure, and the
`dhf_util` package. Formal product documents live there, not in this repo.

---

## Repository Role

| Repo | Role |
|------|------|
| `CompliantFlow` | OSS harness package, CI gates, init scaffolding, agent entrypoints |
| `CompliantFlow-DHF` | AI-native DHF substrate, `dhf_util`, controlled document templates |
| Product repo | source code, tests, build outputs |
| DHF repo | requirements, architecture, risk, change, traceability records |

The harness does not replace the DHF. It connects product-side execution to
controlled DHF structure.

---

## What This Repo Does

- scaffolds product-side files with `compliantflow init`
- runs `ci test-coverage` against JUnit evidence
- generates `ci evidence bundle` runtime outputs
- supports CR-linked product workflows and agent context

---

## Canonical Formal Documents

Formal product direction and process documents live in the DHF substrate and
generated DHF repository:

- `DHF/documents/specs/customer_requirement_specification.md`
- `DHF/documents/specs/architecture_design_specification.md`
- `DHF/documents/plans/development_plan.md`

Use this repo for harness behavior and implementation details. Use the DHF-side
documents above for canonical product requirements, architecture, and process.

---

## Quick Start

```bash
git clone https://github.com/compliantflow/compliantflow
cd CompliantFlow
pip install -e .
compliantflow init
```

`init` writes product-side workflow files locally and fetches the DHF template
from `CompliantFlow-DHF` at runtime.

Full walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md)

---

## Core Workflow

1. Create or update a CR in the DHF repo.
2. Update controlled design content in the DHF repo before or alongside code changes.
3. Implement product changes in the product repo with the CR ID in the PR title.
4. Run `ci test-coverage` against JUnit evidence.
5. Let CI generate the evidence bundle on merge to `main`.

---

## Stable CLI Surface

```text
compliantflow init

compliantflow ci test-coverage
compliantflow ci evidence bundle
compliantflow ci release consume-artifact
compliantflow ci release assemble

compliantflow review-pr
compliantflow context
compliantflow cr workflow ...
```

Developer-facing commands may evolve, but the harness remains focused on
product-side orchestration rather than DHF ownership.

---

## Related Docs

- [GETTING_STARTED.md](GETTING_STARTED.md) for install and onboarding
- [ARCHITECTURE.md](ARCHITECTURE.md) for harness and substrate boundaries
- [PROJECT_STATUS.md](PROJECT_STATUS.md) for current surface stability
- [SUPPORT.md](SUPPORT.md) for support channels

---

## License

MIT — see [LICENSE](LICENSE).
