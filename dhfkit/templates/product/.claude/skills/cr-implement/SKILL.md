---
name: cr-implement
description: Implement an approved CR spec — reads DHF spec and implements product code changes
argument-hint: "<CR-NNN>"
---

You are implementing an approved Change Request for {{project_name}}.

CR ID: $ARGUMENTS

1. Read the approved spec from the DHF repo (path will be in AI-harness/context.md or passed directly).
2. Implement the product code changes described in the spec.
3. Update or add tests as required by the test plan section.
4. Do NOT modify DHF items — those belong in the DHF repo.
5. Create a PR with title format: `feat($ARGUMENTS): <brief description>`

Follow the spec precisely. Small deviations are allowed only when the repo state makes them
necessary — document any deviation in the PR description.
