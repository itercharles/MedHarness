# Technical Strategy

**Owner:** Engineering Lead
**Status:** Active
**Last reviewed:** 2026-04-22

This document records the durable architectural direction and engineering principles for CompliantFlow. It is the authoritative input for architecture-class change requests. Update when architectural boundaries, deployment model, or foundational technical principles change — not when individual features ship.

---

## Architectural Principles

### 1. Two-CLI split: compliantflow is read-only

`compliantflow/` (the user-facing CLI) is strictly read-only — analysis, traceability, compliance reporting. DHF mutations (creating/updating items, lifecycle transitions) go through `python -m utils` in the DHF repository.

Do not add write operations to `CompliantFlowCore`. This enforces separation of concerns and ensures the compliance tool cannot corrupt the audit record it is evaluating.

### 2. Open YAML, Git as audit trail

All DHF content is plain YAML files in a Git repository. Every change is attributed, timestamped, and branchable. The format is readable without the tool.

Do not introduce proprietary storage formats, database-backed item state, or server-side mutation APIs. These would violate the open-format constraint that differentiates CompliantFlow from Jama, Polarion, and Codebeamer.

### 3. Compliance gate is CI, not periodic review

Compliance enforcement happens on every PR via the CI gate — not as a batch review or audit event. This is the core architectural commitment of the product.

Do not design features that rely on or encourage batch compliance remediation. Features should strengthen the per-commit gate, not work around it.

### 4. Local execution first

The tool runs entirely locally. No cloud backend, no external service calls required for core functionality (compliance checks, traceability, reporting). This is a feature for regulated customers with data residency requirements.

Cloud services (Gemini semantic checks) are opt-in via API key. Features that require external network access must be explicitly opt-in and gracefully degraded when unavailable.

### 5. GitOps approval for DHF items

DHF items (UC, CRS, SYS, SRS, SWDD, SYSARCH, RISK, RCM, SOUP, TC) are approved by landing on `main`. No explicit approval workflow, no status field, no workflow engine. The PR review process is the approval.

Items with explicit lifecycle transitions (CR, REL, DEF) use `python -m utils item transition` — these are the only exceptions.

### 6. Traceability is a graph, not a matrix

The traceability model is a directed graph where edges run child → parent (e.g. SRS `derives_from` SYS). `descendants()` means business-upstream (toward requirements); `ancestors()` means business-downstream (toward tests). This is the opposite of the natural English reading — document it rather than fight it.

Do not add a secondary traceability representation. The graph is the single source of truth; the PDF traceability matrix is a projection of it.

---

## Architectural Layers

| Layer | Location | Responsibility |
|---|---|---|
| User CLI | `compliantflow/cli.py` | Command surface, argument parsing, output formatting |
| Compliance engine | `compliantflow/policy/` | Policy check evaluation, governance file loading |
| Traceability | `compliantflow/graph.py` | DHF graph construction and traversal |
| Reporting | `compliantflow/reporting/` | PDF/JSON output generation |
| DHF utilities | `compliantflow-dhf/DHF/utils/` | Item CRUD, lifecycle transitions, schema validation |
| AI harness | `AI-harness/` | Agent context, checklists, model adapters |
| Init command | `compliantflow/init_cmd.py` | Template delivery for both repos |

Changes should stay in the owning layer. Cross-layer changes require explicit justification.

---

## Engineering Guardrails

Avoid:

- Adding write operations to `compliantflow/` — all mutations belong in `python -m utils`
- Designing for hypothetical future requirements — three similar lines is better than a premature abstraction
- Adding cloud service dependencies that are not explicitly opt-in with graceful degradation
- Introducing compliance checks that invoke external LLMs in default CI runs — they break offline use and slow the gate
- Bypassing the CI gate or adding `--skip` flags to compliance checks
- Storing secrets or tokens in DHF YAML files

---

## DevOps Strategy

The CI pipeline (`ci-pipeline.yml`) is the primary delivery vehicle for compliance evidence. It must:

- Run on every PR with a defined four-phase gate
- Generate compliance reports and traceability matrix on every merge to `main`
- Produce a distributable evidence package on every release tag (`v*`)

Near-term DevOps priorities:

- AI-driven CR workflow (cr-analyze, cr-develop, cr-spec-iterate) — delivered in v2.0.x
- Reproducible release bundle (wheel + DHF PDF artifacts) — delivered in v2.0.x
- Post-merge evidence import and CR auto-close — delivered in v2.0.x

Future:

- Preview environment for onboarding demos
- SBOM generation on release
- Signed release artifacts (v3.0.0 scope)

---

## Technology Choices

| Choice | Decision | Rationale |
|---|---|---|
| Python | Primary implementation language | Target users (QA/RA engineers, SaMD devs) have Python in their stack; pip delivery is frictionless |
| WeasyPrint | PDF generation | No Java dependency, CSS-driven layout, works offline |
| PyYAML | DHF item serialization | Readable format, no schema lock-in |
| GitHub Actions | CI/CD | Dominant in target customer segment; no additional tooling required |
| Claude Code CLI | AI automation in CI | `claude -p --dangerously-skip-permissions` is the current implementation; Claude API compatibility is a design constraint |
