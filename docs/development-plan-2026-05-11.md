# MedHarness Development Plan — 2026-05-11

## 1. Competitive Position (Summary)

The full competitive analysis is in `docs/medharness-competitive-positioning-report-2026-05-11.md`.
Key conclusions:

| Competitor | Core model | Why MedHarness is different |
|---|---|---|
| Greenlight Guru | Medtech eQMS + DHF | Broader QMS, but not developer-native; lives outside the code delivery loop |
| Jama Connect | Enterprise requirements + traceability | Optimized for cross-functional collaboration, not executable CI gates |
| Matrix Requirements | Med-device ALM + eQMS | Centralized app platform, not repo-native |
| Polarion / Codebeamer | Enterprise ALM | Heavyweight adoption; built for multi-product orgs, not software-first startups |
| Visure / Helix ALM | Requirements ALM | Database-centric, no AI-governance story |

**MedHarness unique position:**

> Open-source, Git-native, AI-governed design-control workflow for medical-device software teams — compliance embedded inside the delivery loop, not documented after the fact.

Four properties no competitor currently combines:
1. **Git-native** — DHF items are version-controlled YAML; evidence comes from CI, not manual uploads
2. **AI under design control** — AI actions are staged through CR workflows with deterministic validation gates before any LLM review runs
3. **Continuous design control** — traceability and test evidence are validated on every PR, not at audit time
4. **Open-source and composable** — `dhfkit` is a standalone pip package; teams can adopt incrementally

---

## 2. Current State Assessment

### What the roadmap says is done (v0.3.5, per CHANGELOG and roadmap.md)

| Capability | Status |
|---|---|
| `medharness init` single-repo scaffold | ✅ |
| DHF item CRUD, lifecycle, transitions | ✅ |
| Traceability validation (required links, orphans, coverage) | ✅ |
| CI gates: `test-coverage`, `dhf-validate`, evidence bundle | ✅ |
| Document generation (Markdown + PDF) | ✅ |
| Issue → CR intake | ✅ |
| AI spec generation (`ci analyze-cr`) with self-correction | ✅ |
| AI design generation (`ci design-cr`) with deterministic pre-checks | ✅ |
| AI code generation (`ci develop-cr`) with test-annotation validation | ✅ |
| Structured JSON output from all CI commands | ✅ |
| Uniform `stage/status/errors/items_changed/files_changed` payload | ✅ |
| Soft LLM review pass in all three stages | ✅ |

### What the roadmap marks as partial

| Capability | Gap |
|---|---|
| Structured `cr-analyze` output | YAML front-matter in spec works; no standalone structured JSON with `direction_fit`, `affected_items`, `proposed_new_items` as machine-readable fields for downstream consumption |
| Test plan generation | `compute_item_coverage` parses JUnit `@links`; manual-testing flag criteria not automated |
| Structured approval gate | Checklist PR comment exists; no machine-readable approve/reject signal beyond merge itself |

### What WebTPS reveals about the real workflow

WebTPS has 10 CRs against 18 SRS / 15 SYS / 3 RISK items across a React + ASP.NET Core + DICOM stack.

**CR completion rate by complexity:**

| CR | Title | Status | Complexity |
|---|---|---|---|
| CR-003 | Dark mode contrast | completed | trivial |
| CR-005 | Remove click-me page | completed | trivial |
| CR-006 | Maximize viewport | completed | trivial |
| CR-007 | Contouring functions | completed | moderate |
| CR-008 | Delegate DICOM import | completed | moderate |
| CR-010 | Rename Issues to Change Requests | completed | trivial |
| CR-004 | In-app Issues/CR page | **implementing** | complex (new UI flow) |
| CR-009 | 3D structure + MPR contours | **implementing** | complex (rendering) |

Pattern: **simple and moderate CRs complete end-to-end cleanly; complex multi-file CRs stall in the `implementing` phase.** This is the current frontier.

**Risk coverage gap:** 3 RISK items for a radiation therapy treatment planning system is materially thin. ISO 14971 and IEC 62304 would expect identified hazards for dose calculation errors, patient ID mixups, and data loss at minimum. Risk management is currently a DHF structural capability (items + traceability) but not a guided workflow.

---

## 3. Product Strategy Alignment Check

The roadmap defines two milestones:

- **Milestone 1: Structured AI Analysis Loop** — structured reviewable output at each stage
- **Milestone 2: Closed-Loop Implementation** — approved plan → AI implements code + DHF atomically

v0.3.5 has completed the infrastructure for Milestone 1 (deterministic pre-checks, structured JSON payload, soft review pass). What remains is the **reviewer-facing** part of Milestone 1: the machine-readable approval gate and the structured output feeding downstream steps without a human re-interpreting free-form markdown.

Milestone 2 is not started. The current `develop-cr` generates code on a branch but DHF item updates and traceability wiring still require manual YAML editing in complex cases.

**Strategic positioning → development priority mapping:**

| Positioning claim | Current reality | Gap |
|---|---|---|
| "AI under design control" | Deterministic checks before LLM, human approval gates exist | Approval gate is not machine-readable; complex CRs stall |
| "Continuous design control" | CI validates traceability on every PR | Test plan generation is manual; risk traceability is thin |
| "From issue to compliant PR in one workflow" | Works for simple CRs | Complex CRs need multi-round human correction |
| "Git-native DHF" | True for items and evidence | DHF item creation in design-cr still partially manual in complex cases |

---

## 4. Development Plan: Next Steps

### Phase 1 — Complete the Analysis Loop (4-6 weeks)
*Goal: Milestone 1 is fully closed; every stage produces machine-readable structured output that downstream steps consume without human re-interpretation.*

**P1-A: Machine-readable structured `cr-analyze` output**

The current `ci analyze-cr` writes a Markdown spec with YAML front-matter. The front-matter contains `affected_items` but it is embedded in a document, not a standalone structured artifact.

Work:
- Emit a companion `CR-NNN-Spec.json` alongside the Markdown spec containing `direction_fit`, `affected_items`, `proposed_new_items`, `design_impact_summary`, `test_plan_preview`
- `ci design-cr` and `ci develop-cr` consume the JSON directly instead of re-parsing the Markdown
- This removes one class of downstream prompt ambiguity and enables programmatic stage gating

Validation: Run CR-004 or CR-009 through `analyze-cr` with the new output; confirm `design-cr` consumes it without re-summarizing the spec.

**P1-B: Automated test plan with manual-testing flags**

Work:
- Define the flag criteria for "requires manual testing" (UI interaction, hardware interface, safety-critical path, visual output) as a config-driven rule set in `dhfkit`
- `ci analyze-cr` populates `test_plan.needs_manual_tc` alongside `needs_new_tc`
- The structured PR checklist distinguishes: auto-coverable / needs new automated TC / requires manual TC
- `ci test-coverage` gate accepts a `manual-evidence` input (a YAML file with manual test sign-offs) and counts those toward coverage

Validation: WebTPS CR-004 has UI interaction — verify it gets flagged as needing manual TC.

**P1-C: Machine-readable approval gate**

Current state: PR comment has a checklist; there is no programmatic approve/reject that blocks the next stage.

Work:
- Define a PR label scheme: `cr-spec-approved`, `cr-design-approved`, `cr-code-approved`
- `cr-lifecycle.yml` checks for the label before advancing to the next stage; missing label → workflow exits with a clear message
- The label is added either by a human reviewer via GitHub UI, or by a `/approve` PR comment trigger (slash command)
- Rejection path: `/reject <reason>` comment sets `cr-rejected` label, closes the CR branch, and transitions the DHF CR item to `rejected`

Validation: Verify on WebTPS that a PR without the approval label blocks the next stage; verify `/reject` closes cleanly.

---

### Phase 2 — Closed-Loop Implementation for Complex CRs (6-10 weeks)
*Goal: Milestone 2. Approved plan → AI implements code + DHF item updates in one atomic branch.*

**P2-A: Unblock complex CRs in WebTPS**

CR-004 and CR-009 are the test cases. Before building infrastructure, understand *why* they stall:
- Does `develop-cr` fail on the code step?
- Does it succeed on code but miss DHF item creation?
- Is the spec insufficiently structured to guide multi-file changes?

Action: Complete CR-004 manually with MedHarness commands, document every point where human intervention was needed. This becomes the requirement list for P2-B.

**P2-B: Atomic code + DHF branch**

Work:
- `ci develop-cr` creates a single branch containing: implementation code changes + updated/created DHF item YAMLs + wired traceability links
- DHF item creation uses the structured JSON from P1-A as the source of truth for which items to create/update
- Traceability links are auto-wired based on `affected_items` from the spec JSON
- Pre-merge CI validates the combined diff: schema, traceability, and test-annotation presence

**P2-C: CI pre-validation before PR is opened**

Currently the PR is opened and CI runs on it. For regulated software, the AI-generated output should be validated before human reviewers see it.

Work:
- `develop-cr` runs `dhfkit` validation and test-annotation checks locally before pushing
- If validation fails, the self-correction loop runs (already exists for spec/design) before pushing
- PR is only opened if the local validation passes or self-correction reaches max retries
- PR body includes a "Pre-merge validation" section summarizing the local check results

---

### Phase 3 — Risk Management as a First-Class Workflow (8-12 weeks)
*Goal: Risk analysis is part of the CR analysis loop, not a separate manual process.*

**P3-A: Risk impact analysis in `cr-analyze`**

- `cr-analyze` identifies which RISK items are affected by the CR (or should be created)
- `direction_fit` includes a risk dimension: does this CR introduce new hazards? affect mitigation measures?
- `affected_items` includes RISK IDs alongside SRS/SWDD IDs

**P3-B: Risk coverage gate**

- `ci test-coverage` extended to include risk-control coverage: every RISK item with a mitigation measure must have a test linked to the measure
- `ci dhf-validate` checks that every SRS item linked to a safety function has a corresponding RISK item

**P3-C: WebTPS risk build-out**

Use the WebTPS radiation therapy domain to build out a realistic risk register:
- Dose calculation errors
- Patient ID mixup
- Data loss / plan corruption
- Hardware interface failures (DICOM link)

This validates that the risk workflow handles real regulated-device complexity, not just template examples.

---

### Phase 4 — Ecosystem and Adoption (ongoing from month 4)
*Goal: MedHarness is easy to adopt independently of WebTPS; `dhfkit` is a recognized standalone library.*

**P4-A: `dhfkit` standalone release polish**

- Semantic versioned releases independent of `medharness`
- Comprehensive type stubs for IDE support
- A `dhfkit` quickstart guide that covers item CRUD, traceability validation, and document generation without any MedHarness CI context

**P4-B: TypeScript test reporter as first-class artifact**

WebTPS already uses a custom JUnit reporter for Vitest/Playwright. Extract this as a published npm package (`@medharness/vitest-reporter`, `@medharness/playwright-reporter`) so TypeScript teams don't have to write their own.

**P4-C: eQMS integration bridges**

Position MedHarness as the developer-facing layer rather than an eQMS replacement:
- Export a DHF summary in Greenlight Guru's document import format
- Export traceability matrix in a format importable by Jama Connect
- This enables the "MedHarness + incumbent eQMS" adoption pattern that is lower friction for established device companies

**P4-D: WebTPS as public demo**

Make WebTPS a reference that external teams can point to:
- A public GitHub Actions run that shows the end-to-end CR workflow executing
- A "how this CR was built" narrative in WebTPS docs linking to the CI run, the spec, the DHF diff, and the test results
- A badge on WebTPS README: "Design-controlled by MedHarness"

---

## 5. Prioritization Summary

| Priority | Item | Why |
|---|---|---|
| 1 | P1-A: Structured `cr-analyze` JSON output | Unblocks P1-B, P1-C, and all of Phase 2; removes human re-interpretation |
| 2 | P2-A: Diagnose and unblock WebTPS CR-004/CR-009 | Reveals the real gap in complex-CR handling before building infrastructure |
| 3 | P1-C: Machine-readable approval gate | Completes Milestone 1; required for the positioning claim "AI under design control" to be demonstrably true |
| 4 | P1-B: Automated test plan with manual-testing flags | Strengthens the coverage gate story; required for regulated teams |
| 5 | P2-B/C: Atomic code + DHF branch with pre-validation | Milestone 2; the most ambitious capability claim |
| 6 | P3-A/B: Risk management in CR analysis | Required for credibility with safety-critical device teams; major differentiator vs. pure ALM tools |
| 7 | P4-B: TypeScript test reporters as npm packages | Removes a friction point for all web/SaMD teams |
| 8 | P4-A/C/D: dhfkit polish, eQMS bridges, WebTPS public demo | Adoption and ecosystem growth |

---

## 6. Key Metric: The Demo Benchmark

The clearest proof of MedHarness's unique position is a reproducible end-to-end run:

> **From a GitHub issue to a compliant, merged PR with full DHF trail in under 30 minutes, for a non-trivial change.**

Currently this works for trivial CRs. The development plan is complete when it works reliably for moderate-complexity CRs (new UI flow, multi-file backend change) and the full workflow — issue → spec → design → code → review → merge → DHF updated → evidence bundle — is observable in a single GitHub Actions run on WebTPS.

That is the demo that makes the competitive positioning real.
