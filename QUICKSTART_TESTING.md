# Quick Start Guide - Test Integration

## Setup (5 minutes)

### 1. Install pytest
```bash
cd src
pip install pytest pytest-cov
```

### 2. Run tests locally
```bash
pytest ../tests/test_core.py --junitxml=../DHF/test-results/latest.xml -v
```

### 3. View results
- Refresh CompliantFlow in browser
- Navigate to "Traceability" page
- See test statuses with 🤖 (automated) or 👤 (manual) icons

## Test Case Configuration

### Automated Test
```yaml
id: TC-SYS-001
test_type: automated
title: "Test description"
# No verification_status - comes from CI/CD
```

### Manual Test
```yaml
id: TC-CRS-001
test_type: manual
title: "Test description"
verification_status: PENDING
verified_by: ""
verified_date: ""
```

## GitHub Actions (Optional)

1. Push code to GitHub
2. Actions run automatically
3. Results uploaded as artifacts
4. CompliantFlow reads them dynamically

For API mode, create GitHub token and add to `.env`:
```
GITHUB_TOKEN=your_token_here
```

## Documentation

See [TEST_INTEGRATION.md](file:///Users/chenwenliang/code/CompliantFlow/TEST_INTEGRATION.md) for complete guide.
