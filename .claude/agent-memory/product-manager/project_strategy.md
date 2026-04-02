---
name: Strategic Context and Prioritization Rationale
description: Key strategic bets, gaps, and decision principles for roadmap planning
type: project
---

**Product positioning:** Developer-first, CLI-native, Git-native ALM for medical device software teams. Competes on: open format (YAML), CI/CD integration, low cost, auditability. Does NOT currently compete on: GUI usability, cloud collaboration, enterprise access control.

**Commercial context (updated 2026-04-02):** CompliantFlow is a commercial product sold/licensed to other medical device companies. The compliance check engine is the core commercial differentiator. Web UI is explicitly NOT a priority — it should not block or delay compliance engine work. UI can come later for data visibility.

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

**Compliance adoption blockers (must fix before commercial launch):**
- BLOCKER: IEC 82304-1 governance file is incomplete — any customer needing that standard is blocked
- BLOCKER: No PR↔CR automated linking (CR-003) — IEC 62304 §6.2 change control gap, regulators will flag this
- BLOCKER: Manual ID editing possible (CR-006) — data integrity / traceability gap; IDs can break silently
- BLOCKER: Semantic compliance checks require Gemini API key — air-gapped or locked-down environments (common in medtech) cannot use these checks with no fallback
- RISK: No audit trail for compliance check runs — results are computed but not persisted/signed; auditor can't reproduce a past state
- RISK: Release gate criteria (REL items) are not enforced by CLI — regulatory readiness check is manual

**Strategic time constraint (updated 2026-04-02):**
- Ketryx ($55M raised) will move down-market within 18–24 months (est. Q4 2027). CompliantFlow must have 3–5 paying SaMD startup customer references with 510(k) or CE mark submissions before then. Every near-term prioritization decision should be filtered through this window.

**Market-informed prioritization additions (2026-04-02):**
- Gemini API dependency is a HIGH-severity commercial blocker today — air-gapped medtech environments (defense-adjacent, hospital-deployed, Class III implantables) cannot use semantic checks. Promoted to v1.3.0 critical priority.
- Innolitics RDM users are the best near-term acquisition target — free, unmaintained, pre-qualified for docs-as-code compliance. Migration tooling + guide is a NEXT priority.
- ISO 14971 governance file promoted from LATER to NEXT — full 62304 + 82304-1 + 14971 coverage is a genuine market differentiator with no competitor match.
- FDA 21 CFR Part 11: Git author attribution may not satisfy Part 11 auditors. A written technical brief (no code) reviewed by a regulatory consultant should ship in NEXT.
- 510(k) case study is the single highest-leverage GTM action — one named reference eliminates the "auditor unfamiliar with YAML-in-Git" objection at scale. Needs a business development owner assigned now.
- "No per-seat pricing" must be made explicit in all positioning (pricing page, README, demos). Currently implicit.
- Read-only web dashboard demoted from NEXT to LATER — owner flagged as not priority; market confirms ICP is developer-led and CLI-comfortable.

**Strategic gaps (post-commercial-launch roadmap):**
- Gap: No multi-project / multi-DHF support — limits enterprise / portfolio adoption
- Gap: No authentication or access control — fine for single-team, not for enterprise
- Gap: Web UI — deferred intentionally; unlocks QA/RA persona when ready

**Version history context:**
- v1.0.0: released — core traceability, graph, requirements parsing
- v1.2.0: released — new features (CR-001, CR-010 referenced)
- v1.1.0: draft, empty — appears to have been skipped or merged into 1.2.0
- v1.3.0 (NOW, Q2 2026): commercial blockers — PR-CR linking, ID integrity, 82304-1 completion, Gemini fallback, 510(k) case study (GTM)
- v2.0.0 (NEXT, Q3 2026): TAM expansion — release gate, defect hook, 82304-1 full + ISO 14971, RDM migration, Part 11 documentation
- v2.x (LATER, Q4 2026+): enterprise readiness — multi-DHF, RBAC, web UI, broader migration tools
