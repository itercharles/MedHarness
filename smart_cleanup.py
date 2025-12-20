#!/usr/bin/env python3
"""
Smart YAML cleanup script.
Reads project config to determine valid properties for each doc type.
Removes any fields not in the allowed list.
"""

from pathlib import Path
import yaml
import sys

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Core fields that should always be kept
CORE_FIELDS = {
    'id', 'content', 'title', 'links', 'status', 
    'verification_status', 'manual_verifications'
}

def load_project_config(dhf_root: Path):
    """Load project configuration."""
    config_path = dhf_root / "config" / "project_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_allowed_fields_for_prefix(prefix: str, config: dict) -> set:
    """Get allowed fields for a given prefix."""
    # Find matching doc type
    for doc_type in config.get('doc_types', []):
        if doc_type.get('prefix') == prefix:
            # Start with core fields
            allowed = CORE_FIELDS.copy()
            
            # Add configured properties
            if doc_type.get('properties'):
                allowed.update(doc_type['properties'])
            
            # Add lifecycle metadata fields (e.g., approved_by, approved_date)
            lifecycle = doc_type.get('lifecycle', {})
            for state in lifecycle.get('states', []):
                state_id = state['id']
                allowed.add(f"{state_id}_by")
                allowed.add(f"{state_id}_date")
            
            return allowed
    
    # If no match found, return core fields only
    return CORE_FIELDS

def extract_prefix(item_id: str) -> str:
    """Extract prefix from item ID (e.g., 'SYS-001' -> 'SYS-')."""
    if '-' in item_id:
        parts = item_id.rsplit('-', 1)
        if len(parts) == 2:
            return parts[0] + '-'
    return ''

def clean_yaml_file(file_path: Path, config: dict) -> bool:
    """
    Clean a single YAML file based on project config.
    Returns True if file was modified.
    """
    try:
        # Try safe load first
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.constructor.ConstructorError:
            # If safe load fails (Python objects), use unsafe load
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.unsafe_load(f)
        
        if not data or not isinstance(data, dict):
            return False
        
        # Get item ID and prefix
        item_id = data.get('id') or data.get('uid')
        if not item_id:
            print(f"⚠️  No ID found in {file_path.name}")
            return False
        
        prefix = extract_prefix(item_id)
        if not prefix:
            print(f"⚠️  Could not extract prefix from {item_id}")
            return False
        
        # Get allowed fields for this doc type
        allowed_fields = get_allowed_fields_for_prefix(prefix, config)
        
        # Remove fields not in allowed list
        fields_to_remove = []
        for field in list(data.keys()):
            if field not in allowed_fields:
                fields_to_remove.append(field)
        
        if not fields_to_remove:
            return False
        
        # Remove the fields
        for field in fields_to_remove:
            del data[field]
        
        # Ensure we have 'id' and 'content' (not uid/text)
        if 'uid' in data and 'id' not in data:
            data['id'] = data['uid']
            del data['uid']
        elif 'uid' in data:
            del data['uid']
        
        if 'text' in data and 'content' not in data:
            data['content'] = data['text']
            del data['text']
        elif 'text' in data:
            del data['text']
        
        # Fix verification_status if needed
        if 'verification_status' in data:
            vs = data['verification_status']
            if not isinstance(vs, str):
                if isinstance(vs, list) and len(vs) > 0:
                    data['verification_status'] = str(vs[0])
                elif hasattr(vs, 'value'):
                    data['verification_status'] = vs.value
                else:
                    data['verification_status'] = 'PENDING'
        
        # Rewrite file
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
        
        return True
        
    except Exception as e:
        print(f"✗ Error cleaning {file_path.name}: {e}")
        return False

def main():
    dhf_root = Path(__file__).parent / "DHF"
    items_dir = dhf_root / "items"
    
    # Load project config
    print("Loading project configuration...")
    config = load_project_config(dhf_root)
    print(f"Found {len(config.get('doc_types', []))} document types")
    
    # Find all YAML files
    yaml_files = list(items_dir.rglob("*.yaml"))
    print(f"\nFound {len(yaml_files)} YAML files\n")
    
    cleaned = 0
    unchanged = 0
    
    for yaml_file in yaml_files:
        if clean_yaml_file(yaml_file, config):
            print(f"✓ Cleaned {yaml_file.relative_to(items_dir)}")
            cleaned += 1
        else:
            unchanged += 1
    
    print(f"\n{'='*60}")
    print(f"Cleanup complete!")
    print(f"  Cleaned: {cleaned}")
    print(f"  Unchanged: {unchanged}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
