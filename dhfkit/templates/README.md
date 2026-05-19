# DHF — Design History File for {{project_name}}

Scaffolded by [MedHarness](https://github.com/itercharles/MedHarness).

> **This repo contains starter sample content.** Replace all items, documents, and plans with your project's real requirements, architecture, risks, and change records before using this for a regulated product.

## Next Steps

1. Edit `AI-harness/context.md` with your product overview, regulatory class, and architecture constraints
2. Replace sample items under `DHF/items/` with your project's actual requirements
3. Adapt plan documents under `DHF/documents/plans/`
4. Run `dhfkit --dhf DHF validate schema` to verify, then commit and push

## Directory Layout

```
├── DHF/
│   ├── items/                # One YAML file per requirement/risk/CR item
│   │   ├── 00_uc/            # Use Cases
│   │   ├── 01_crs/           # Customer Requirements
│   │   ├── 02_sys/           # System Requirements
│   │   ├── 03_srs/           # Software Requirements
│   │   ├── 04_modules/       # Software Modules
│   │   ├── 05_swdd/          # Detailed Design
│   │   ├── 06_sysarch/       # System Architecture
│   │   ├── 07_cr/            # Change Requests
│   │   ├── 08_rel/           # Releases
│   │   ├── 09_soup/          # SOUP items
│   │   ├── 10_risk/          # Risks
│   │   ├── 11_rcm/           # Risk Control Measures
│   │   └── 12_def/           # Defects
│   ├── config/               # global.yaml + doc_types/*.yaml
│   ├── test-results/         # Automated test result records
│   └── documents/
│       ├── plans/            # Planning documents
│       └── specs/            # Generated specs + Jinja2 templates
├── AI-harness/
│   └── context.md            # Product context for AI agents — keep this current
├── .github/
│   ├── prompts/              # AI agent prompts for CR workflows
│   └── workflows/            # DHF-side CI
└── README.md
```

## Item Type Model

Items follow the V-model hierarchy. Each type has a fixed code prefix.

| Code | Name | One item per… |
|------|------|---------------|
| `UC` | Use Case | User goal or operating scenario |
| `CRS` | Customer Requirement | Stakeholder need |
| `SYS` | System Requirement | System-level behavioural obligation |
| `SRS` | Software Requirement | Software-level behavioural obligation |
| `MODULE` | Software Module | Software unit in the architecture decomposition |
| `SWDD` | Software Detailed Design | Design decisions for an SRS requirement within a module |
| `SYSARCH` | System Architecture | System-level design decision for a SYS requirement |
| `RISK` | Risk | Identified hazard or hazardous situation |
| `RCM` | Risk Control Measure | Mitigation for a risk, implemented as a system requirement |
| `CR` | Change Request | Proposed change driving a DHF update cycle |
| `SOUP` | SOUP | Third-party dependency (IEC 62304 §5.3.3) |
| `REL` | Release | Software release record (IEC 62304 §9) |
| `DEF` | Defect | Tracked problem or non-conformance |

### Traceability Links

Links are written on the child item and point upward to the parent.

| Link field | Written on | Points to |
|------------|-----------|-----------|
| `derives_from` | CRS | UC |
| `satisfies` | SYS | CRS |
| `design` | SYSARCH | SYS |
| `derives_from` | SRS | SYS |
| `module` | SWDD | MODULE |
| `implements` | SWDD | SRS |
| `mitigates` | RCM | RISK |
| `implements` | RCM | SYS |

### Design Layer: SYSARCH / MODULE / SWDD

- **SYSARCH** — one per SYS requirement; records the system-level design decision for that requirement
- **MODULE** — one per software unit; defines responsibility, key interfaces, internal structure
- **SWDD** — one per SRS requirement under a MODULE; must carry both `implements` (SRS) and `module` (MODULE)

### Approval Model

Requirement items (UC, CRS, SYS, SRS, SWDD, SYSARCH, RISK, RCM) have no `status` field. Approval is implicit from Git: on `main` = approved, on a feature branch = draft.

## Common Commands

```bash
# Data operations (dhfkit)
dhfkit --dhf DHF item list --type SYS
dhfkit --dhf DHF item get SYS-001
dhfkit --dhf DHF item create --type SYS --data '{"title": "My requirement"}'
dhfkit --dhf DHF validate schema
dhfkit --dhf DHF validate traceability
dhfkit --dhf DHF doc generate ALL
dhfkit --dhf DHF report

# AI-assisted CR workflow (medharness)
medharness --dhf DHF ci generate-dhf --cr CR-001   # design phase
medharness --dhf DHF ci develop-cr --cr CR-001     # implement phase
```

See the [MedHarness README](https://github.com/itercharles/MedHarness) for the full command reference and CI gate documentation.

---

`dhfkit` is bundled with MedHarness — install with `pip install medharness`.
