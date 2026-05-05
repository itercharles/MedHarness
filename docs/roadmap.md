# Roadmap

## Vision

Medical device software development is being transformed by AI coding tools. Engineers can now generate implementation code in minutes. But regulatory compliance — the Design History File, traceability, test evidence, design impact analysis — is still maintained by hand.

**CompliantFlow's goal:** make the DHF self-maintaining. Every code change should automatically propagate into the DHF, with humans confirming rather than authoring.

---

## The Problem We're Solving

AI coding tools (Claude Code, Cursor, Copilot) dramatically accelerate implementation. But they create a compliance debt: the faster you ship, the further behind your DHF falls. Teams end up in one of two failure modes:

- **Compliance theater** — DHF is maintained separately from code, diverges over time, fails audits
- **AI paralysis** — teams avoid AI tools because they can't keep the DHF in sync

Neither is acceptable for a team trying to build a safe, auditable medical device.

---

## The Solution: AI-Native Design Control

CompliantFlow treats the DHF as a first-class engineering artifact, co-located with code in git, maintained by the same CI/CD pipeline that builds and tests the product.

The core loop looks like this:

```
1. Engineer opens an issue
2. Engineer triages: is this worth doing? (go/no-go)
3. AI analyzes the issue against the current DHF:
      - Does this fit the product's commercial and technical direction?
      - Which existing design items are affected?
      - What is the proposed implementation approach (based on code analysis)?
      - What tests are already covered? What requires new or manual tests?
4. Engineer reviews and approves the plan
5. AI implements: code changes + DHF updates in a single PR
6. CI validates traceability and test coverage
7. On merge: DHF is updated, evidence is generated automatically
```

The engineer's job shifts from **authoring compliance documentation** to **reviewing and approving AI-generated plans**.

---

## Reference Implementation: WebTPS

[WebTPS](https://github.com/itercharles/WebTPS) is a medical device web application being developed using CompliantFlow as its compliance infrastructure. It serves as the primary reference implementation and the main driver of CompliantFlow's feature development.

Every CompliantFlow feature is validated against the WebTPS workflow before release.

---

## Current State: v0.1.0

The infrastructure layer is complete and open-sourced.

### What works today

| Capability | Status |
|-----------|--------|
| `compliantflow init` — scaffold a DHF repo and product repo | ✅ |
| DHF item CRUD — create, update, transition, list | ✅ |
| Traceability validation — required links, orphan detection, coverage | ✅ |
| CI gate — `ci test-coverage` against JUnit evidence | ✅ |
| CI gate — `ci dhf-validate` structural checks | ✅ |
| Evidence bundle — specs, plans, traceability JSON, manifest | ✅ |
| Document generation — Jinja2 → Markdown → PDF (WeasyPrint) | ✅ |
| Issue → CR intake — `cr intake-github-issue` | ✅ |
| CR lifecycle — develop → review → completed transitions | ✅ |
| AI implementation context — `dhf context` | ✅ |
| Scaffold CI workflows — cr-analyze, cr-develop, cr-transition | ✅ |
| Claude Code skills — pre-analyze, cr-implement, traceability-check | ✅ |
| Structured AI analysis — YAML front-matter in spec | ✅ |
| Computed test plan — JUnit coverage injected into `$DHF_CONTEXT` | ✅ |
| Structured approval gate — checklist in spec PR + reject on out-of-scope | ✅ |

### What's partial

| Capability | Gap |
|-----------|-----|
| AI design analysis | YAML front-matter works; `cr-analyze.md` prompt enriched; "what needs manual testing" heuristic not yet automated |
| Test plan generation | `compute_item_coverage` parses JUnit `@links`; manual-testing flag criteria not yet computed |
| Structured plan approval | Checklist editable via `gh pr edit`; no machine-readable approve/reject gate beyond merge |

---

## Roadmap

### Milestone 1: Structured AI Analysis Loop
*Goal: the AI analysis step produces structured, reviewable output — not just a Markdown comment.*

**CR-A — Structured `cr-analyze` output**

Replace the free-form Markdown analysis with a structured JSON result containing:
- `direction_fit`: does this issue align with the product's CRS/UC items?
- `affected_items`: list of DHF items (SRS, SWDD, RISK) that need updating
- `proposed_new_items`: DHF items that should be created
- `design_impact_summary`: human-readable impact statement

The structured output feeds downstream steps (test plan, implementation) rather than requiring a human to re-read and re-interpret.

**CR-B — Test plan generation**

Given a CR and its affected items, compute:
- Which existing test cases (via `@links`) already cover the affected requirements
- Which requirements have no test coverage (need new TCs)
- Which test scenarios require manual testing (flag criteria: UI interaction, hardware interface, safety-critical path)

Output: a test plan checklist attached to the PR, distinguishing auto-covered vs manual-required items.

**CR-C — Structured approval gate**

Replace the "read the PR comment and decide" step with a structured checklist that an engineer explicitly approves:
- [ ] Direction fit confirmed
- [ ] Affected DHF items reviewed
- [ ] Test plan accepted
- [ ] Implementation approach approved

Approval triggers the implementation step. Rejection closes the CR with a reason.

---

### Milestone 2: Closed-Loop Implementation
*Goal: approved plan → AI implements code and DHF in one atomic operation.*

- AI generates code changes and DHF item updates in the same branch
- DHF items (new SRS, updated SWDD, new test cases) are created automatically
- Traceability links are wired without manual YAML editing
- CI validates the result before the PR is opened for human review

---

## Contributing

If you are building medical device software and want to influence this roadmap, the best way is to open an issue describing your workflow. The more concrete the use case, the more directly it shapes development priorities.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get involved.
