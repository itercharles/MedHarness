# CompliantFlow

**An open-source design-controlled development harness for medical software.**

CompliantFlow provides the engineering infrastructure — DHF structure, design
traceability, requirement→test coverage enforcement, evidence bundle generation,
and AI agent context — that medical device teams need to build software under
design control. It is a harness that connects design documentation to engineering
work and keeps them in lock-step on every commit.

---

## How It Works

CompliantFlow uses a **multi-repo model**:

| Repo | What it holds | Role |
|------|---------------|------|
| **CompliantFlow** (_this repo_) | The harness CLI, CI gate logic, scaffolding templates | Orchestration / harness |
| **CompliantFlow-DHF** | The AI-native DHF substrate — item schemas, lifecycle rules, governance policies, traceability engine | DHF substrate |
| **Your product repo** | Code, tests, CI workflows | Regulated software |
| **Your DHF repo** | Requirements, risks, architecture, test evidence | Regulated data / structural gate |

```
  CompliantFlow (harness)
       │
       ├──► Your DHF repo ─── governed by CompliantFlow-DHF
       │    (requirements, risks, traceability)
       │
       └──► Your product repo ─── engineering control CI
            (code, tests, verification evidence)
```

**CompliantFlow** is the orchestration layer. **CompliantFlow-DHF** is the
AI-native DHF substrate (schema validation, lifecycle rules, governance policies,
document generation). **Your repos** hold the regulated content — requirements
and code — while the harness enforces the structure and traceability constraints.

Requirement → test coverage is enforced in CI by `ci test-coverage` on the
product repo. Design traceability (UC → CRS → SYS → SRS → SWDD / TC) is
enforced in the DHF repo through structural validation. Evidence bundles are
produced on every merge to `main`, not assembled manually before an audit.

AI agents receive structured DHF context so they can generate requirements, tests,
and design documents that respect traceability rules from the start.

---

## The Regulated Chain

CompliantFlow supports a design-controlled engineering workflow:

1. **DHF structure and traceability** constrain engineering work — every item type
   has required upstream/downstream links; orphaned items block CI.
2. **AI assists** analysis, planning, implementation, and review — agents receive
   DHF schema, lifecycle rules, and traceability context before they generate content.
3. **Formal evidence** remains grounded in design, implementation, and
   verification artifacts — the harness produces traceability reports and
   evidence bundles from the same YAML/Git source of truth.

Semantic compliance checking against specific standards (IEC 62304, ISO 14971,
etc.) is a separate commercial capability and is not part of the open-source core.

---

## Quick Start

```bash
git clone https://github.com/compliantflow/compliantflow
cd CompliantFlow
pip install -e .
```

Then scaffold a new project:

```bash
compliantflow init
```

`init` asks about your org, product repo, and DHF repo, then writes scaffolding
locally — no GitHub operations. Review, push, and open a PR. From that point
every push runs the traceability and coverage gates automatically.

Full walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md)

---

## Core Workflow

After `init`, the daily workflow is:

1. Open a PR with a CR ID in the title (e.g. `feat(CR-012): add dose calculation`)
2. CI runs the **test-coverage** gate — verifies test evidence covers all requirements
3. DHF repo enforces structural/design traceability
4. On merge to `main`, CI produces an **evidence bundle** with traceability reports
   as CI artifacts
5. CR is auto-closed in the DHF

Run coverage checks locally before pushing:

```bash
compliantflow --dhf DHF ci test-coverage --junit-dir test-results
```

---

## Stable CLI Surface

These commands are the supported public interface. Backward compatibility is
maintained across minor versions.

```
compliantflow init                              Scaffold DHF + product repo CI

compliantflow ci test-coverage                  Requirement → test coverage gate
compliantflow ci evidence bundle                Produce CI evidence bundle
compliantflow ci release consume-artifact       Download CI artifact from Actions run
compliantflow ci release assemble               Assemble release bundles (wheel + DHF)

compliantflow review-pr                         DHF traceability PR review checklist
compliantflow context                           DHF schema + traceability context for AI agents
compliantflow cr workflow ...                   CR intake, completion, status
```

### Not yet stable public API

These commands are present but their interfaces may change:

- `validate traceability`, `validate coverage` — kept as developer tools.
- `export submission` — 510(k) submission assembly; depends on active FDA
  submission engagement for scoping.
- `dhf item ...` — DHF automation facade; adapter protocol is stable but
  provider-specific behaviour varies.
- `migrate rdm` — Innolitics RDM migration; target format matures with DHF schema.
- `status` — design traceability posture summary; output format evolving.
- `test import`, `test list`, `test status` — test result management.
- `validate compliance`, `ci compliance-check` — available internally but not part
  of the stable OSS surface; these will become commercial capabilities.

---

## Relationship to CompliantFlow-DHF

CompliantFlow-DHF is a companion repository that provides the DHF substrate:

- Item type schemas (field definitions, lifecycle rules, required links)
- The `dhf_util` Python package (item CRUD, schema validation, document generation)
- AI-native DHF workflows (CR analysis, spec iteration, implementation)
- Governance policy files for standards compliance (bundled with the DHF
  substrate; enforcement is part of the commercial tier)

CompliantFlow _orchestrates at the product level_ — CI gates, release assembly,
scaffolding. CompliantFlow-DHF _owns the DHF data model_. The harness knows the
structure; the substrate defines what valid content looks like.

---

## Open Source vs Future Commercial Direction

CompliantFlow is open source (MIT). The harness, design traceability gates,
scaffolding templates, and AI agent context infrastructure are free to use,
modify, and redistribute.

A commercial tier (planned) may add:

- Semantic compliance checking (IEC 62304, ISO 14971, IEC 82304-1 policy enforcement)
- Team RBAC and collaboration features
- Web UI for QA/RA workflows
- Enterprise-grade release signing and SBOM
- Hosted compliance evidence storage

The open-source core will always include the full design traceability gate,
scaffolding, and agent context infrastructure. The commercial layer adds
standards-based compliance intelligence and enterprise workflow features.

Current status: **active open-source development**.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, the CR workflow,
and PR conventions.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest tests/ -q
```

---

## Example: A Two-Repo Medical Device Project

This is what a CompliantFlow-scaffolded project looks like in practice:

**Your product repo** (e.g. `acme/insulin-pump`):
```
├── AI-harness/               # AI agent context (pre-configured)
│   ├── context.md            # DHF structure, when to update DHF, gate semantics
│   ├── CLAUDE.md             # Entry points for AI coding tools
│   ├── pre-checklist.md
│   └── ...
├── docs/                     # Strategy scaffold (fill in)
├── .github/workflows/
│   ├── engineering-control.yml  # Tests → test-coverage gate → evidence bundle
│   └── cr-complete.yml          # Auto-close CRs on PR merge
└── src/                      # Your product code
```

**Your DHF repo** (e.g. `acme/insulin-pump-dhf`):
```
├── DHF/
│   ├── items/                # UC, CRS, SYS, SRS, SWDD, RISK, RCM, CR items
│   ├── config/               # Doc type schemas, global lifecycle
│   │   ├── global.yaml       # required_traceability, document_specifications
│   │   └── doc_types/        # SYS.yaml, SRS.yaml, CR.yaml, ...
│   └── documents/
│       └── specs/            # Jinja2 templates (*.md.j2)
├── governance/               # Governance policy files (structural reference)
└── .github/workflows/        # DHF structural CI
```

The product CI runs `ci test-coverage` on every push, checking that test evidence
covers all requirements. The DHF CI runs structural validation, checking that all
items have required traceability links. On merge to `main`, an evidence bundle is
produced — ready for audit, no manual assembly needed.

---

## License

MIT — see [LICENSE](LICENSE).
