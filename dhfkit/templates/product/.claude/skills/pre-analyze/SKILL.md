---
name: pre-analyze
description: Pre-flight DHF analysis before opening a CR — checks direction fit, finds affected items, identifies coverage gaps
argument-hint: "<brief description of proposed change>"
---

You are helping a developer understand the DHF impact of a proposed change to {{project_name}}.

1. Read `AI-harness/context.md` for current DHF state.
2. Check direction fit: does this change align with the current SRS/CRS scope?
3. Identify DHF items likely to be affected (list by ID and title).
4. Flag any open traceability gaps that this change touches.
5. Recommend whether a CR is needed or if this is within existing scope.

Keep output concise — this is a developer pre-check, not a full spec.
