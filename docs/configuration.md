# Configuration

Everything in `DHF/config/` that you can change, and what each change reaches.

## Changing the defaults

MedHarness reads two layers. The **defaults** ship inside the package: 13 item
types — CRS, UC, SYS, SYSARCH, MODULE, SRS, SWDD, RISK, RCM, SOUP, CR, DEF, REL —
each with its fields and lifecycle, plus the rules for which links are required
and the templates for the specifications. **Your project** adds files under
`DHF/config/` and `DHF/documents/specs/`. Where your project has one, it is used
instead of the default; where it has none, the default applies. That is why a new
project's `global.yaml` holds only its name, and why upgrading `medharness`
upgrades every default you have not overridden.

An override replaces the whole default it names; it never merges into it. Each
kind of default is overridden in its own place:

| To change | Do this | Example |
|---|---|---|
| A setting, such as which links are required | Write that key in `DHF/config/global.yaml`. Your value replaces the default value of that key, so copy the default value and edit it | `required_traceability: [...]` — your list is the whole list |
| The fields or lifecycle of an item type | Add `DHF/config/doc_types/srs.yaml` with `code: SRS`. It replaces the default SRS, so start from a copy of the default | give SRS a `hazard_ref` field |
| An item type of your own | Add a file in the same folder with a new `code` | `code: HWR` for hardware requirements |
| An item type you don't use | List its code in `omit_doc_types` in `global.yaml` | `omit_doc_types: [UC]` |
| A specification template | Add a file of the same name in `DHF/documents/specs/` | your own `requirements_specification.md.j2` |

Copy from the defaults in
[`dhfkit/templates/config/doc_types`](../dhfkit/templates/config/doc_types),
[`dhfkit/templates/config/global.yaml`](../dhfkit/templates/config/global.yaml)
and [`dhfkit/templates/specs`](../dhfkit/templates/specs).

The trade-off: an overridden item type stops following the package's changes to
that type, so override only what you change.

### Your own types and relationships

A relationship is a field on the child item, declared in its doc type with the
types it may point at. This adds hardware requirements that refine a SYS:

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
  target_types: [SYS]         # a link to anything else fails verify dhf and item create|update
```

```yaml
# DHF/config/global.yaml
required_traceability:        # replaces the default list, so copy the rules you keep
- source_type: HWR
  direction: upstream
  field: refines
  target_type: SYS
  min_count: 1
traceability_matrices:        # the chains: coverage is checked along them
- name: Hardware chain
  description: SYS to HWR
  path: [SYS, HWR]
```

A rule can name a second way to be satisfied with `or_covered_by: <type>`: the default
`SYS satisfies CRS` carries `or_covered_by: RCM`, so a system requirement either comes
from a customer need or is implemented for a risk control (an RCM that lists it under
`implements`). Write the list again without `or_covered_by` to require a CRS always, or
without the rule to drop it; `required_traceability: []` turns every rule off.

`item create` and `item update` refuse a link to an item that does not exist, so a
typo never reaches the DHF; `affected_items` is the exception, because it also names
items the branch deleted.

Everything reads this: `verify dhf` (dangling and wrong-type links, required links,
coverage), `item get` (`all_linked_uids`), the release's traceability reports (one per
matrix), and `build plan`, whose prompt describes your link fields and chains and
whose check expects an item it creates to get a child next along a chain. Only
what is configured is checked: a type with no `target_types` accepts any target.

**Say what belongs at each level.** A doc type's `description` is your own definition of
its tier: what belongs there, what does not, one example. `build plan` puts it in the
prompt ("What Belongs at Each Level"), and the model decides from it where a new item sits
and whether a change needs one at all. The defaults for UC, CRS, SYS, SRS and SYSARCH
say it for a typical product; a project with its own copy of those files adds a
`description:` key to them, in its own words. A type without one is left out.

Projects scaffolded before 0.37 carry full copies of the config and templates.
They keep working: each copy overrides the default it duplicates. To follow the
defaults again, delete the copies you have not changed.
