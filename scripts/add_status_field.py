#!/usr/bin/env python3
"""Add status field to existing requirement items."""

import yaml
from pathlib import Path

# Directories to process
dirs_to_process = [
    "DHF/items/01_req_crs",
    "DHF/items/02_req_sys",
    "DHF/items/04_req_sds",
]

def add_status_to_file(filepath: Path):
    """Add status: draft to a YAML file if it doesn't have status."""
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    
    # Check if status already exists
    if 'status' in data:
        print(f"  ✓ {filepath.name} already has status: {data['status']}")
        return False
    
    # Add status
    data['status'] = 'draft'
    
    # Write back
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    print(f"  ✅ Added status to {filepath.name}")
    return True

def main():
    total_updated = 0
    
    for dir_path in dirs_to_process:
        dir_full = Path(dir_path)
        if not dir_full.exists():
            print(f"⚠️  Directory not found: {dir_path}")
            continue
        
        print(f"\n📁 Processing {dir_path}...")
        
        yaml_files = list(dir_full.glob("*.yaml"))
        for filepath in yaml_files:
            if add_status_to_file(filepath):
                total_updated += 1
    
    print(f"\n✅ Done! Updated {total_updated} files")

if __name__ == "__main__":
    main()
