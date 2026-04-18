# compliantflow-dhf

Design History File for [CompliantFlow](https://github.com/itercharles/CompliantFlow).

This repository serves two purposes:

1. **Regulatory documentation** — CompliantFlow's own DHF, maintained under IEC 62304, ISO 14971, and IEC 82304-1.
2. **Reference implementation** — A working example of how any project uses CompliantFlow. Clone this as a starting template for your own DHF.

## Structure

```
DHF/          # Design History File (items, config, documents, test-results)
governance/   # Compliance policy files (IEC_62304.yaml, ISO_14971.yaml, ...)
```

## Usage with CompliantFlow

```bash
# Clone the tool
git clone https://github.com/itercharles/CompliantFlow
cd CompliantFlow

# Clone this DHF alongside
git clone https://github.com/itercharles/compliantflow-dhf

# Set PYTHONPATH so the CLI can find LocalDHFAdapter
export PYTHONPATH=.:compliantflow-dhf/DHF

# Run compliance checks
python -m compliantflow --dhf compliantflow-dhf/DHF validate compliance IEC_62304 \
  --governance-dir compliantflow-dhf/governance
```

## DHF utilities

The `DHF/utils/` package is the DHF system's own API (item CRUD, lifecycle transitions,
schema validation). It is not part of the CompliantFlow tool itself.

```bash
# Create a new item
PYTHONPATH=.:DHF python -m utils item create --type SRS --title "My requirement"

# Run DHF utility tests
PYTHONPATH=.:DHF pytest DHF/utils/tests/
```
