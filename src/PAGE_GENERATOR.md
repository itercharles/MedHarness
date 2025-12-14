# Page Generator

Automatically generates Streamlit page files from `DHF/config/project_config.yaml`.

## Why?

All pages use the same universal template (`universal_page_template.py`). Instead of manually creating/updating page files when adding new item types, this script auto-generates them from configuration.

## Usage

### Generate Pages

```bash
cd /Users/chenwenliang/code/CompliantFlow
src/venv/bin/python3 src/generate_pages.py
```

### When to Run

Run this script whenever you:
- ✅ Add a new doc type with `page_enabled: true`
- ✅ Change `page_number` for any doc type
- ✅ Change `name` or `icon` for a doc type
- ✅ Remove a doc type

### What It Does

1. **Reads** `DHF/config/project_config.yaml`
2. **Finds** all doc types with `page_enabled: true`
3. **Generates** page files in `src/pages/` named `{page_number}_{Name}.py`
4. **Removes** old page files that are no longer in config

### Example

**Configuration:**
```yaml
doc_types:
  - code: DEFECT
    name: "Defect"
    icon: "🐛"
    page_enabled: true
    page_number: 8
```

**Generated File:** `src/pages/8_Defect.py`

```python
"""Defect page - uses universal template."""
import streamlit as st
from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore
from pages.universal_page_template import render_item_management_page

# ... (auto-generated code)
```

## Benefits

✅ **Single Source of Truth** - Configuration drives everything  
✅ **No Manual Page Creation** - Just update config and run script  
✅ **Consistent** - All pages use same template  
✅ **Maintainable** - One place to update page logic

## Current Pages

Generated pages (as of last run):
- `4_Release.py` (RELEASE)
- `5_Customer_Requirement.py` (CRS)
- `6_System_Requirement.py` (SYS)
- `7_Software_Design_Specification.py` (SDS)
- `8_Defect.py` (DEFECT)
- `9_Change_Request.py` (CR)
