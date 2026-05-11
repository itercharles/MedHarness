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
highest-value remaining near-term work breaks down into the following phases.

### Recently Completed

The following areas are now implemented and are no longer the primary roadmap
focus:

- structured CR analysis output, including companion machine-readable spec
  artifacts and stronger `test_plan` contracts
- explicit machine-readable approval and stage-status CLI surfaces
- deterministic preflight validation for design, code, and coupled
  implementation branches
- stronger spec-to-design coupling, including validation that proposed DHF
  items are actually materialized

These completed slices correspond to the earlier Phase 1 and Phase 2 work.

### Phase 3: Risk Management as a First-Class Workflow

With the core CR loop stronger, the next major gap is deeper risk integration.

Priority areas:

- identifying which risk items are affected during CR analysis
- adding stronger CI checks for risk-to-requirement and risk-to-verification
  coverage
- validating the approach against real WebTPS risk management needs

This phase maps most directly to:

- stronger risk and verification flows

### Phase 4: Adoption and Ecosystem

After the core workflow is stronger, the project becomes more useful when teams can adopt pieces of it
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
