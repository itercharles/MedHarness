#!/usr/bin/env python3
"""Validate all item YAML files against the project configuration schema.

Usage:
    python src/validate_items.py [DHF_PATH]

If DHF_PATH is omitted the script looks for a 'DHF' directory next to 'src/'.
Exit code 0 means all items are valid; non-zero means errors were found.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from traceability.compliant_flow_core import CompliantFlowCore
from traceability.exceptions import ValidationError


def validate_all_items(dhf_path: Path) -> list[tuple[str, str]]:
    """
    Load every item in *dhf_path* and collect validation errors.

    Returns:
        List of (filename, error_message) tuples; empty list means success.
    """
    errors = []
    try:
        core = CompliantFlowCore(dhf_path)
        count = len(core.get_all_items())
        print(f"✅  All {count} items validated successfully.")
    except ValidationError as e:
        errors.append(("", str(e)))
    except Exception as e:
        errors.append(("", f"Unexpected error: {e}"))
    return errors


def main() -> None:
    if len(sys.argv) > 1:
        dhf_path = Path(sys.argv[1])
    else:
        dhf_path = Path(__file__).parent.parent / "DHF"

    if not dhf_path.exists():
        print(f"❌  DHF directory not found: {dhf_path}")
        sys.exit(1)

    print(f"Validating items in {dhf_path} …\n")
    errors = validate_all_items(dhf_path)

    if errors:
        print(f"❌  {len(errors)} validation error(s):\n")
        for _, msg in errors:
            print(f"  {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
