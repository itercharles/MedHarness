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

If the project stays aligned with its current DHF-focused direction, the highest-value public priorities are likely:

1. clearer DHF item and traceability workflows across CR stages
2. stronger approval and review gates for AI-assisted changes
3. better support for complex software changes that touch code, DHF artifacts, and evidence together
4. stronger linkage between requirements, risks, verification, and generated evidence
5. easier adoption for software teams using Git- and CI-based development

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
