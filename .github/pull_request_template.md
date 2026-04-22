# Summary

Describe the change concisely. Include the CR ID: **CR-XXX**

## DHF Updates

- List exact compliantflow-dhf item files changed
- Or state explicitly: `No DHF update required`

## Automated Validation

List the commands actually run:

- `.venv/bin/python -m pytest tests/ -q`

## Manual Testing Required

Describe the manual testing still required, with concrete steps.

Example:
1. `pip install dist/*.whl`
2. `compliantflow init` in a temp directory
3. Verify generated `.github/workflows/` files contain expected content

## Remaining Risk / Follow-up

List any residual risk, known gaps, or follow-up items.
