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

## What Problem We Solve

Medical device software teams must maintain a Design History File (DHF) throughout
the product lifecycle and produce submission-ready compliance evidence before every
regulatory review. Three problems make this consistently painful:

### 1. DHF maintenance consumes engineering time without producing value

Every requirement change, architecture update, or test result must be manually
reflected in a traceability matrix, linked to test records, and reconciled with
change control documentation. This happens every sprint. It requires diligence, not
expertise — which means it occupies a significant fraction of a QA engineer's week
and pulls senior engineers away from product work whenever a gap is found.

**What we do:** DHF items are YAML files. Changes are commits. Traceability is a
graph computed automatically. Engineers write the requirement; the tool handles the
bookkeeping. Effective recovery: ~0.5 FTE per 10–20 person team.

### 2. Pre-submission audit prep takes weeks and blocks shipping

Before a 510(k) submission or notified body audit, someone assembles the evidence
package — traceability matrix, test results, compliance coverage — manually from
wherever it lives (Confluence, Jira, spreadsheets, test runner exports). This
typically takes 4–6 weeks for two people and happens at the worst possible time:
immediately before a submission deadline.

**What we do:** The CI pipeline generates a traceability PDF and a compliance PDF
on every merge. By submission day, the evidence package already exists and reflects
current product state. Prep time collapses from weeks to a review day. Cost
savings: $25–40K per submission (2–3 person-months at blended rates).

### 3. There is no enforcement mechanism — compliance gaps discovered at audit are catastrophic

Without automated checks, non-compliant changes accumulate silently during
development and surface at internal audits (expensive rework) or during FDA/notified
body review (potentially fatal to the submission timeline). No existing tool blocks
a merge that creates a traceability gap or drops a required compliance attribute.

**What we do:** A four-phase CI gate enforces compliance on every merge — CR
linkage, traceability coverage, lifecycle integrity, and IEC 62304 / ISO 14971 /
IEC 82304-1 policy checks. Non-compliance is caught at the commit, not the audit.

---

## The AI Coding Multiplier

AI coding tools (Copilot, Cursor, Claude Code) are accelerating how fast engineers
produce code, requirements, and documentation. For medical device software, this
creates a new bottleneck: compliance verification has not kept pace with content
generation speed.

**Without CompliantFlow, AI coding makes the DHF problem worse.** AI generates
requirements faster → more items to maintain traceability for. AI produces test
code faster → more results to link to DHF items. AI proposes architecture changes
faster → more cross-layer impacts to verify. Every AI-generated change that is not
compliance-verified is a liability accumulating in the DHF.

**With CompliantFlow, AI coding and compliance scale together.** AI generates the
content; CompliantFlow verifies it. The CI gate runs on every commit regardless of
whether it was authored by a human or an AI agent. The gap between "AI draft" and
"submission-ready" collapses to a CI run.

| Scenario | DHF overhead | Audit prep |
|---|---|---|
| Traditional (no AI, no tool) | 0.5–1.0 FTE manual | 4–6 weeks × 2 people |
| AI coding tools only | Worse — more content, same manual burden | Same or worse |
| CompliantFlow only | ~0.5 FTE saved | 1 day |
| **AI coding + CompliantFlow** | **Near-zero** | **1 day** |

This positions CompliantFlow as the compliance infrastructure that makes
AI-assisted medical device development viable — not just a DHF tool.

---

## Positioning

**One sentence:** CompliantFlow is the CLI-native, Git-native compliance
infrastructure for SaMD teams that turns AI-generated and human-generated DHF
content into submission-ready evidence automatically, on every CI run.

**What we compete on:**
- Automated compliance evidence across three standards (IEC 62304, ISO 14971,
  IEC 82304-1) — not a starting template, fully configured
- CI/CD-native enforcement — compliance is a merge gate, not an audit event
- Open YAML format — no vendor lock-in, no per-seat pricing on data access
- Git as the audit trail — every change is attributed, timestamped, and branchable
- AI coding compatibility — the compliance gate works regardless of who authored
  the content

**What we do not compete on (deliberately):**
- GUI usability (v3.0.0 scope)
- Cloud collaboration and RBAC (v3.0.0 scope)
- Enterprise access control (v3.0.0 scope)

---

## Structured Selling Points

**1. "Your traceability matrix is always current — automatically."**
No more manually updating Excel after every sprint. Requirements, tests, and
architecture stay linked by the tool. The matrix is generated on demand, not
assembled by hand.

**2. "Audit prep goes from 6 weeks to 1 day."**
The evidence package is generated on every CI run. By submission day, it already
exists. Your RA engineer reviews it; they do not compile it.

**3. "Compliance gaps are caught at the commit, not the audit."**
The CI gate enforces IEC 62304, ISO 14971, and IEC 82304-1 on every merge — the
same way a failing unit test blocks a PR.

**4. "One tool covers three standards."**
IEC 62304 (75/106 checks automated), ISO 14971, IEC 82304-1 — fully configured.
Most teams cobble this together from three separate tools or manual processes.

**5. "The compliance layer for AI-generated medical device software."**
AI tools now write requirements, tests, and architecture at speed. Without
automated compliance verification, that content is a draft. CompliantFlow is the
missing layer that makes AI-generated DHF content submission-ready.

**6. "No per-seat pricing. No lock-in. Your data stays in YAML."**
Engineers own the DHF. The format is readable without the tool. No vendor
negotiation when the team scales.

**7. "Designed for the RDM migration."**
If you are on Innolitics RDM, the migration command converts your existing repo.
You keep your Git history; you gain automated compliance checks.

---

## Target Customer

**Primary ICP:** Seed-to-Series B SaMD startups and embedded medical device
software teams. Class II or Class III devices. 5–50 engineers. FDA 510(k) or CE
mark pathway. Engineering-led culture — the buying decision is made or strongly
influenced by the engineering lead or VP Engineering.

**Secondary ICP:** Innolitics RDM users at any size. RDM is effectively
unmaintained; these teams have committed to docs-as-code and are actively seeking
a migration path.

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
