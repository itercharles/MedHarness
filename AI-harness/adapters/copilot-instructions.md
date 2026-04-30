# GitHub Copilot Instructions — CompliantFlow
#
# Copy this file to .github/copilot-instructions.md to enable GitHub Copilot support.
# Content mirrors AI-harness/context.md — update both if the project context changes.

CompliantFlow is a CLI compliance gate for medical device software (IEC 62304, ISO 14971).
The DHF lives in a separate repo: compliantflow/compliantflow-dhf.
PYTHONPATH=.:compliantflow-dhf/DHF is required for CLI and compliance checks.

## Key rules

- CompliantFlowCore remains analysis-oriented; DHF automation goes through adapter/facade APIs
- Product repos must not depend on DHF storage paths or direct file edits
- Graph edges run child → parent; descendants() = upstream toward requirements
- Requirement items (UC, CRS, SYS, SRS, SWDD, ...) are approved by landing on main
- CR, REL, DEF use explicit lifecycle transitions
- Always create a CR before writing code; include CR ID in branch name and PR title
- Run `.venv/bin/python -m pytest tests/ -q` before pushing

## Environment

```bash
pip install dhf_util
.venv/bin/pytest tests/ -q
```

See AI-harness/context.md for full reference.
