# Software Development Plan

**Owner:** Engineering Lead
**Status:** Draft — Starter Content, Replace for Your Project
**Last reviewed:** Template — adapt for your project

> This is a starter plan scaffolded by MedHarness. Replace the content
> below with your project's actual development processes, CI expectations,
> and release model before using this repository for a real product.

This document defines the development lifecycle, verification approach, CI
expectations, and release model for the {{project_name}} product family.

---

## 1. Product Delivery Model

{{project_name}} is delivered from a single tooling-first repository that
contains two complementary layers:

- `medharness` is the orchestration CLI, CI gate logic, and scaffolding system
- `dhfkit` is the reusable DHF engine for items, traceability, lifecycle, and document generation
- product repositories own implementation code, executable tests, and product CI
- DHF repositories (generated from bundled templates) own controlled requirements, architecture, risk, traceability, and formal plan/spec documents

The workflow is designed so that design updates happen before or alongside
implementation, not after it. Structural and design traceability live with the
DHF content. Requirement-to-test coverage and executable evidence live with
the product repository and its CI outputs.

## 2. Development Lifecycle

### 2.1 CR-Driven Change Flow

Every non-trivial change starts from a Change Request (CR) tracked in the DHF:

1. **CR created** — `medharness dhf item create --type CR`
2. **Design updated** — impacted CRS, SYS, SRS, SWDD, SYSARCH, risk, or test-facing items are revised in the DHF as needed
3. **Implementation** — code changes proceed on a branch with the CR ID in the title
4. **PR review** — product CI runs the coverage gate; DHF CI runs structural and design validation
5. **Merge to main** — evidence bundle is produced; CR automation can close the change
6. **Verification** — product evidence and DHF records are reconciled so the traceability chain remains current

### 2.2 Branch and PR Conventions

- Branch naming: `feature/`, `fix/`, `refactor/`
- PR title must include the CR ID: `feat(CR-012): description`
- CR ID is extracted from PR title by CI for automatic CR completion

### 2.3 Responsibility Split

- DHF-side workflows own structure, lifecycle, architecture/design linkage, and document control
- Product-side workflows own executable implementation, test execution, and requirement-to-test evidence
- Cross-repo integrity is maintained through shared CR IDs, linked item IDs, and CI-produced evidence artifacts

## 3. Verification and Testing Strategy

Testing is part of the development plan rather than a parallel process document.
The product family uses layered tests, structured evidence conventions, and CI
contracts that allow runtime outputs to be traced back to controlled requirements.

### 3.1 Test Layers

| Layer | Location | What it covers |
|-------|----------|---------------|
| SYS tests | `tests/sys/` | API-facing and subsystem product behaviour |
| CRS tests | `tests/crs/` | End-to-end scenario and user-facing coverage |
| DHF util tests | `dhfkit/tests/` | DHF CRUD, lifecycle, validation, document generation |

Tests should validate externally visible behavior or controlled interfaces, not
private implementation details.

### 3.2 Evidence Conventions

Executable tests are expected to emit JUnit XML. Test cases should carry stable
test identifiers and requirement links so evidence can be imported or evaluated
consistently across local runs and CI runs.

Format: `TC-SYS-NNN-NNN` or `TC-CRS-NNN-NNN`. Every test function name embeds
the test case ID:

```python
def test_TC_SYS_027_001_init_creates_dhf_structure(tmp_path):
    """
    TC-SYS-027-001: description

    @test_id: TC-SYS-027-001
    @links: SYS-027
    """
```

The `@links` contract connects executable evidence to the DHF requirement chain.
The product repo must prove requirement coverage through test metadata and results.

### 3.3 JUnit Contract

```xml
<testcase name="test_TC_SYS_027_001_...">
  <properties>
    <property name="medharness.id" value="TC-SYS-027-001"/>
    <property name="medharness.links" value="SYS-027"/>
  </properties>
</testcase>
```

`medharness.links` is the contract consumed by coverage workflows and evidence
processing. The evidence bundle is assembled from runtime artifacts that satisfy
this contract.

### 3.4 Local Execution Expectations

Developers are expected to run relevant tests and traceability checks locally
before opening or updating a PR. At minimum:

```bash
pytest tests/ -q --junitxml=test-results/results.xml
medharness --dhf DHF ci test-coverage --junit-dir test-results
medharness --dhf DHF dhf validate traceability
```

Local runs are fast feedback mechanisms. They reduce CI churn but do not replace
the CI record.

### 3.5 CI Expectations

CI is the canonical execution environment for release-quality evidence.
Product-side CI is expected to:

- execute the relevant automated test suites
- persist JUnit XML artifacts
- run `ci test-coverage`
- generate an evidence bundle on merge to `main`

DHF-side CI is expected to:

- validate schemas and required fields
- validate structural traceability and design coverage
- enforce CR-driven document updates where applicable

### 3.6 Development Tests vs Formal Verification Evidence

Not every local or exploratory test run is formal verification evidence. The
distinction is:

- development tests support day-to-day engineering decisions and debugging
- formal verification evidence is the subset of controlled CI outputs and linked artifacts used to demonstrate requirement coverage and release readiness

This distinction matters because the OSS system promises runtime evidence bundle
generation, not blanket capture of every engineering action.

### 3.7 What Not to Test

- private implementation details instead of observable behavior
- unstable filesystem side effects outside isolated fixtures
- non-deterministic external services as part of the default coverage gate

## 4. CI Pipeline

### 4.1 Product CI

1. **TESTING** — SYS and CRS test suites run and publish JUnit evidence
2. **ACCEPTANCE GATE** — `ci test-coverage` checks requirement-to-test coverage
3. **EVIDENCE** (main only) — `ci evidence bundle` produces runtime audit artifacts
4. **AUDIT** — OSS build hygiene and workflow integrity checks run on PRs

### 4.2 DHF Structural CI

DHF repo CI runs CR validation and design traceability checks. Its role is
structural and document-centric: it ensures the controlled design record stays
coherent as implementation evolves.

### 4.3 Generated Product CI

Scaffolded product repos get:

- test execution with JUnit artifact upload
- `ci test-coverage`
- `ci evidence bundle` on merge to `main`
- `cr-complete.yml` for automatic CR completion on PR merge

## 5. Release and Build

### 5.1 MedHarness

- **Trigger:** push of `v*` tag
- **Output:** Python wheel published to GitHub Releases
- **Release contains:** installable package (harness code and metadata, including `dhfkit`)
- **Release does not contain:** DHF templates as prebuilt document deliverables

### 5.2 dhfkit

- **Package:** `dhfkit` bundled in the `medharness` distribution
- **All DHF operations available via `medharness dhf` after `pip install medharness`.
- **Templates:** bundled within the `medharness` package at `dhfkit/templates/`

### 5.3 Evidence Bundles

Evidence bundles are runtime CI outputs, not release payloads. They are
produced on merge to `main` by `ci evidence bundle` and uploaded as CI artifacts
for audit consumption.

## 6. Document Control

### 6.1 Canonical Product Documents

Formal product documents live in the DHF repository under `DHF/documents/`:

- `DHF/documents/specs/customer_requirement_specification.md`
- `DHF/documents/specs/architecture_design_specification.md`
- `DHF/documents/plans/development_plan.md`

These are the authoritative source for product requirements, architecture, and
development process. MedHarness repo-level docs are derivative summaries.

### 6.2 Generated Documents

DHF item content is rendered into specification documents via Jinja2 templates
under `DHF/documents/specs/`. Generated output is runtime-only and need not be
committed as source material.

### 6.3 Update Process

- product direction is updated in the CRS narrative chapters when mission, scope, or roadmap changes
- architecture narrative is updated when repo boundaries, delivery mechanics, or agent-guidance structure changes
- this plan is updated when CI, testing, evidence contracts, or release mechanics change
- all updates follow the CR workflow
