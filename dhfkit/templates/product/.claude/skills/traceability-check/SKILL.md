---
name: traceability-check
description: Check test coverage traceability for this product repo against the DHF
argument-hint: "[CR-NNN to focus on a specific CR]"
---

You are checking requirement-to-test traceability for {{project_name}}.

1. Run `medharness ci test-coverage` and capture the output.
2. List any SYS/SRS requirements with no linked test cases.
3. If $ARGUMENTS is set, focus on items linked to that CR.
4. Suggest test IDs to add based on uncovered items.

Output a coverage table: Item ID | Title | Covered? | Linked Tests
