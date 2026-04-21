---
name: AI-First Framework Strategy
description: Strategic analysis of repositioning CompliantFlow as AI-first medtech development framework; gaps, roadmap changes, risks (April 2026)
type: project
---

**Analysis date**: 2026-04-21

**Core thesis**: Reposition from "compliance gate" to "AI-first development framework for medical device software" where CompliantFlow is the trust layer between AI-generated code and regulatory requirements.

**Three-layer model**:
1. AI layer (AI-harness) -- guides AI agents to generate compliant code and DHF docs
2. Validation layer (CompliantFlow) -- CI gate enforcing compliance semantics
3. Infrastructure layer (compliantflow init) -- one-command setup of both repos

**Critical gaps identified**:
1. Product repo has no AI harness (CRITICAL) -- AI in product repo has zero DHF/compliance context
2. No cross-repo coordination protocol (HIGH) -- no mechanism for product-repo AI to trigger DHF updates
3. No framework packaging/narrative (MEDIUM) -- three layers not presented as coherent framework

**Recommended first move**: CR-055 (Product Repo AI Harness) -- extend `compliantflow init` to write AI harness to product repo. Low technical risk, high strategic value, independently shippable as v2.0.x.

**Roadmap impact**:
- v2.1.0 expanded: add CR-041 (draft pre-validation) + CR-043 (machine-readable reports) + CR-055
- v2.2.0 reframed as "AI Framework Maturity" with cross-repo coordination protocol
- v3.0.0 unchanged

**Key risk**: Positioning runs ahead of product reality. Mitigation: ship CR-055 and validate with beta users before updating public messaging.

**How to apply**: When evaluating new CRs or roadmap changes, assess whether they strengthen or weaken the three-layer framework model. Product repo AI harness is the gating item for the positioning shift.
