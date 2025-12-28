# Test Fixtures - Baseline DHF

## Purpose
This directory contains a **static snapshot** of the DHF used for browser testing. This ensures tests are stable and repeatable, independent of changes to the production DHF.

## Structure
```
baseline_dhf/
├── items/          ← All DHF items at time of snapshot
├── config/         ← Project configuration
├── documents/      ← Document templates
└── governance/     ← Governance policies
```

## Usage
Tests copy this baseline to a temporary directory for each test run:
1. Test starts → Copy `baseline_dhf/` to `/tmp/test_dhf_*/`
2. Test runs → Modifies temp copy (e.g., creates SRS-999)
3. Test ends → Deletes temp copy
4. Production DHF remains untouched ✅

## Updating the Baseline
When you need to update test data (e.g., add new items for testing):

```bash
# From project root
cd /Users/chenwenliang/code/CompliantFlow

# Update baseline with current DHF
rm -rf tests/crs/fixtures/baseline_dhf/*
cp -r DHF/items tests/crs/fixtures/baseline_dhf/
cp -r DHF/config tests/crs/fixtures/baseline_dhf/
cp -r DHF/documents tests/crs/fixtures/baseline_dhf/
cp -r DHF/governance tests/crs/fixtures/baseline_dhf/

# Commit the updated baseline
git add tests/crs/fixtures/baseline_dhf/
git commit -m "Update test baseline DHF"
```

## Snapshot Information
- **Created**: 2025-12-28
- **Source**: Production DHF at commit [current]
- **Items**: All current DHF items
- **Purpose**: Stable browser test data

## Benefits
✅ **Stable**: Tests don't break when production DHF changes  
✅ **Repeatable**: Same data every test run  
✅ **Fast**: No need to sync with production  
✅ **Isolated**: Production DHF never modified  
✅ **Version Controlled**: Baseline tracked in git

## Notes
- This is a **snapshot**, not a live copy
- Update when you need different test data
- Keep minimal - only items needed for tests
- Document any special test items added
