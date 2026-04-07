# Product Strategy

**Owner:** Product Manager
**Status:** Active
**Last reviewed:** 2026-04-07

This document records the durable strategic direction for CompliantFlow. It is the
authoritative input to roadmap prioritisation. It is not a feature list — feature
scope and CR tracking live in the DHF. Update this document when the market
position, target customer, or core value proposition changes, not when individual
features ship.

---

## Mission

**Make every change compliant. Zero compliance debt, continuously.**

This is the primary objective — not efficiency, not audit savings. Those are
consequences. The mission is a state: a medical device software codebase where
every commit, every requirement change, every test result, and every architecture
update is immediately verified against the applicable regulatory standards. No
backlog of unverified changes. No compliance debt accumulating between audits.

Everything else in this document follows from that mission.

---

## Strategic Objectives

### Objective 1 — Zero compliance debt at every commit (primary)

Traditional medical device development accumulates compliance debt continuously:
requirements are written without traceability, tests run without being linked to
DHF items, architecture changes land without policy checks. The debt is settled
manually before each audit — weeks of rework, late in the cycle, at the worst
possible time.

CompliantFlow eliminates this model. Compliance is a CI gate, not an audit event.
Every merge is verified against IEC 62304, ISO 14971, and IEC 82304-1. Traceability
is computed automatically. Evidence is generated on every run. The debt cannot
accumulate because the gate blocks non-compliant changes at the commit.

**Consequence for the customer:** Audit prep collapses from 4–6 weeks to a review
day. A 510(k) submission is not a crisis — it is a download of the latest CI
artifacts.

### Objective 2 — Be the compliance infrastructure for AI-assisted medtech development (co-equal)

AI coding tools (Copilot, Cursor, Claude Code) are now generating requirements,
tests, architecture descriptions, and DHF content at high speed. For normal
software, this is a pure productivity gain. For medical device software, it creates
a new problem: compliance verification has not kept pace with content generation
speed.

Without a compliance gate, AI coding tools make the DHF problem worse. AI
generates requirements faster → more items to maintain traceability for. AI
produces tests faster → more results to link. AI proposes architecture changes
faster → more cross-layer impacts to verify. Every AI-generated change that is not
immediately compliance-verified is debt — accumulating faster than before.

CompliantFlow removes this ceiling. The CI gate runs on every commit regardless
of whether it was authored by a human or an AI agent. Zero-debt compliance scales
with however fast the team moves.

| Scenario | Compliance debt | Audit prep |
|---|---|---|
| Traditional (no AI, no tool) | Accumulates every sprint | 4–6 weeks × 2 people |
| AI coding only | Accumulates faster | Same or worse |
| CompliantFlow only | Zero | 1 day |
| **AI coding + CompliantFlow** | **Zero** | **1 day** |

The efficiency gain is a consequence of eliminating debt, not a separate feature.
The faster a team moves — whether human or AI-driven — the more valuable the gate
becomes.

### Objective 3 — Provide a compliance harness for AI coding in medtech (forward-looking)

Beyond acting as a verification layer for AI-generated content, CompliantFlow is
positioned to become the structured environment that makes compliant AI coding
possible in medtech in the first place.

AI coding agents require context to generate correct output: what schema a DHF item
must follow, what lifecycle states are valid, which fields are required for
traceability, what compliance policies apply. Without that structure, AI generates
plausible-looking content that silently violates regulatory requirements.
CompliantFlow's DHF schema, lifecycle definitions, policy rules, and agent
entrypoints (CLAUDE.md, AGENTS.md) already provide exactly this context. The
system is already a harness — this objective is to make that role explicit,
supported, and marketed.

The forward-looking direction: CompliantFlow ships with pre-configured AI coding
agent context that enables any AI coding tool to generate IEC 62304-compliant
requirements, risk items, test stubs, and change requests correctly, with the
compliance gate confirming the output. This makes CompliantFlow the natural
platform for medtech teams adopting AI-assisted development, not just a tool they
run alongside it.

This objective is directional — it informs roadmap decisions but does not drive
near-term CRs.

---

## What Problem We Solve

### 1. DHF maintenance consumes engineering time without producing value

Every requirement change, architecture update, or test result must be manually
reflected in a traceability matrix, linked to test records, and reconciled with
change control documentation. This happens every sprint. It requires diligence, not
expertise — occupying a significant fraction of a QA engineer's week and pulling
senior engineers away from product work.

**What we do:** DHF items are YAML files. Changes are commits. Traceability is a
graph computed automatically. Engineers write the requirement; the tool handles the
bookkeeping. Effective recovery: ~0.5 FTE per 10–20 person team.

### 2. Pre-submission audit prep takes weeks and blocks shipping

Before a 510(k) submission or notified body audit, someone assembles the evidence
package manually from wherever it lives (Confluence, Jira, spreadsheets, test runner
exports). This typically takes 4–6 weeks for two people, immediately before a
submission deadline.

**What we do:** The CI pipeline generates a traceability PDF and a compliance PDF
on every merge. By submission day, the evidence package already exists. Prep time
collapses from weeks to a review day. Cost savings: $25–40K per submission.

### 3. No enforcement — compliance gaps discovered at audit are catastrophic

Without automated checks, non-compliant changes accumulate silently and surface at
internal audits (expensive rework) or during FDA/notified body review (potentially
fatal to the submission timeline).

**What we do:** A four-phase CI gate enforces compliance on every merge — CR
linkage, traceability coverage, lifecycle integrity, and policy checks across three
standards. Non-compliance is caught at the commit, not the audit.

---

## Positioning

**One sentence:** CompliantFlow is the compliance infrastructure for medical device
software teams that enforces zero compliance debt on every commit — and scales that
guarantee to however fast the team moves, whether human or AI-driven.

**What we compete on:**
- Zero compliance debt at the commit — not batch remediation before audits
- Automated evidence across three standards (IEC 62304, ISO 14971, IEC 82304-1) —
  fully configured, not a starting template
- CI/CD-native enforcement — compliance is a merge gate, not a periodic review
- Open YAML format — no vendor lock-in, no per-seat pricing on data access
- Git as the audit trail — every change is attributed, timestamped, and branchable
- First-class AI coding compatibility — the gate verifies AI-generated content at
  the same zero-debt standard as human-authored content

**What we do not compete on (deliberately):**
- GUI usability (v3.0.0 scope)
- Cloud collaboration and RBAC (v3.0.0 scope)
- Enterprise access control (v3.0.0 scope)

---

## Structured Selling Points

**1. "Zero compliance debt — on every commit."**
Every change is verified against IEC 62304, ISO 14971, and IEC 82304-1 in CI.
Compliance gaps are caught at the merge, not discovered at the audit.

**2. "Audit prep goes from 6 weeks to 1 day."**
The evidence package is generated on every CI run. By submission day, it already
exists. Your RA engineer reviews it; they do not compile it.

**3. "One tool covers three standards."**
IEC 62304 (75/106 checks automated), ISO 14971, IEC 82304-1 — fully configured.
Most teams cobble this together from three separate tools or manual processes.

**4. "Your traceability matrix is always current — automatically."**
Requirements, tests, and architecture stay linked by the tool. The matrix is
generated on demand, not assembled by hand.

**5. "AI coding doesn't create compliance debt. It creates compliant software."**
If your team uses AI coding tools, CompliantFlow keeps every AI-generated commit
at the same zero-debt standard as human-authored changes. The faster AI moves,
the more valuable the gate becomes.

**6. "The structured environment that makes AI coding viable for medtech."**
AI agents need context to generate compliant content: schema, lifecycle rules,
policy requirements. CompliantFlow provides that context. AI coding without
CompliantFlow generates plausible-looking DHF content that silently violates
regulatory requirements. With it, AI generates correctly.

**7. "No per-seat pricing. No lock-in. Your data stays in YAML."**
Engineers own the DHF. The format is readable without the tool. No vendor
negotiation when the team scales.

---

## Target Customer

**Primary ICP:** Seed-to-Series B SaMD startups and embedded medical device
software teams. Class II or Class III devices. 5–50 engineers. FDA 510(k) or CE
mark pathway. Engineering-led culture — the buying decision is made or strongly
influenced by the engineering lead or VP Engineering.

**Secondary ICP:** Innolitics RDM users at any size. RDM is effectively
unmaintained; these teams have committed to docs-as-code and are actively seeking
a migration path.

**Emerging ICP (Objective 3):** Medtech teams actively adopting AI coding tools
who need a compliance harness to make AI-generated content submission-ready. This
segment is growing rapidly and is underserved — no existing tool addresses the
AI coding + medtech compliance intersection.

**Personas (priority order):**

1. **Software Engineering Lead / VP Engineering** — economic buyer or strong
   influencer. Cares about CI/CD integration, open format, cost predictability.
   Pain: manual DHF maintenance slows sprints; enterprise ALM tools are too heavy.

2. **Quality / Regulatory Engineer** — primary daily user for compliance checks and
   evidence generation. Pain: manually assembling traceability matrices takes weeks.
   Current limitation: CLI-only; addressed in v2.1.0 (web dashboard) and fully in
   v3.0.0 (full Web UI).

3. **DevOps / CI Engineer** — integration owner. Cares about GitHub Actions/GitLab
   CI integration, JUnit XML import, and the CR validation gate.

---

## Strategic Constraints

These are deliberate decisions, not gaps. Do not revisit without a significant
market signal.

- **No free tier.** The product reduces compliance risk in a regulated industry.
  Free positioning undercuts perceived quality. Offer a 30-day trial or free
  onboarding workshop instead.
- **No GUI before v2.1.0.** The primary ICP is engineering-led. GUI investment
  before the CLI value proposition is proven dilutes focus.
- **No cloud hosting before v3.0.0.** Local execution is a feature for regulated
  customers with data residency requirements.
- **No per-seat pricing on data access.** Core differentiator against Jama,
  Polarion, and Codebeamer. Pricing is on projects and capabilities, not users.
- **Submission template validation (CR-032) requires a real submission engagement
  to scope.** Do not build speculatively.

---

## Roadmap

CRs are the authoritative backlog — this section records the milestone grouping and rationale. Full CR descriptions live in `DHF/items/09_cr/`.

### v2.1.0 — "Deepen & Enforce" (Q3 2026)

Strengthen the zero-debt guarantee and make compliance feedback actionable for engineers and AI agents.

| CR | Title | Priority |
|---|---|---|
| CR-035 | Actionable Compliance Feedback | High |
| CR-036 | ISO 14971 Policy Completeness | High |
| CR-037 | IEC 62304 Manual Check Reduction | High |
| CR-038 | Compliance Drift Detection | High |

### v2.2.0 — "AI Coding Infrastructure" (Q4 2026)

Make CompliantFlow the structured environment AI coding tools operate within, not just a verifier that runs after them.

| CR | Title | Priority |
|---|---|---|
| CR-039 | Field Schema Protocol Extension *(unblocks CR-040, CR-041)* | High |
| CR-040 | AI Agent Context Package | High |
| CR-041 | Draft Item Pre-Validation | High |
| CR-042 | Compliance Status Summary Command | Medium |
| CR-043 | Machine-Readable Compliance Report Export | High |
| CR-044 | ISO 13485 Governance File | Medium |
| CR-045 | SOUP Automated Vulnerability Check | Medium |
| CR-046 | RDM Migration Completeness Validation | Medium |

### v3.0.0 — "Enterprise Motion" (H1 2027)

Sell to the QA Director, not just the engineering lead. Existing planned scope: RBAC, full Web UI, Jira/GitHub Issues sync, SOC 2 Type II, signed release artifacts + SBOM. New additions:

| CR | Title | Priority |
|---|---|---|
| CR-047 | 510(k) Submission Evidence Package *(requires active submission engagement)* | High |
| CR-048 | Compliance Posture REST API *(requires RBAC first)* | High |
| CR-049 | Compliance-Aware PR Review Agent | High |

---

## Key Strategic Risk

**Ketryx** ($55M raised, currently targeting Series B+) is the primary competitive
threat. Estimated down-market move to the SaMD startup segment: Q4 2027.
CompliantFlow must have 3–5 paying customer references with actual regulatory
submissions before then. At that point, defensibility shifts from feature
differentiation to reference credibility and switching cost.

The single highest-leverage action available: a **510(k) case study** documenting
a real FDA submission accepted with CompliantFlow-generated evidence. This is a
business development action, not an engineering one. It is the gating item for
scaling beyond early adopters.
