# GitHub Copilot Instructions — Product Repository
#
# Copy this file to .github/copilot-instructions.md to enable GitHub Copilot support.
# Content mirrors AI-harness/context.md — update both if the project context changes.

This is a medical device software repository managed with CompliantFlow.
The Design History File (DHF) lives in a separate repo: {{dhf_repo}}.

## Key rules

- Before writing code, check if the change requires a DHF update (new/changed requirement, risk, architecture, or test)
- Every tracked change starts with a CR in the DHF repo — include the CR ID in branch name and PR title
- The compliance CI gate rejects PRs without a CR ID in the title
- Standards: {{standards}}

## When DHF update is needed

- New or changed user-facing behaviour → UC or CRS item
- New or changed system/software behaviour → SYS or SRS item
- New risk or mitigation → RISK or RCM item
- Architecture change → SYSARCH item
- New third-party library → SOUP item
- New or changed test → TC item with @links tags

## Local compliance check

```bash
DHF_DIR="../$(basename {{dhf_repo}})/DHF"
GOVERNANCE_DIR="../$(basename {{dhf_repo}})/governance"
compliantflow --dhf "$DHF_DIR" validate traceability
compliantflow --dhf "$DHF_DIR" status --governance-dir "$GOVERNANCE_DIR"
```

See AI-harness/context.md for full reference.
