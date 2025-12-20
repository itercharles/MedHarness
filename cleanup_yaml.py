#!/usr/bin/env python3
"""
Clean up YAML files by reloading and resaving all items.
This will fix:
- Duplicate fields (id/uid, content/text)
- Python object serialization in verification_status
- Move files from 'other' directory to correct locations
"""

from pathlib import Path
import sys

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from traceability.compliant_flow_core import CompliantFlowCore

def main():
    # Initialize core
    dhf_root = Path(__file__).parent / "DHF"
    print(f"Loading CompliantFlow from {dhf_root}")
    core = CompliantFlowCore(dhf_root)
    
    # Get all items
    all_items = core.get_all_items()
    print(f"\nFound {len(all_items)} items to clean")
    
    # Track statistics
    cleaned = 0
    errors = 0
    
    # Reload and resave each item
    for item_dict in all_items:
        item_id = item_dict.get('id')
        try:
            # Get the item (this loads it as an Item object)
            item = core.get_item(item_id)
            if not item:
                print(f"⚠️  Could not load {item_id}")
                errors += 1
                continue
            
            # Resave it (this will use the new serialization logic)
            core.update_item(item_id, item_dict)
            cleaned += 1
            print(f"✓ Cleaned {item_id}")
            
        except Exception as e:
            print(f"✗ Error cleaning {item_id}: {e}")
            errors += 1
    
    print(f"\n{'='*60}")
    print(f"Cleanup complete!")
    print(f"  Cleaned: {cleaned}")
    print(f"  Errors: {errors}")
    print(f"{'='*60}")
    
    # Check for files in 'other' directory
    other_dir = dhf_root / "items" / "other"
    if other_dir.exists():
        other_files = list(other_dir.glob("*.yaml"))
        if other_files:
            print(f"\n⚠️  Warning: {len(other_files)} files still in 'other' directory:")
            for f in other_files:
                print(f"  - {f.name}")
            print("\nThese files may need manual review or deletion.")

if __name__ == "__main__":
    main()
