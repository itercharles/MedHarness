---
name: Competitive Landscape
description: Market analysis of IEC 62304 / medical device ALM tools competing with CompliantFlow as of April 2026
type: project
---

**Last updated:** 2026-04-02

## Market categories

1. **Traditional enterprise ALM** — Jama Connect, Siemens Polarion, PTC Codebeamer, Perforce Helix ALM. Expensive, GUI-heavy, per-seat pricing, no CI/CD-native workflows.
2. **SaMD-specific compliance wrappers** — Ketryx (dominant, $39M Series B). Sits on top of Jira/GitHub. Strong AI automation but requires cloud, opaque pricing, vendor lock-in.
3. **Medtech QMS platforms** — OpenRegulatory Formwork (99–499 €/month), Qualio. Primarily document/QMS-oriented, not code-native.
4. **Open-source / docs-as-code** — Innolitics RDM (GitHub, ~500 stars). Template-based, generates Word/Markdown docs but no compliance engine, no CI integration, limited maintenance.
5. **Test/static analysis tools** — Parasoft, MATLAB/Simulink, Diffblue. Narrow scope — not full ALM.

## CompliantFlow's key differentiators

- Only CLI-native, Git-native, CI/CD-first DHF platform with automated policy checks (75 automated IEC 62304 checks)
- No per-seat pricing on data access; YAML is open format — no vendor lock-in
- Git as immutable audit trail (GitOps approval model)
- Works with any test runner via JUnit XML boundary
- Self-hostable / air-gap compatible (caveat: Gemini dependency for semantic checks is a current gap)

## ICP recommendation

Seed-to-Series B SaMD or embedded medical device software teams (5–50 engineers), Class II/III devices, needing IEC 62304 compliance without enterprise ALM budget or complexity.

## Positioning risks

- Ketryx has $55M+ in funding and enterprise relationships — estimated down-market move within 18–24 months (Q4 2027). Must capture SaMD startup references before then.
- No GUI is a barrier for QA/RA personas who are not CLI-comfortable (acceptable for current ICP; revisit at enterprise motion stage)
- Gemini API dependency blocks air-gapped customers (a major medtech segment) — classified as HIGH-severity commercial blocker, targeted for v1.3.0
- Innolitics RDM is free and has established credibility but is effectively unmaintained — RDM users are the best near-term acquisition target; migration tooling targeted for v2.0.0
- FDA 21 CFR Part 11: US prospects may challenge Git author attribution as insufficient for e-signature equivalence — documentation brief targeted for v2.0.0

## Opportunity signals

- No per-seat pricing is a direct differentiator vs. all enterprise ALM competitors — should be explicit in positioning, not implicit
- Full IEC 62304 + IEC 82304-1 + ISO 14971 coverage in a single CLI platform has no competitor match — "complete DHF coverage" positioning available once ISO 14971 ships
- One 510(k) case study eliminates the primary sales objection ("auditor unfamiliar with YAML-in-Git") — highest-leverage GTM action available now, requires a business development owner
