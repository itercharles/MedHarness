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
of items and a config, never a path. The commands reach items through
`dhfkit.store.open_store` and the `DHFStore` interface it returns; which adapter
holds them is invisible to a check — see [Item adapters](#item-adapters).

The one place `medharness` writes DHF files directly is `init`, which creates
the skeleton. Everything else goes through the store — `tests/guards/test_storage_access_is_bounded.py` holds
that line.

## Item adapters

Three layers separate the commands from wherever a DHF's items live:

```
Commands (medharness)   the checks and build steps — the business layer
   │  sees only the DHFStore interface, through open_store()
   ▼
ItemStore         what is the same for every system: reads DHF/config, checks an
   │              item's fields against its doc type, checks links, allocates IDs,
   │              runs the lifecycle, renders documents
   │  reaches items only through the DHFAdapter interface
   ▼
an adapter        one per system, one file each: how items are read and written
                  LocalDHFAdapter (dhfkit/local_adapter.py)  YAML files in the repository
                  JiraDHFAdapter  (a jira_adapter.py, when written)  Jira issues
```

- **`DHFStore`** (`dhfkit/store.py`) is what `medharness` depends on, with the
  `open_store(dhf_root)` factory. `medharness` never imports the class behind it,
  the adapters or the YAML loader, and
  `tests/guards/test_the_business_layer_sees_only_the_store_interface.py` fails the
  build if it does.
- **`ItemStore`** (`dhfkit/item_store.py`) implements `DHFStore`. Because the schema,
  links, IDs and lifecycle live here, they behave the same on every adapter, and
  an adapter does not reimplement them.
- **`DHFAdapter`** (`dhfkit/adapter.py`) is what a system implements: `load_all`,
  `load_by_uid`, `save` and `used_ids`, plus `integrity_errors` and a
  `tracks_files` flag. `LocalDHFAdapter` is the implementation for a DHF kept as
  files; another system adds a file beside it.

The project's `config/` (item types, links, rules, lifecycle) and `documents/`
stay in the repository whichever adapter is chosen, so they are configured the
same way for every system.

`DHF/config/global.yaml` chooses the adapter:

```yaml
store:
  type: yaml        # the default; any other type is an installed adapter
```

An adapter that is not in this repository is a package that registers an entry
point in the `dhfkit.adapters` group, named for its `type`; it is called with
`settings` (the rest of `store:`), `config` and `dhf_root`.
`tests/integration/test_a_store_that_is_not_files.py` is the reference: an
in-memory adapter that runs the same commands.

What depends on items being files in Git, and so refuses another adapter with a
message naming the store: `verify changes`, `build plan` and `build code`, which
read the branch's diff. Everything else — `item`, `verify dhf|tests|soup|completion`,
`build soup`, `build release` — runs on any adapter.

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
through [ci.md](ci.md#setting-up-ci), and a test keeps the two
identical.

## The AI change workflow

```
CR (new) ─► build plan ─► design reviewed on the PR ─► build code ─► verify * ─► merge
```

The steps are the prompts in `medharness/prompts/`, run by one of two agents:
the one `build plan`/`build code` start (CI), or the one the engineer is already
using, which reads them from `--prompt` (local). There is one copy of the steps.

**`build plan`**

1. Triage: duplicate, out of scope or architecture conflict. Writes
   `triage_result` on the CR; a change that spans several branches is approved
   as `large`, with a note on how to split it.
2. Characterise the change: the behaviour delta, its category, the ambiguities
   resolved.
3. Locate it: test files first (every requirement has a test), then a top-down
   drill with `item list --brief` and `--linked-to`, then `--match`.
4. Propagate: from the anchors, decide each item unchanged, updated or created
   beside, and queue the neighbours of every change — unchanged over update
   over create.
5. Gaps: a verdict for each of nine dimensions (product, requirements,
   architecture, risk, SOUP, test, regulatory, security, usability).
6. Write the items, run `verify dhf`, and record on the CR `affected_items`,
   `reviewed_items`, `affected_risk_items`, `impact_analysis` and
   `implementation_notes`.

After it, deterministic validation, and one fix pass if it fails; then the design
review, written to `docs/reviews/<CR>-Design-Review.md`, with up to three
fix-and-review cycles. The reviewer is also given each changed item's parent chain,
its siblings and any near-duplicate, and judges omission, overlap and conflict
against the CR's `impact_analysis`. The harness rewrites `affected_items` from the branch.

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
| `services/cr_generation.py` | The two stages, `generate_dhf` (`build plan`) and `generate_code` (`build code`) |
| `services/stage_run.py` | What the stages share: `Run` (steps, warnings, the session, the answer's shape), the model step, review parsing |
| `services/llm.py` | Running a model: provider config, the `claude` CLI, the OpenAI-compatible loop |
| `services/pr_feedback.py` | What a reviewer asked for on a PR, and pushing a run's work back to it |
| `services/context.py` | What the model is told about the DHF for one CR: the whole DHF summarized until the CR records `affected_items`, then those items in full |
| `services/prompt_assembly.py` | Loads prompts from `medharness/prompts/` and renders `services/context.py` into them |
| `services/cr_impact.py` | Writes `affected_items` back onto the CR |
| `services/design_validation.py` | The deterministic check after each design pass |

## `verify changes`: a reader and a judge

`services/verify_changes.py` `validate_atomic_branch` reads the diff and hands plain values
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
