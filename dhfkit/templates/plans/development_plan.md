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

## 3. DHF Item Type Model

DHF items follow the V-model hierarchy. Each type has a fixed code prefix and a defined role in
the design and traceability chain.

### 3.1 Item types

| Code | Name | One item per… |
|------|------|---------------|
| `UC` | Use Case | User goal or operating scenario |
| `CRS` | Customer Requirement | Stakeholder need |
| `SYS` | System Requirement | System-level behavioural obligation |
| `SRS` | Software Requirement | Software-level behavioural obligation |
| `MODULE` | Software Module | Software unit defined in the architecture decomposition |
| `SWDD` | Software Detailed Design | Design decisions for an SRS requirement within a module |
| `SYSARCH` | System Architecture | System-level design decision for a SYS requirement |
| `RISK` | Risk | Identified hazard or hazardous situation |
| `RCM` | Risk Control Measure | Mitigation for a risk, implemented as a system requirement |
| `CR` | Change Request | Proposed change driving a DHF update cycle |
| `SOUP` | SOUP | Third-party dependency tracked for IEC 62304 §5.3.3 |
| `REL` | Release | Software release record (IEC 62304 §9) |
| `DEF` | Defect | Tracked problem or non-conformance |

### 3.2 Traceability links

All links are written on the child item and point upward to the parent.

| Link field | Written on | Points to | Meaning |
|------------|-----------|-----------|---------|
| `derives_from` | CRS | UC | Customer requirement derives from a use case |
| `satisfies` | SYS | CRS | System requirement satisfies a customer requirement |
| `design` | SYSARCH | SYS | Architecture item records the design decision for a SYS requirement |
| `derives_from` | SRS | SYS | Software requirement derives from a system requirement |
| `module` | SWDD | MODULE | Detailed design belongs to this software module |
| `implements` | SWDD | SRS | Detailed design implements a software requirement |
| `mitigates` | RCM | RISK | Risk control measure mitigates a risk |
| `implements` | RCM | SYS | Risk control measure is implemented as a system requirement |

### 3.3 Design layer roles

Three item types together describe the software design:

- **SYSARCH** — one per SYS requirement. Records the system-level design decision for that
  specific requirement (which module handles it, what protocol is used, where the boundary falls).
  Requirement-oriented, not module-oriented.
- **MODULE** — one per software unit. Defines each unit's responsibility, key interfaces, and
  internal structure. Declared in the architecture overview, not tied to individual requirements.
- **SWDD** — one per SRS requirement, grouped under a MODULE. Records detailed design decisions
  within a specific module. Must carry both `implements` (SRS ID) and `module` (MODULE ID).
  The combined picture — MODULE overview + its SWDD items — forms the Software Design Document for
  that module.

## 4. Traceability Maintenance

Every change that introduces or modifies DHF items must preserve the traceability
chain. The following coverage rules are enforced by `dhf validate traceability`
and must pass before a CR can be considered complete.

### 4.1 Required coverage

| Rule | Meaning |
|------|---------|
| UC → CRS | Every use case is addressed by at least one customer requirement |
| CRS → SYS | Every customer requirement is allocated to at least one system requirement |
| SYS → SRS | Every system requirement is refined into at least one software requirement |
| SRS → SWDD | Every software requirement has at least one detailed design item |
| SYS → SYSARCH | Every system requirement has at least one architectural design item |
| MODULE → SWDD | Every defined software module has at least one detailed design item |
| RISK → RCM | Every identified risk has at least one risk control measure |

### 4.2 Required links per item type

In addition to coverage, individual items must carry the following upstream links:

| Item type | Required link | Target |
|-----------|--------------|--------|
| CRS | `derives_from` | UC |
| SRS | `derives_from` | SYS |
| SYSARCH | `design` | SYS |
| SWDD | `implements` | SRS |
| SWDD | `module` | MODULE |
| RCM | `mitigates` | RISK |
| RCM | `implements` | SYS |

Missing links are reported as `required traceability failures` by the validator
and block the compliance gate.

## 5. Verification and Testing Strategy

Testing is part of the development plan rather than a parallel process document.
The product family uses layered tests, structured evidence conventions, and CI
contracts that allow runtime outputs to be traced back to controlled requirements.

### 5.1 Test Layers

| Layer | Location | What it covers |
|-------|----------|---------------|
| SYS tests | `tests/sys/` | API-facing and subsystem product behaviour |
| CRS tests | `tests/crs/` | End-to-end scenario and user-facing coverage |
| DHF util tests | `dhfkit/tests/` | DHF CRUD, lifecycle, validation, document generation |

Tests should validate externally visible behavior or controlled interfaces, not
private implementation details.

### 5.2 Evidence Conventions

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

### 5.3 JUnit Contract

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

### 5.4 Local Execution Expectations

Developers are expected to run relevant tests and traceability checks locally
before opening or updating a PR. At minimum:

```bash
pytest tests/ -q --junitxml=test-results/results.xml
medharness --dhf DHF ci test-coverage --junit-dir test-results
medharness --dhf DHF dhf validate traceability
```

Local runs are fast feedback mechanisms. They reduce CI churn but do not replace
the CI record.

### 5.5 CI Expectations

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

### 5.6 Development Tests vs Formal Verification Evidence

Not every local or exploratory test run is formal verification evidence. The
distinction is:

- development tests support day-to-day engineering decisions and debugging
- formal verification evidence is the subset of controlled CI outputs and linked artifacts used to demonstrate requirement coverage and release readiness

This distinction matters because the OSS system promises runtime evidence bundle
generation, not blanket capture of every engineering action.

### 5.7 What Not to Test

- private implementation details instead of observable behavior
- unstable filesystem side effects outside isolated fixtures
- non-deterministic external services as part of the default coverage gate

## 6. CI Pipeline

### 6.1 Product CI

1. **TESTING** — SYS and CRS test suites run and publish JUnit evidence
2. **ACCEPTANCE GATE** — `ci test-coverage` checks requirement-to-test coverage
3. **EVIDENCE** (main only) — `ci evidence bundle` produces runtime audit artifacts
4. **AUDIT** — OSS build hygiene and workflow integrity checks run on PRs

### 6.2 DHF Structural CI

DHF repo CI runs CR validation and design traceability checks. Its role is
structural and document-centric: it ensures the controlled design record stays
coherent as implementation evolves.

### 6.3 Generated Product CI

Scaffolded product repos get:

- test execution with JUnit artifact upload
- `ci test-coverage`
- `ci evidence bundle` on merge to `main`
- `cr-complete.yml` for automatic CR completion on PR merge

## 7. Release and Build

### 7.1 MedHarness

- **Trigger:** push of `v*` tag
- **Output:** Python wheel published to GitHub Releases
- **Release contains:** installable package (harness code and metadata, including `dhfkit`)
- **Release does not contain:** DHF templates as prebuilt document deliverables

### 7.2 dhfkit

- **Package:** `dhfkit` bundled in the `medharness` distribution
- **All DHF operations available via `medharness dhf` after `pip install medharness`.
- **Templates:** bundled within the `medharness` package at `dhfkit/templates/`

### 7.3 Evidence Bundles

Evidence bundles are runtime CI outputs, not release payloads. They are
produced on merge to `main` by `ci evidence bundle` and uploaded as CI artifacts
for audit consumption.

## 8. Document Control

### 8.1 Canonical Product Documents

Formal product documents live in the DHF repository under `DHF/documents/`:

- `DHF/documents/specs/customer_requirement_specification.md`
- `DHF/documents/specs/architecture_design_specification.md`
- `DHF/documents/plans/development_plan.md`

These are the authoritative source for product requirements, architecture, and
development process. MedHarness repo-level docs are derivative summaries.

### 8.2 Document Sources and Generated Output

Files ending in `.md.j2` under `DHF/documents/specs/` are **document sources** —
they contain the project's controlled document narrative (sections, rationale, scope)
with Jinja2 placeholders used only for injecting DHF item tables at generation time.
They are not blank forms; they are the document itself.

`DHF/config/global.yaml` maps each doc type to its source file via the `source:` key
under `document_specifications`. The `output:` key controls where the rendered
Markdown is written. Treat `.md.j2` files like any other controlled document:
update them through the CR workflow, review them in PRs, and keep their narrative
current as the product evolves.

### 8.3 Update Process

- product direction is updated in the CRS narrative chapters when mission, scope, or roadmap changes
- architecture narrative is updated when repo boundaries, delivery mechanics, or agent-guidance structure changes
- this plan is updated when CI, testing, evidence contracts, or release mechanics change
- all updates follow the CR workflow
