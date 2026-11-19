# Configuration

What you can change in `DHF/config/`, and what each change reaches.

## Changing the defaults

MedHarness ships defaults: 13 item types (CRS, UC, SYS, SYSARCH, MODULE, SRS, SWDD, RISK, RCM, SOUP, CR, DEF, REL), the links that are required, and the specification templates. Your project overrides any of them by adding a file under `DHF/config/` or `DHF/documents/specs/`. Where you have a file it is used instead; where you have none, the default applies, so upgrading `medharness` upgrades everything you have not overridden.

An override **replaces** the default it names, never merges into it. Start from a copy of the default (in [`dhfkit/templates`](../dhfkit/templates)) and edit.

| To change | Do this |
|---|---|
| A setting, such as which links are required | Write that key in `DHF/config/global.yaml`. Your value is the whole value |
| The fields or lifecycle of an item type | Add `DHF/config/doc_types/srs.yaml` with `code: SRS` |
| An item type of your own | Add a file there with a new `code` |
| An item type you do not use | List it in `omit_doc_types` in `global.yaml` |
| A specification template | Add a file of the same name in `DHF/documents/specs/` |

An overridden type stops following the package's changes to it, so override only what you change.

### Your own types and relationships

A relationship is a field on the child item, with the types it may point at. This adds hardware requirements that refine a SYS:

```yaml
# DHF/config/doc_types/hwr.yaml
code: HWR
name: Hardware Requirement
prefix: HWR-
directory: hwr
properties:
- id
- name: title
  format: short_text
- name: content
  format: long_text
- name: refines
  format: relationship        # or item_multiselect; both hold item IDs
  description: Hardware requirement refines a system requirement
  target_types: [SYS]         # a link to anything else is refused
```

```yaml
# DHF/config/global.yaml
required_traceability:        # replaces the default list: copy the rules you keep
- source_type: HWR
  direction: upstream
  field: refines
  target_type: SYS
  min_count: 1
traceability_matrices:        # the chains coverage is checked along
- name: Hardware chain
  description: SYS to HWR
  path: [SYS, HWR]
```

`required_traceability: []` turns every rule off. A rule may add `or_covered_by: <type>` as a second way to be satisfied; the default `SYS satisfies CRS` has `or_covered_by: RCM`.

Everything reads this: `verify dhf`, `item create|update` (they refuse a link to a missing item or the wrong type), the release's traceability reports, and `build plan`. Only what is configured is checked.

**Say what belongs at each level.** A type's `description` is your definition of its tier: what belongs there, what does not, one example. `build plan` gives it to the model, which decides from it where a new item sits. The defaults say it for a typical product; in your own copy of a type, write it in your words.

## What `verify impact` reads

- The CR's `affected_items`: the branch's DHF changes must be exactly that list, apart from the CR itself. `--code-path PATH` also requires a change under PATH.
- `impact_depth` in `global.yaml`: how many typed links out from a changed item it looks for an item that depends on it and was neither changed nor listed in the CR's `reviewed_items`. `0` turns it off.
- A MODULE lists the paths it owns in `paths` (a trailing `/` is a directory). A changed file then reaches the SWDD items that name that module, and the requirements they implement, which must be changed or listed in `reviewed_items`.
- Once any module declares `paths`, a changed file no module owns fails too, unless `unowned_paths` in `global.yaml` exempts it (by default docs, CI workflows, Markdown, licences and lockfiles). Until then the code check is off.

## Items from another system

Every command reads one YAML file per item under `DHF/items/`. A team whose requirements live in another tool exports them into that format and runs the same commands. `medharness verify dhf` checks the export.

- The file is any name ending `.yaml`; the folder does not matter.
- `id` is required, and its prefix (`SRS-`) picks the type.
- Only fields the type declares are allowed; declare an extra one by overriding the type first.
- A link is a field of format `relationship` or `item_multiselect`: IDs of a type its `target_types` accepts.

To read a tool directly instead, an installed adapter is chosen with `store:` in `global.yaml` ([architecture.md](architecture.md#item-adapters)). `verify impact`, `build plan` and `build code` need the items in Git and refuse another store.
