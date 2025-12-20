# Hybrid Test Verification System

This document explains how to set up and use the hybrid test verification system that supports both automated and manual tests.

## Overview

CompliantFlow supports two types of test verification:

1. **Automated Tests** - Run in CI/CD pipeline (GitHub Actions), results retrieved dynamically
2. **Manual Tests** - Executed manually, status tracked in YAML files with audit trail

## Setup

### 1. Configure Test Types

Add `test_type` field to your test case YAML files:

```yaml
# Automated test
id: TC-SYS-001
test_type: automated
title: "Verify core initialization"
# No verification_status needed - comes from CI/CD

# Manual test
id: TC-CRS-001
test_type: manual
title: "User acceptance test"
verification_status: PENDING
verified_by: ""
verified_date: ""
verification_notes: ""
```

### 2. GitHub Actions Setup (for automated tests)

The workflow is already configured in `.github/workflows/test.yml`.

**To enable:**
1. Push your code to GitHub
2. GitHub Actions will automatically run tests
3. Test results are uploaded as artifacts

### 3. Local Testing (optional)

For local development without GitHub:

```bash
# Run tests locally
pytest tests/ --junitxml=DHF/test-results/latest.xml

# CompliantFlow will read from this file
```

### 4. GitHub Token (optional, for API mode)

To fetch results directly from GitHub API:

1. Create Personal Access Token: https://github.com/settings/tokens
2. Required scopes: `repo`, `actions:read`
3. Create `.env` file:
   ```
   GITHUB_TOKEN=your_token_here
   ```
4. Update `project_config.yaml`:
   ```yaml
   test_integration:
     automated:
       provider: github  # Change from 'local'
       github:
         repository: your-username/CompliantFlow
   ```

## Usage

### Viewing Test Results

**Traceability Matrix:**
- Shows verification status for all tests
- 🤖 icon for automated tests
- 👤 icon for manual tests
- Status updates automatically from CI/CD

**Manual Testing Page:**
- Navigate to "Manual Testing" in sidebar
- View all manual test cases
- Filter by status
- Update verification status

### Writing Automated Tests

Test function names must include the test case ID:

```python
def test_TC_SYS_001_description():
    """TC-SYS-001: Test description"""
    # Your test code
    assert True
```

Supported formats:
- `test_TC_SYS_001_...`
- `test_tc_sys_001_...`

### Updating Manual Tests

**Option 1: Via UI (Coming Soon)**
1. Go to "Manual Testing" page
2. Select test case
3. Update status and add notes
4. Submit

**Option 2: Edit YAML Directly**
```yaml
id: TC-CRS-001
test_type: manual
verification_status: PASS
verified_by: "John Doe"
verified_date: "2024-12-20"
verification_notes: "All acceptance criteria met"
```

## Troubleshooting

**Tests not showing up:**
- Ensure test function names include test ID
- Check JUnit XML file exists: `DHF/test-results/latest.xml`
- Verify `test_type` field is set in YAML

**GitHub Actions not running:**
- Check workflow file: `.github/workflows/test.yml`
- Verify repository has Actions enabled
- Check GitHub Actions tab for errors

**Status shows PENDING:**
- For automated: Tests haven't run yet or XML file missing
- For manual: `verification_status` not set in YAML

## Architecture

```
Test Case (YAML)
    ↓
test_type field
    ↓
┌───────────┴──────────┐
│                      │
automated            manual
    ↓                  ↓
GitHub Actions      YAML file
    ↓                  ↓
JUnit XML          verification_status
    ↓                  ↓
└───────────┬──────────┘
            ↓
    TestResultsProvider
            ↓
      CompliantFlow UI
```

## Files

- `src/test_results/` - Provider infrastructure
- `.github/workflows/test.yml` - CI/CD configuration
- `tests/` - Automated test files
- `DHF/test-results/` - Test results and audit logs
- `DHF/config/project_config.yaml` - Integration configuration
