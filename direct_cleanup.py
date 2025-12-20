#!/usr/bin/env python3
"""
Direct YAML cleanup script.
Reads YAML files, removes duplicate fields, fixes serialization, and rewrites.
"""

from pathlib import Path
import yaml
import re

def clean_yaml_file(file_path: Path) -> bool:
    """
    Clean a single YAML file.
    Returns True if file was modified, False otherwise.
    """
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse YAML
        data = yaml.safe_load(content)
        
        if not data or not isinstance(data, dict):
            return False
        
        modified = False
        
        # Remove duplicate fields
        if 'uid' in data and 'id' in data:
            del data['uid']
            modified = True
        
        if 'text' in data and 'content' in data:
            del data['text']
            modified = True
        
        # Fix verification_status if it's not a simple string
        if 'verification_status' in data:
            vs = data['verification_status']
            # If it's not already a string, try to extract the value
            if not isinstance(vs, str):
                # Try to get the value from various formats
                if isinstance(vs, list) and len(vs) > 0:
                    data['verification_status'] = vs[0]
                    modified = True
                elif hasattr(vs, 'value'):
                    data['verification_status'] = vs.value
                    modified = True
                else:
                    # Default to PENDING if we can't determine
                    data['verification_status'] = 'PENDING'
                    modified = True
        
        # If modified, rewrite the file
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
        print(f"✗ Error cleaning {file_path.name}: {e}")
        return False

def main():
    # Find all YAML files in items directory
    dhf_root = Path(__file__).parent / "DHF"
    items_dir = dhf_root / "items"
    
    if not items_dir.exists():
        print(f"Error: {items_dir} does not exist")
        return
    
    # Find all YAML files
    yaml_files = list(items_dir.rglob("*.yaml"))
    print(f"Found {len(yaml_files)} YAML files")
    
    cleaned = 0
    unchanged = 0
    errors = 0
    
    for yaml_file in yaml_files:
        try:
            if clean_yaml_file(yaml_file):
                print(f"✓ Cleaned {yaml_file.relative_to(items_dir)}")
                cleaned += 1
            else:
                unchanged += 1
        except Exception as e:
            print(f"✗ Error with {yaml_file.name}: {e}")
            errors += 1
    
    print(f"\n{'='*60}")
    print(f"Cleanup complete!")
    print(f"  Cleaned: {cleaned}")
    print(f"  Unchanged: {unchanged}")
    print(f"  Errors: {errors}")
    print(f"{'='*60}")
    
    # Report on wrong directories
    wrong_dirs = ['TC-CRS', 'TC-SDS', 'TC-SYS', 'RCM', 'REL', 'RISK']
    for dirname in wrong_dirs:
        dir_path = items_dir / dirname
        if dir_path.exists():
            files = list(dir_path.glob("*.yaml"))
            if files:
                print(f"\n⚠️  {len(files)} files in wrong directory '{dirname}/':")
                for f in files[:5]:  # Show first 5
                    print(f"  - {f.name}")
                if len(files) > 5:
                    print(f"  ... and {len(files) - 5} more")

if __name__ == "__main__":
    main()
