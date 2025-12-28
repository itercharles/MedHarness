# CRS Browser Tests - Test Data Management

## Key Points

### Directory Path Handling

**Problem**: `project_config.yaml` contains directory paths like:
```yaml
doc_types:
  - code: CRS
    directory: 01_req_crs  # Relative path
```

**Solution**: 
- ✅ Paths are **relative** to DHF root
- ✅ Copy entire config as-is
- ✅ Set `DHF_ROOT` env var to test directory
- ✅ Application resolves paths correctly

### Test Data Structure

```
/tmp/test_dhf_XXXXX/
├── config/
│   └── project_config.yaml (copied, paths are relative)
├── items/
│   ├── 00_uc/
│   │   └── UC-001.yaml (minimal test data)
│   ├── 01_req_crs/
│   │   ├── CRS-001.yaml
│   │   └── CRS-002.yaml
│   └── ...
├── documents/
│   └── specifications/
│       └── templates/ (copied)
└── governance/
    └── IEC_62304.yaml (copied)
```

### Configuration Validation

The `conftest.py` validates that config paths are relative:
```python
for doc_type in config['doc_types']:
    directory = doc_type['directory']
    assert not directory.startswith('/'), \
        "Config has absolute path - should be relative"
```

### Running Tests

**Local**:
```bash
# Start Streamlit with test DHF
DHF_ROOT=/tmp/test_dhf_XXXXX streamlit run src/app.py &

# Run tests
pytest tests/crs/ -v
```

**CI/CD** (GitHub Actions):
```yaml
- name: Setup test DHF
  run: |
    export TEST_DHF=$(mktemp -d)
    # Setup happens in conftest.py
    
- name: Start Streamlit
  run: |
    DHF_ROOT=$TEST_DHF streamlit run src/app.py &
    sleep 10
    
- name: Run CRS tests
  run: pytest tests/crs/ -v
```

### Safety Checks

1. ✅ **Isolated directory**: Tests use temp directory
2. ✅ **Relative paths**: Config paths are relative
3. ✅ **Cleanup**: Temp directory deleted after tests
4. ✅ **No production impact**: Real DHF untouched

This approach ensures tests are safe and reproducible!
