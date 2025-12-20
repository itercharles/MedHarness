#!/usr/bin/env python3
"""
Fix TC-SDS data quality issues:
1. Add missing 'content' field (copy from 'title' if missing)
2. Fix 'not_verified' to 'PENDING'
3. Fix misplaced 'status: PASS' to 'verification_status: PASS'
"""

from pathlib import Path
import yaml

def fix_tc_sds_file(file_path: Path) -> bool:
    """Fix a single TC-SDS YAML file. Returns True if modified."""
    try:
        # Load with unsafe_load to handle any Python objects
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.unsafe_load(f)
        
        if not data or not isinstance(data, dict):
            return False
        
        modified = False
        
        # Fix 1: Add missing 'content' field
        if 'content' not in data:
            # Use title as content if available
            if 'title' in data:
                data['content'] = f"Test case: {data['title']}"
                modified = True
                print(f"  Added content field to {file_path.name}")
            else:
                data['content'] = "Test case content"
                modified = True
                print(f"  Added default content to {file_path.name}")
        
        # Fix 2: Change 'not_verified' to 'PENDING'
        if data.get('verification_status') == 'not_verified':
            data['verification_status'] = 'PENDING'
            modified = True
            print(f"  Fixed verification_status in {file_path.name}")
        
        # Fix 3: Move misplaced 'status: PASS' to 'verification_status'
        if data.get('status') == 'PASS':
            data['verification_status'] = 'PASS'
            data['status'] = 'draft'  # Set proper lifecycle status
            modified = True
            print(f"  Fixed misplaced status in {file_path.name}")
        
        # Save if modified
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False
                )
            return True
        
        return False
        
    except Exception as e:
        print(f"✗ Error fixing {file_path.name}: {e}")
        return False

def main():
    # Find all TC-SDS files
    tc_sds_dir = Path(__file__).parent / "DHF" / "items" / "07_tc_sds"
    
    if not tc_sds_dir.exists():
        print(f"Error: {tc_sds_dir} does not exist")
        return
    
    yaml_files = list(tc_sds_dir.glob("*.yaml"))
    print(f"Found {len(yaml_files)} TC-SDS files\n")
    
    fixed = 0
    unchanged = 0
    
    for yaml_file in yaml_files:
        if fix_tc_sds_file(yaml_file):
            fixed += 1
        else:
            unchanged += 1
    
    print(f"\n{'='*60}")
    print(f"TC-SDS Fix Complete!")
    print(f"  Fixed: {fixed}")
    print(f"  Unchanged: {unchanged}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
