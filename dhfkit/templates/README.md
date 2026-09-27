# DHF — {{project_name}}

The Design History File: one YAML file per item, checked by
[MedHarness](https://github.com/itercharles/MedHarness).

> **The items here are samples.** Replace them with your product's real
> requirements, risks and change requests before relying on this DHF.

## Layout

```
DHF/
├── config/
│   └── global.yaml        # the project name, and anything you change
├── items/                 # one YAML file per item, one directory per type
└── documents/specs/       # specifications rendered by `dhfkit doc`
```

The item types, lifecycles, required links and templates are defaults from
MedHarness. To change one, put an override next to `global.yaml`: a key in
`global.yaml` replaces the default key, and `config/doc_types/<type>.yaml`
replaces the default type of that code.

## Item types

| Code | Item | Links to |
|------|------|----------|
| `UC` | Use case | — |
| `CRS` | Customer requirement | `derives_from` → UC |
| `SYS` | System requirement | `satisfies` → CRS, `implements` → RCM |
| `SYSARCH` | System architecture decision | `design` → SYS |
| `SRS` | Software requirement | `derives_from` → SYS |
| `MODULE` | Software module | — |
| `SWDD` | Software detailed design | `implements` → SRS, `module` → MODULE |
| `RISK` | Risk | — |
| `RCM` | Risk control measure | `mitigates` → RISK, `implements` → SYS |
| `SOUP` | Third-party component | — |
| `CR` | Change request | `affected_items`, `affected_risk_items` → RISK/RCM, `target_release` → REL |
| `DEF` | Defect | `affected_items`, `found_in_release` → REL |
| `REL` | Release record | `included_items` → CR |

A link is written on the child and points up to its parent. Which links are
required is `required_traceability` — a default you can override in `global.yaml`.

## Commands

```bash
dhfkit item list --type SYS
dhfkit item create --type SYS --data '{"title": "…", "satisfies": ["CRS-001"]}'
dhfkit item update SYS-001 --data '{"title": "…"}'
medharness verify dhf        # does the V-model hold together
```

Run them from the directory that contains `DHF/`, or pass `--dhf PATH` before
the command.
