---
name: Strategic Context and Prioritization Rationale
description: Key strategic bets, gaps, decision principles, and full product roadmap through v3.0.0
type: project
---

**Product positioning:** Developer-first, CLI-native, Git-native ALM for medical device software teams. Competes on: open format (YAML), CI/CD integration, low cost, auditability. Does NOT currently compete on: GUI usability, cloud collaboration, enterprise access control.

**Commercial context (updated 2026-04-07):** CompliantFlow is a commercial product sold/licensed to other medical device companies. The compliance check engine is the core commercial differentiator. Web UI is explicitly NOT a priority — it should not block or delay compliance engine work.

**Formal product strategy document:** `docs/product_strategy.md` — authoritative source for mission, strategic objectives, positioning, selling points, ICP, roadmap, and strategic constraints. PM-owned. Updated 2026-04-07. Read this before making any roadmap or prioritisation decisions.

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
6. **FDA sees PDFs, not YAML.** The YAML-in-Git storage is an internal implementation detail. Regulatory submissions use the generated PDF evidence reports (traceability_report.pdf, compliance_report.pdf). Auditor/FDA unfamiliarity with YAML is not a real risk — they evaluate the PDF output, which is a conventional submission artifact. Do not raise "FDA won't accept YAML" as a commercial risk.

**Strategic time constraint (updated 2026-04-02):**
Ketryx ($55M raised) will move down-market within 18–24 months (est. Q4 2027). CompliantFlow must have 3–5 paying SaMD startup customer references with 510(k) or CE mark submissions before then.

---

## Product Roadmap (updated 2026-04-02)

### v1.3.0 — NOW (Q2 2026): "Commercial Foundation"
**Status: Complete — all commercial blockers resolved.**

Confirmed complete items:
- PR↔CR automated linking (CR-003)
- Compliance run persistence
- IEC 82304-1 governance (31 policies, 20 automated)
- LLM backend abstraction / Ollama fallback
- ID immutability (CR-006)
- Traceability report with test results

Outstanding GTM action (not code): 510(k) case study — business dev responsibility.

Success metrics:
- All 75 IEC 62304 automated checks pass in CI on at least one customer repo
- At least one paying customer reference onboarded
- 510(k) case study authored and published

---

### v2.0.0 — NEXT (Q3 2026): "Compliance Completeness + RDM Migration"
**Theme: "Complete the DHF. Own the migration."**

Strategic goals:
1. ISO 14971 governance file — complete the regulatory trinity (CR-023, Critical)
2. Release gate enforcement via CLI — REL lifecycle gate in `compliantflow validate` (CR-024, High)
3. Defect lifecycle CI hook — DEF item traceability in CI (CR-025, High)
4. Innolitics RDM migration tooling — `compliantflow migrate rdm` command (CR-026, High)
5. FDA 21 CFR Part 11 technical brief — regulatory document addressing GitOps e-signature equivalence (CR-027, High)
6. GitLab CI and Jenkins artifact integration — multi-platform `test pull` support (CR-028, High)

Success metrics:
- ISO 14971 governance file with ≥20 automated checks shipping and passing on CompliantFlow's own DHF
- REL lifecycle gate blocks `compliantflow validate` when a release is non-compliant
- DEF items auto-linked in CI on PR merge for at least one customer
- RDM migration tooling converts a representative RDM repo in <30 minutes of manual effort
- Part 11 brief reviewed by at least one regulatory consultant
- GitLab CI artifact fetcher tested on a customer pipeline

---

### v2.1.0 — Q4 2026: "Platform Maturity"
**Theme: "Make it production-grade for a 50-person team."**

Strategic goals:
1. Multi-DHF / multi-project support — portfolio company use case (CR-029, High)
2. Read-only compliance status web dashboard — QA/RA persona access (CR-030, Medium)
3. Ollama air-gap deployment package — documented, tested, docker-compose (CR-031, Medium)
4. PDF submission template validation — regulatory consultant sign-off (CR-032, Medium)
5. Bulk approval for requirements — CR-001 implementation (existing approved CR, Low)

Success metrics:
- Multi-project support tested with at least two DHF configurations in one repo
- Web dashboard deployed and accessible without CLI for three reference customers
- At least one customer completes a submission review using CompliantFlow PDF output without format objections
- CR-001 closed and released
- Ollama setup verified on a representative air-gapped test environment

---

### v3.0.0 — H1 2027: "Enterprise Motion"
**Theme: "Sell to the QA Director, not just the engineering lead."**

Strategic goals:
1. RBAC / access control — role-based (Author, Reviewer, Approver, Auditor)
2. Full Web UI — complete GUI for DHF item management, traceability, compliance, CR workflow
3. Jira/GitHub Issues integration — bidirectional sync for CRs
4. SOC 2 Type II readiness — required for enterprise procurement
5. Signed release artifacts + SBOM — cryptographic signing + Software Bill of Materials

Success metrics:
- RBAC enforced and tested with at least three distinct roles
- Full Web UI passes usability test with three QA/RA personas who do not use the CLI
- At least two enterprise deals closed ($30K+ ARR each) using v3.0.0 capabilities
- SOC 2 Type II audit initiated
- SBOM generated and published for each release

---

**Strategic gaps (updated 2026-04-07):**
All v2.0.0 gaps are resolved. Active gaps driving CR-035 to CR-049:
- ISO 14971 policy coverage incomplete — CR-036
- 31 IEC 62304 checks remain manual — CR-037
- Compliance feedback is not actionable (PASS/FAIL only) — CR-035
- No time-based drift detection between merges — CR-038
- Field-level schema not exposed through ProjectSchema — CR-039 (architectural prerequisite)
- No machine-readable context for AI coding agents — CR-040
- No pre-commit draft item validation — CR-041
- No single at-a-glance compliance status command — CR-042
- Compliance reports are PDF-only, not machine-readable — CR-043
- ISO 13485 (QMS) not covered — CR-044
- SOUP vulnerabilities not monitored continuously — CR-045
- RDM migration produces converted files but not validated compliance — CR-046
- No 510(k) submission package assembly command — CR-047
- No REST API layer (blocks Web UI, Jira, AI tool plugins) — CR-048
- No AI coding agent compliance harness — CR-049
