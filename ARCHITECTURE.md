# Architecture

CompliantFlow is the **orchestration / harness layer** in a multi-repo medical
device development system. This document explains the architecture boundaries,
how the repos interact, where AI fits, and the split between open-source
infrastructure and future commercial intelligence.

---

## Regulated Layer vs Execution Layer

The system is split into two conceptual layers:

| Layer | Repo | What it owns |
|-------|------|-------------|
| **Regulated** | Your DHF repo + CompliantFlow-DHF | Item schemas, lifecycle rules, governance policies, traceability requirements, risk records, test evidence — everything subject to design control |
| **Execution** | Your product repo + CompliantFlow | Source code, tests, CI pipelines, AI agent context, scaffolding templates — everything that produces or verifies regulated content |

The boundary is explicit: the harness (CompliantFlow) never holds regulated
content. It reads DHF schemas to understand the shape of valid content, enforces
traceability constraints, and generates evidence from existing artifacts.
The regulated data stays in the DHF.

```
┌─────────────────────────────────────────────┐
│  CompliantFlow (harness / orchestration)     │
│                                              │
│  ┌──────────────┐  ┌──────────────────────┐  │
│  │ CI gates     │  │ init scaffolding     │  │
│  │ test-coverage│  │ engineering-control  │  │
│  │ evidence     │  │ CLAUDE.md gen        │  │
│  │ release      │  │ DHF workflow gen     │  │
│  └──────┬───────┘  └──────────────────────┘  │
│         │                                     │
└─────────┼─────────────────────────────────────┘
          │ reads schemas, enforces traceability
          ▼
┌─────────────────────────────────────────────┐
│  CompliantFlow-DHF (DHF substrate)           │
│                                              │
│  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Item schemas │  │ Governance policies  │  │
│  │ Lifecycle    │  │ IEC 62304, ISO 14971 │  │
│  │ Graph engine │  │ (commercial layer)   │  │
│  └──────────────┘  └──────────────────────┘  │
│                                              │
│  Owns the DHF data model and validation.    │
│  Your DHF repo clones/starts from here.     │
└─────────────────────────────────────────────┘
```

---

## How CompliantFlow and CompliantFlow-DHF Interact

CompliantFlow depends on CompliantFlow-DHF at two levels:

1. **Build time** — `compliantflow init` bundles the DHF template (item type
   schemas, document templates) from CompliantFlow-DHF into the scaffolding
   it writes for new projects.
2. **Runtime** — CLI commands (`ci test-coverage`, `ci evidence bundle`, etc.)
   load the `dhf_util` Python package from the Python path. `dhf_util` provides
   the `LocalDHFAdapter` — the default provider for item CRUD, lifecycle
   transitions, schema validation, and graph operations.

The adapter protocol in `complainflow/adapters/protocol.py` defines the
interface. `LocalDHFAdapter` (in CompliantFlow-DHF's `dhf_util`) is the
reference implementation. Teams can swap in a different adapter if they
have a different DHF storage backend.

---

## Where AI Fits

AI operates at three levels in the CompliantFlow architecture:

### 1. Agent Context (repo-local docs)

`compliantflow init` writes a minimal `CLAUDE.md` into product repos. Agents
receive project structure and DHF boundaries from:

- `README.md` — project identity and multi-repo model
- `ARCHITECTURE.md` — regulated vs execution layer boundaries
- `CLAUDE.md` — repo-local rules and pointers to canonical docs
- Workflow prompts (`.github/prompts/`) — only where automation actively uses them

This replaces the previous AI-harness/ bundle with a skills-first, doc-native model.

### 2. DHF Workflows (open-source automation)

The DHF repo scaffolding includes GitHub Actions workflows for AI-driven CR
lifecycle management:

- `cr-analyze.yml` — AI generates a plan spec when a CR is created
- `cr-spec-iterate.yml` — AI revises the plan spec based on review feedback
- `cr-develop.yml` — AI implements the approved spec

These workflows call Claude Code or equivalent agents with structured prompts.

### 3. Semantic Compliance Checks (commercial, opt-in)

Standards-based compliance checking (IEC 62304, ISO 14971, IEC 82304-1 policy
enforcement) uses LLMs (Gemini API) to evaluate content that cannot be checked
mechanically. This capability is part of the **commercial tier** and is not
included in the open-source core.

---

## Open-Source Infrastructure vs Future Commercial Intelligence

| Component | Status | License |
|-----------|--------|---------|
| `compliantflow init` scaffolding | Open source (MIT) | Free |
| CLAUDE.md generation | Open source (MIT) | Free |
| `ci test-coverage` (requirement → test) | Open source (MIT) | Free |
| `ci evidence bundle` (evidence production) | Open source (MIT) | Free |
| Release assembly (`ci release assemble`) | Open source (MIT) | Free |
| `dhf_util` (DHF substrate) | Open source (MIT) | Free |
| `ci compliance-check` (standards enforcement) | Commercial | Paid |
| Governance policy enforcement (IEC 62304, etc.) | Commercial | Paid |
| Web UI | Commercial | Paid |
| RBAC and team collaboration | Commercial | Paid |
| Enterprise release signing + SBOM | Commercial | Paid |

The open-source core covers design traceability, test coverage enforcement, and
evidence production — a complete design-controlled engineering workflow. Commercial
features add standards compliance intelligence, enterprise scale, and collaboration.
