# ADR-002: GitOps Approval for DHF Items

**Status:** Accepted
**Date:** 2026-01-01
**Deciders:** Engineering Lead

---

## Context

DHF items (requirements, risks, test cases, architecture) need an approval workflow. Traditional regulated development uses explicit approval steps: someone reviews a document and signs it. This typically happens in a document management system with a separate approval record.

Alternatives considered:
1. Explicit `status: approved` field on every item, changed via a transition command
2. A web UI with reviewer assignment and sign-off workflow
3. GitOps: landing on `main` via a merged PR is the approval event

## Decision

DHF items are approved by landing on `main`. No explicit `status` field, no approval record in the YAML, no workflow engine.

The PR review process serves as the approval workflow: the PR is the review, the merge is the sign-off, and the Git commit is the timestamped audit record.

Items with explicit multi-state lifecycles (CR, REL, DEF) are exceptions — these use `python -m dhf_util item transition` because they have distinct states that need to be machine-readable (e.g. Phase 0 checks that a CR is `new/analyzing/developing` before allowing a PR).

## Consequences

**Positive:**
- No approval infrastructure to build or maintain — GitHub PR review is the mechanism
- Git history is the complete audit trail: who approved, when, what changed
- Works naturally with AI-driven workflows (CR-056): AI opens a PR, human reviews and merges
- Eliminates the "approved but not merged" state that creates compliance debt

**Negative:**
- Main branch is the only canonical "approved" state — feature branches are inherently unapproved
- Auditors unfamiliar with Git-based approval workflows may require explanation
- No granular approval roles (any reviewer with merge rights can approve any item type)

**Constraints this imposes:**
- Items on feature branches must never be referenced as approved in compliance checks
- The Phase 0 gate must enforce that CRs exist and are in a valid in-progress state before any work PR can merge
