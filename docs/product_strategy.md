# Product Strategy

**Owner:** Product Manager
**Status:** Active
**Last reviewed:** 2026-04-21

This document records the durable strategic direction for CompliantFlow. It is the
authoritative input to roadmap prioritisation. It is not a feature list — feature
scope and CR tracking live in the DHF. Update this document when the market
position, target customer, or core value proposition changes, not when individual
features ship.

---

## Mission

**The AI-first development framework for medical device software. Zero compliance debt, continuously.**

AI coding tools are generating code and documentation faster than compliance processes can verify it. CompliantFlow is the trust layer that closes this gap: it provides the structured environment AI agents need to generate compliant content, and enforces compliance on every commit through a CI gate that understands IEC 62304, ISO 14971, and ISO 13485 semantics — not just code quality.

The mission is a state: a medical device software codebase where every commit — human or AI-generated — is immediately verified against applicable regulatory standards. No backlog of unverified changes. No compliance debt.

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

### Objective 3 — Ship the AI coding infrastructure for medtech (co-equal)

CompliantFlow is not just a verifier that runs after AI tools. It is the structured
environment that makes compliant AI coding possible in the first place.

AI coding agents require context to generate correct output: what schema a DHF item
must follow, what lifecycle states are valid, which fields are required for
traceability, what compliance policies apply. Without that structure, AI generates
plausible-looking content that silently violates regulatory requirements.

CompliantFlow ships this context as `AI-harness/` — pre-configured for every project
via `compliantflow init`. Both the product repo and the DHF repo receive a harness
with model-agnostic context, pre/post-task checklists, and adapters for Claude Code,
Cursor, and GitHub Copilot. The CI gate then confirms the output is correct.

**Current state (shipped in v2.0.x):**
- DHF repo AI harness: context.md, CLAUDE.md, AGENTS.md, GEMINI.md, checklists, adapters
- Product repo AI harness: same structure, tailored to product-side concerns (when to update the DHF, compliance gate semantics, CR workflow)
- `compliantflow init` delivers both harnesses in one command

**Next:** Make the framework positioning explicit in marketing and onboarding materials.

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

**One sentence:** CompliantFlow is the AI-first development framework for medical device software — out-of-the-box infrastructure where AI coding agents generate compliant code and documentation, with a compliance gate that enforces zero debt on every commit.

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

**Emerging ICP (now primary entry motion):** Technical co-founders and engineering leads at medtech startups adopting AI coding tools (Copilot, Cursor, Claude Code). They are building from scratch with AI-first practices and need compliance infrastructure that works with those tools, not against them. No existing tool addresses the AI coding + medtech compliance intersection. This segment is growing rapidly and acquisition cost is low — they are actively searching for this solution.

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

### Shipped (v2.0.x)

| CR | Title |
|---|---|
| CR-054 | `compliantflow init` — interactive infrastructure onboarding |
| CR-055 | Product repo AI harness |
| — | DHF repo AI harness (AI-harness/ in dhf-template) |
| CR-041 | Draft Item Pre-Validation (`validate draft`) |
| CR-043 | Machine-Readable Compliance Report Export (`report compliance --format json`) |

### v2.1.0 — "Deepen & Enforce" (Q3 2026)

Strengthen the zero-debt guarantee and make compliance feedback actionable for engineers and AI agents.

| CR | Title | Priority |
|---|---|---|
| CR-035 | Actionable Compliance Feedback | High |
| CR-036 | ISO 14971 Policy Completeness | High |
| CR-037 | IEC 62304 Manual Check Reduction | High |
| CR-038 | Compliance Drift Detection | High |

### v2.2.0 — "AI Coding Infrastructure" (Q4 2026)

Deepen the AI framework: machine-readable interfaces, richer agent context, and broader standard coverage.

| CR | Title | Priority |
|---|---|---|
| CR-039 | Field Schema Protocol Extension *(unblocks CR-040)* | High |
| CR-040 | AI Agent Context Package | High |
| CR-042 | Compliance Status Summary Command | Medium |
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
