# Architecture

> **Stability:** Stable
> **Last reviewed:** 2026-09-30

How the code is organised, for contributors. What a user calls is in the
[README](../README.md) and [interface.md](interface.md).

## Two packages, one install

| Package | CLI | Owns |
|---------|-----|------|
| `dhfkit` | — (a library) | Storage: item CRUD (an update rewrites only the fields whose value changed) and lifecycle, config and schemas, schema validation, dangling-link detection, document generation, JUnit parsing and the pytest plugin, the CycloneDX SBOM |
| `medharness` | `medharness` | Analysis and process: traceability over the whole item set, the gates, SOUP sync, releases, the AI change workflow, scaffolding |

There is one CLI, `medharness`; its `item` commands are thin wrappers over
`dhfkit`.

- `medharness` imports from `dhfkit`; `dhfkit` never imports from `medharness`.
- `medharness` uses only `dhfkit`'s public surface — no underscored names.

`tests/guards/test_package_boundary.py` enforces both.

Each top-level command group lives in the file named after it:
`medharness/cli/item.py`, `verify.py`, `build.py` and `init.py`. A new
command goes in the file of its verb. `cli/output.py` holds the JSON-to-stdout,
lines-to-stderr helpers every command shares. Each `verify` check sits in its own
module, `services/verify_<name>.py`, and answers in the envelope from
`services/envelope.py`.

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

The analysis in `medharness.services.traceability`, and the release's
traceability matrix in `medharness.services.traceability_report`, take a list
of items and a config, never a path. The commands reach items through the item
store: `medharness` calls `dhfkit.store.open_store` and sees only the `DHFStore`
interface, never the class behind it, which keeps the items wherever the
project's backend does — see [Item backends](#item-backends).
`tests/guards/test_the_business_layer_sees_only_the_store_interface.py` holds
that line.

The one place `medharness` writes DHF files directly is `init`, which creates
the skeleton. Everything else goes through the store — `tests/guards/test_storage_access_is_bounded.py` holds
that line.

## Item backends

The item store owns everything that is the same wherever items live: the
doc-type schema, link checks, ID allocation, the lifecycle, and the shape
callers get back. A **backend** owns only persistence, five methods
(`dhfkit.backend.ItemBackend`): `load_all`, `load_by_uid`, `save`, `delete`,
`used_ids`, plus `integrity_errors` and a `tracks_files` flag. The project's
`config/` and `documents/` stay in the repository whichever backend is chosen,
so the item types, links and rules are configured the same way for every store.

`DHF/config/global.yaml` chooses one:

```yaml
store:
  type: yaml        # the default; any other type is an installed backend
```

A backend is a package that registers an entry point in the `dhfkit.backends`
group, named for its `type`, and is called with `settings` (the rest of `store:`),
`config` and `dhf_root`. `tests/integration/test_a_store_that_is_not_files.py`
is the reference: an in-memory backend that passes the same commands.

What depends on items being files in Git, and so refuses another backend with a
message naming the store: `verify changes`, `build plan` and `build code`, which
read the branch's diff. Everything else — `item`, `verify dhf|tests|soup|completion`,
`build soup`, `build release` — runs on any backend.

## Defaults and overrides

`dhfkit/templates/config/` and `dhfkit/templates/specs/` are the defaults every
DHF reads: the 13 doc types, the lifecycle, the traceability rules, the
specification templates. `ProjectConfig.load` merges them with the project's own
config — each `global.yaml` key replaces the default key, a `doc_types/` file
replaces the default type of its `code`, `omit_doc_types` drops one — and the
document generator looks for a template in the project, then the package.

So a project holds only what it changes, and a new version's defaults reach it
by upgrading the package. `tests/guards/test_packaging_templates.py` builds the
wheel and requires every default to be in it.

## What `init` writes

```
<project>/
├── DHF/
│   ├── README.md                 # what the DHF is and how to edit it
│   ├── config/global.yaml        # the project name, and room for overrides
│   └── items/NN_type/            # one directory per item type, with a sample item
├── AGENTS.md                     # product context and the DHF steps, for any agent
├── CLAUDE.md                     # @AGENTS.md
└── .gitignore
```

`build plan` writes its design reviews to `docs/reviews/`, creating it on first
use. Specifications, traceability and the SBOM are rendered by `build release`
into its `--out-dir`, never into the DHF.
Placeholders: `{{project_name}}` (from the directory name) and
`{{medharness_version}}`.

The CI recipe, `dhfkit/templates/github/workflows/dhf.yml`, is **not** installed:
it names branches, runners and secrets that differ per project. It is published
through [adopting.md](adopting.md#setting-up-ci), and a test keeps the two
identical.

## The AI change workflow

```
CR (new) ─► build plan ─► design reviewed on the PR ─► build code ─► verify * ─► merge
```

The steps are the prompts in `medharness/prompts/`, run by one of two agents:
the one `build plan`/`build code` start (CI), or the one the engineer is already
using, which reads them from `--prompt` (local). There is one copy of the steps.

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
`medharness item transition`: `new → design → develop → completed`, `rejected`
from `new` or `design`, or `cancelled` from any of the three. `completed` is refused until `implementation_notes`,
`affected_risk_items` and `triage_result` are recorded. `build plan` and
`build code` refuse a CR that is `completed`, `rejected` or `cancelled`.

Each stage takes its model from `MEDHARNESS_{DESIGN|DESIGN_REVIEW|DEVELOP|CODE_REVIEW}_MODEL`
as `provider:model` — `anthropic` (the `claude` CLI, the default), `openai`,
`deepseek` — with `MEDHARNESS_{STAGE}_BASE_URL` for other endpoints.

### Where the code is

| Module | Does |
|---|---|
| `services/cr_generation.py` | Stage orchestration, model calls, PR feedback |
| `services/context.py` | What the model is told about the DHF for one CR: the whole DHF summarized until the CR records `affected_items`, then those items in full |
| `services/prompt_assembly.py` | Loads prompts from `medharness/prompts/` and renders `services/context.py` into them |
| `services/cr_impact.py` | Writes `affected_items` back onto the CR |
| `services/design_validation.py` | The deterministic check after each design pass |

## `verify changes`: a reader and a judge

`services/git.py` `validate_atomic_branch` reads the diff and hands plain values
to `judge_branch(cr_id, cr_item, dhf_item_changes, code_changes)`, which decides
and touches nothing. Test a rule by calling the judge with the values you want;
patch the reader only to test the reading itself.

## Tests

| Layer | Directory | Scope |
|-------|-----------|-------|
| Unit | `tests/unit/` | Logic worth isolating: parsers, judges, mappings |
| Guards | `tests/guards/` | The repository about itself: boundaries, documented commands, packaging |
| Integration | `tests/integration/` | A command run against a real project and repository: `init`, the CR workflow end to end |
| Contract | `tests/contract/` | The CLI and scaffold as a caller sees them |
| Engine | `dhfkit/tests/` | Storage: CRUD, validation, documents |
