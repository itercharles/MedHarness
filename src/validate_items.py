#!/usr/bin/env python3
"""Validate all item files against project configuration schema."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from traceability.compliant_flow_core import CompliantFlowCore
from traceability.exceptions import ValidationError


def validate_all_items(dhf_path: Path) -> list[tuple[str, str]]:
    """
    Validate all item files against project config schema.
    
    Args:
        dhf_path: Path to DHF directory
        
    Returns:
        List of (file_path, error_message) tuples for validation errors
    """
    errors = []
    
    try:
        # Initialize core with validation enabled
        core = CompliantFlowCore(dhf_path)
        print(f"✅ All {len(core.get_all_items())} items validated successfully!")
        
    except ValidationError as e:
        # Validation error occurred during loading
        errors.append(("unknown", str(e)))
    except Exception as e:
        # Other error
        errors.append(("unknown", f"Unexpected error: {e}"))
    
    return errors


def main():
    """Run validation and report results."""
    # Find DHF directory (src/../DHF)
    script_dir = Path(__file__).parent
    dhf_path = script_dir.parent / 'DHF'
    
    if not dhf_path.exists():
        print(f"❌ DHF directory not found at {dhf_path}")
        sys.exit(1)
    
    print(f"Validating items in {dhf_path}...")
    print()
    
    errors = validate_all_items(dhf_path)
    
    if errors:
        print(f"❌ Found {len(errors)} validation error(s):")
        print()
        for file_path, error_msg in errors:
            print(f"  {error_msg}")
        print()
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
