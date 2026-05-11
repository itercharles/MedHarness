# Roadmap

## Purpose

This document is the canonical public roadmap for MedHarness.

It describes the project's likely direction and near-term priorities. It is not a delivery commitment. Priorities may change based on contributor capacity, user feedback, and what is learned from real-world use.

## Scope

Current framing:

**MedHarness is Git-native DHF and design-control tooling for medical-device software teams.**

This roadmap assumes that MedHarness remains focused on:

- DHF and design-control execution for software teams
- traceability, validation, and evidence flows
- Git- and CI-centered engineering workflows
- AI-assisted changes with explicit review and approval points

This roadmap does not assume that MedHarness becomes:

- a full eQMS
- a company-wide quality operating system
- a full replacement for broad enterprise ALM platforms

That scope keeps the roadmap specific and credible.

## Current Strengths

Based on the current repository, MedHarness already provides:

- DHF item creation, update, validation, and document generation
- traceability validation and requirement coverage checks
- CI commands for DHF validation, test coverage, and evidence bundling
- AI-assisted CR analysis, design, and development stages
- machine-readable CR stage and approval status via the CLI
- a scaffolded single-repo workflow for software teams managing DHF artifacts alongside code

These are the capabilities the public roadmap should build on.

## Public Roadmap Principles

Future roadmap updates should follow a few simple rules:

- describe themes, not promises
- separate current capabilities from proposed ones
- avoid exact delivery dates unless the work is already committed
- prefer `planned`, `proposed`, or `under consideration` over certainty language
- keep the roadmap aligned with the project's DHF-focused scope

## Roadmap Themes

### 1. More Structured CR Outputs

One likely next step is to make CR-stage outputs easier for both humans and automation to consume.

Examples:

- structured machine-readable artifacts alongside Markdown specs
- more consistent output contracts between analyze, design, and develop stages
- clearer handoff data between workflow stages

Why this matters:

- reduces ambiguity between stages
- improves automation reliability
- makes the workflow easier to integrate with other tools

### 2. Stronger Approval and Review Gates

Another likely area of work is making approval points more explicit and easier to audit.

Examples:

- clearer machine-readable approval signals
- better status reporting around staged CR progress
- stronger enforcement of review checkpoints before downstream automation runs

Why this matters:

- improves trust in AI-assisted workflows
- makes design-control behavior easier to demonstrate
- aligns better with regulated review expectations

### 3. Better Support for Complex Changes

The current workflow is well suited to straightforward changes. A natural next direction is improved handling of larger, multi-file, cross-cutting changes.

Examples:

- better structured inputs for implementation stages
- improved pre-validation before generated changes are proposed
- more reliable linkage between code changes, DHF items, and evidence

Why this matters:

- expands the practical usefulness of the project
- reduces manual cleanup in more complex workflows
- makes the end-to-end story stronger for real software teams

### 4. Stronger Risk and Verification Flows

MedHarness already includes traceability and coverage concepts. A likely next step is deeper support for risk-aware workflows.

Examples:

- better linkage between risk items, requirements, and tests
- clearer handling for automated versus manual verification evidence
- stronger reporting around verification completeness

Why this matters:

- improves DHF usefulness
- strengthens the regulated software story
- helps teams keep evidence closer to the actual engineering workflow

### 5. Better Adoption Paths

Open-source adoption improves when the project is easy to try incrementally.

Examples:

- better standalone `dhfkit` guidance
- improved quickstarts and example projects
- cleaner bridges to external systems when teams need them
- reusable tooling for common software stacks

Why this matters:

- lowers trial friction
- helps teams adopt MedHarness without major process disruption
- supports both small teams and more mature organizations

## Near-Term Priorities

If the project stays aligned with its current DHF-focused direction, the
highest-value near-term work breaks down into a few concrete phases.

### Phase 1: Complete the Analysis Loop

The immediate goal is to make CR analysis output reliably machine-readable and
easier for downstream stages to consume.

Priority areas:

- companion structured artifacts alongside Markdown specs
- automated test-plan generation, including clearer criteria for what must
  remain manual
- explicit machine-readable approval signals for stage advancement

This phase maps most directly to:

- more structured CR outputs
- stronger approval and review gates

### Phase 2: Closed-Loop Implementation for Complex CRs

Once the analysis loop is stronger, the next step is handling larger,
cross-cutting changes more reliably.

Priority areas:

- documenting real human intervention points on non-trivial WebTPS CRs so the
  next automation layer is based on observed gaps, not assumptions
- tighter coupling of implementation changes, DHF item updates, and
  traceability in one working branch
- moving validation earlier so issues are caught before a PR is opened

Observed WebTPS intervention points that inform this phase:

- cross-repo touchpoint discovery still requires human judgment on complex CRs:
  deciding which frontend, backend, and DHF surfaces actually belong in scope
- new DHF item creation is not just a file-write problem:
  the human still decides whether a change needs a new requirement, design, or
  risk item versus an update to an existing one
- implementation branches need an explicit coupled-change contract:
  spec, DHF item YAML, code, and traceability annotations must move together or
  reviewers lose confidence in what the branch actually proves
- deterministic preflight checks need to run before PR creation:
  missing DHF updates or missing `@links` annotations are cheaper to catch
  before review starts than after a branch is already under review

This phase maps most directly to:

- better support for complex changes

### Phase 3: Risk Management as a First-Class Workflow

After the core CR loop is stronger, the next major gap is deeper risk
integration.

Priority areas:

- identifying which risk items are affected during CR analysis
- adding stronger CI checks for risk-to-requirement and risk-to-verification
  coverage
- validating the approach against real WebTPS risk management needs

This phase maps most directly to:

- stronger risk and verification flows

### Phase 4: Adoption and Ecosystem

Longer term, the project becomes more useful when teams can adopt pieces of it
incrementally and connect it to their existing stack.

Priority areas:

- reducing friction around test-result integration for common software stacks
- improving `dhfkit` as a more polished standalone dependency
- supporting bridge patterns where MedHarness coexists with incumbent eQMS or
  ALM systems

This phase maps most directly to:

- better adoption paths

## Benchmark

The clearest benchmark for whether the positioning is real is this:

- from a GitHub issue to a compliant merged PR with a full DHF trail in under
  30 minutes
- for a non-trivial change
- reliably
- on WebTPS
- observable in one automation run

## What the Project Should Likely Avoid

To keep the roadmap clear and credible, MedHarness should avoid framing itself publicly as:

- a full QMS roadmap
- a broad enterprise ALM replacement roadmap
- a promise of fully autonomous regulated software development

Those directions are broader than the current project scope and would make the public story less precise.

## Contributor Guidance

Contributors proposing new features should ask:

- Does this strengthen DHF and design-control execution for software teams?
- Does this improve traceability, validation, or evidence flow?
- Does this make the Git and CI workflow more usable or more trustworthy?
- Does this stay within the project's public scope?

If the answer is yes, the proposal is likely aligned.

## Bottom Line

The most useful public roadmap for MedHarness is a focused one:

- improve DHF and traceability workflows inside normal development practice
- make approval and evidence gates clearer for AI-assisted changes
- support more realistic software changes across code, documents, and tests
- improve risk and verification linkage
- make adoption easier without turning the project into a full QMS

That keeps the roadmap credible, contributor-friendly, and consistent with the project's open-source positioning.
