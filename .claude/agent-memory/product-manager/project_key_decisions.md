---
name: Key Product Decisions
description: Strategic product decisions, their rationale, and date made — reference before making roadmap changes
type: project
---

## 2026-04-21: AI-First Framework Repositioning Analysis

**Decision**: Analyzed opportunity to reposition CompliantFlow from "compliance gate" to "AI-first development framework for medical device software." Recommendation: proceed, but ship product substance (CR-055: product repo AI harness) before updating public positioning.

**Why**: No competitor addresses the AI coding + medtech compliance intersection. The two-repo model (product + DHF) has a critical gap: product repo has no AI harness, so AI agents working on code have zero compliance context. This is the single biggest blocker to the framework narrative being real.

**How to apply**: CR-055 (product repo AI harness) is P0. v2.1.0 scope should expand to include CR-041 (draft pre-validation) and CR-043 (machine-readable reports) pulled forward from v2.2.0. Positioning update happens after CR-055 ships and is validated with 2+ beta users.

## 2026-04-07: CR Closure Automation

**Decision**: CR closure is automated via post-merge CI (cr-transition.yml in compliantflow-dhf). Never manually close CRs before PR merge -- Phase 0 CI rejects PRs with closed CR status.

**Why**: Prior incident where pre-closing a CR caused CI rejection. The automation is the single source of truth for CR lifecycle.

**How to apply**: Always confirm CR is `planned` before opening a PR. Do not transition CRs to `closed` manually as part of development workflow.

## 2026-04-02: Ketryx Competitive Timeline

**Decision**: Ketryx ($55M raised) estimated to move down-market to SaMD startup segment by Q4 2027. CompliantFlow must have 3-5 paying customer references with regulatory submissions before then.

**Why**: At that point, defensibility shifts from feature differentiation to reference credibility and switching cost. A 510(k) case study is the highest-leverage GTM action.

**How to apply**: Prioritize actions that accelerate customer acquisition and submission references over feature completeness.

## 2026-04-02: Web UI Is Not a Priority

**Decision**: Web UI does not block core compliance engine work. Deferred to v3.0.0 enterprise motion. CR-030 (web dashboard) closed -- CI already generates PDF artifacts that serve the QA/RA persona.

**Why**: Primary ICP is engineering-led. GUI investment before CLI value proposition is proven dilutes focus.

**How to apply**: Do not prioritize GUI features. If QA/RA persona access comes up, point to CI-generated PDF artifacts.
