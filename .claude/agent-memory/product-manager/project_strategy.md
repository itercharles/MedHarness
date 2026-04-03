---
name: Strategic Context and Prioritization Rationale
description: Key strategic bets, gaps, and decision principles for roadmap planning
type: project
---

**Product positioning:** Developer-first, CLI-native, Git-native ALM for medical device software teams. Competes on: open format (YAML), CI/CD integration, low cost, auditability. Does NOT currently compete on: GUI usability, cloud collaboration, enterprise access control.

**Commercial context (updated 2026-04-03):** CompliantFlow is a commercial product sold/licensed to other medical device companies. The compliance check engine is the core commercial differentiator. Web UI is explicitly NOT a priority — it should not block or delay compliance engine work.

**Commercial value propositions (prioritized):**
1. Automated compliance evidence generation against IEC 62304 / ISO 14971 — replaces manual audit prep that takes weeks
2. CI/CD-native compliance gate — block non-compliant merges before they reach a regulator
3. Open YAML format — no vendor lock-in, no per-seat pricing on data access
4. Git as the audit trail — every change is immutably attributed, timestamped, and branchable
5. Framework-agnostic test traceability — works with any test runner via JUnit XML

**Key prioritization principles:**
1. Regulatory compliance coverage (IEC 62304, ISO 14971) is non-negotiable — any gap is a blocker for adoption
2. CI/CD integration is a first-class concern — the JUnit XML boundary and GitHub artifact fetcher reflect this
3. Architecture extensibility (DHFAdapter protocol) is a deliberate design choice — do not violate it
4. GitOps approval model is intentional — do not add explicit status fields to requirement items
5. Web UI does NOT block core compliance work — it is a later milestone

**v1.3.0 status (Q2 2026) — all commercial blockers resolved:**
- ✅ PR↔CR automated linking (CR-003)
- ✅ Compliance run persistence
- ✅ IEC 82304-1 governance (31 policies)
- ✅ LLM backend abstraction / Ollama fallback
- ✅ ID immutability (CR-006, PR #81 pending merge)
- ✅ Traceability report with test results
- ⏳ 510(k) case study (GTM — business dev action, not code)

**Remaining commercial risk:** Semantic compliance checks still require either GEMINI_API_KEY or a local Ollama instance. Air-gapped deployments need documentation on Ollama setup.

**Strategic time constraint (updated 2026-04-02):**
Ketryx ($55M raised) will move down-market within 18–24 months (est. Q4 2027). CompliantFlow must have 3–5 paying SaMD startup customer references with 510(k) or CE mark submissions before then.

**v2.0.0 (NEXT, Q3 2026) — TAM expansion:**
- Release gate enforcement via CLI (REL items)
- Defect hook in CI (DEF lifecycle → gate)
- ISO 14971 governance file
- IEC 82304-1 full coverage (remaining gaps)
- Innolitics RDM migration tooling + guide
- FDA 21 CFR Part 11 technical brief

**v2.x (LATER, Q4 2026+) — enterprise readiness:**
- Multi-DHF / multi-project support
- RBAC / access control
- Web UI (read-only dashboard, then full)

**Strategic gaps (post-commercial-launch):**
- No multi-project / multi-DHF support — limits enterprise / portfolio adoption
- No authentication or access control — fine for single-team, not enterprise
- Web UI — deferred intentionally; unlocks QA/RA persona when ready
