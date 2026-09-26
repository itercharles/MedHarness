# Architecture

> **Stability:** Stable
> **Last reviewed:** 2026-09-27

How the code is organised, for contributors. What a user calls is in the
[README](../README.md) and [interface.md](interface.md).

## Two packages, one install

| Package | CLI | Owns |
|---------|-----|------|
| `dhfkit` | `dhfkit` | Storage: item CRUD and lifecycle, config and schemas, schema validation, dangling-link detection, document generation, JUnit parsing and the pytest plugin, the CycloneDX SBOM |
| `medharness` | `medharness` | Analysis and process: traceability over the whole item set, the gates, SOUP sync, releases, the AI change workflow, scaffolding |

- `medharness` imports from `dhfkit`; `dhfkit` never imports from `medharness`.
- `medharness` uses only `dhfkit`'s public surface — no underscored names.

`tests/guards/test_package_boundary.py` enforces both.

## Storage versus analysis

The rule for which package a check belongs to is what a store can answer on
its own:

| Question | Belongs to |
|---|---|
| Is this item well-formed? | `dhfkit` |
| Do two files claim one ID? | `dhfkit` |
| Does this link name an item that exists? | `dhfkit` |
| Is every SYS covered by an SRS? | `medharness` |
| Does a traceability chain cycle? | `medharness` |
| Which risks does this change touch? | `medharness` |
| Are the links this doc type requires present? | `medharness` |

The analysis in `medharness.services.traceability` takes a list of items and a
config, never a path. **The commands, though, always read the YAML store**
(`dhfkit.local_adapter.LocalDHFAdapter`); nothing lets you hand them another
backend. Requirements kept in another system are checked by exporting them into
`DHF/items/` in the YAML format.

The one place `medharness` writes DHF files directly is scaffolding: `init`
creates the skeleton and `upgrade` keeps its templates current. Everything else
goes through the store — `tests/guards/test_storage_access_is_bounded.py` holds
that line.

## What `init` writes

```
<project>/
├── DHF/
│   ├── README.md                 # what the DHF is and how to edit it
│   ├── config/
│   │   ├── global.yaml           # project name, lifecycle states, traceability rules
│   │   ├── doc_types/*.yaml      # 13 item types: fields, links, lifecycle
│   │   └── soup-sources.yaml     # where the dependency manifests are
│   ├── items/NN_type/            # one directory per item type, with a sample item
│   └── documents/specs/          # Jinja2 templates and the stylesheet
├── CLAUDE.md                     # product context the AI stages read
└── .gitignore
```

`build plan` writes its design reviews to `docs/reviews/`, creating it on first
use. The source is `dhfkit/templates/`. Placeholders: `{{project_name}}` (from the
directory name) and `{{medharness_version}}`.

`upgrade` manages the 13 doc-type configs and the spec templates with their stylesheet — it reports
where they differ from the installed version and `--apply` rewrites them. It
seeds `soup-sources.yaml` if missing and never overwrites it. It never touches
`global.yaml`, the items, `DHF/README.md` or `CLAUDE.md`.

The CI recipe, `dhfkit/templates/github/workflows/dhf.yml`, is **not** installed:
it names branches, runners and secrets that differ per project. It is published
through [adopting.md](adopting.md#setting-up-ci), and a test keeps the two
identical.

## The AI change workflow

```
CR (new) ─► build plan ─► design reviewed on the PR ─► build code ─► verify * ─► merge
```

**`build plan`**

1. Triage: duplicate, out of scope, architecture conflict or too large. Writes
   `triage_result` on the CR.
2. V-model cascade: creates or updates items top-down — CRS → SYS → SYSARCH,
   RISK, RCM → SRS → SWDD — reading the relevant source before writing SWDD.
   Writes `affected_risk_items` on the CR.
3. Implementation plan into the CR's `implementation_notes`.
4. Deterministic validation (`verify dhf`), and one fix pass if it fails.
5. Design review, written to `docs/reviews/<CR>-Design-Review.md`; up to three
   fix-and-review cycles.
6. Records the items it changed as the CR's `affected_items`.

**`build code`**

1. Implements `implementation_notes`, using the SWDD items for module design.
2. Tags tests with the requirements they verify and runs `verify tests` until
   every requirement is covered.
3. Reconciles `implementation_notes` and SWDD if the code deviated.
4. Code review; up to three fix-and-review cycles.

Neither command moves the CR through its lifecycle. The project does, with
`dhfkit item transition`: `new → design → develop → completed`, or `rejected`
from `new` or `design`. `completed` is refused until `implementation_notes`,
`affected_risk_items` and `triage_result` are recorded. `build plan` and
`build code` refuse a CR that is `completed`, `rejected` or `cancelled`.

Each stage takes its model from `MEDHARNESS_{DESIGN|DESIGN_REVIEW|DEVELOP|CODE_REVIEW}_MODEL`
as `provider:model` — `anthropic` (the `claude` CLI, the default), `openai`,
`deepseek` — with `MEDHARNESS_{STAGE}_BASE_URL` for other endpoints.

### Where the code is

| Module | Does |
|---|---|
| `services/cr_generation.py` | Stage orchestration, model calls, PR feedback |
| `services/prompt_assembly.py` | Loads prompts from `medharness/prompts/` and adds DHF context |
| `services/cr_impact.py` | Writes `affected_items` back onto the CR |
| `services/design_validation.py` | The deterministic check after each design pass |

## Tests

| Layer | Directory | Scope |
|-------|-----------|-------|
| Unit | `tests/unit/` | One function or command |
| Guards | `tests/guards/` | The repository about itself: boundaries, documented commands, packaging |
| Integration | `tests/integration/` | `init`, the CR workflow end to end |
| Contract | `tests/contract/` | The CLI and scaffold as a caller sees them |
| Engine | `dhfkit/tests/` | Storage: CRUD, validation, documents |
