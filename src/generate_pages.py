#!/usr/bin/env python3
"""
Page Generator Script

Automatically generates Streamlit page files from project_config.yaml.
Run this script whenever you add/modify doc types in the configuration.

Usage:
    python generate_pages.py
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load project configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def generate_page_content(doc_type: Dict[str, Any]) -> str:
    """Generate page file content for a doc type."""
    code = doc_type['code']
    name = doc_type.get('name', code)
    icon = doc_type.get('icon', '📄')
    
    return f'''"""{name} page - uses universal template."""

import streamlit as st
from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore
from pages.universal_page_template import render_item_management_page

# Initialize core
dhf_root = Path(__file__).parent.parent.parent / "DHF"
core = CompliantFlowCore(dhf_root)

# Get doc type config
doc_type = None
for dt in core.config.doc_types:
    if dt.code == '{code}':
        doc_type = dt
        break

if doc_type:
    # Convert to dict for template
    config_dict = {{
        'code': doc_type.code,
        'name': doc_type.name,
        'prefix': doc_type.prefix,
        'icon': getattr(doc_type, 'icon', '{icon}'),
        'lifecycle': getattr(doc_type, 'lifecycle', {{}}),
        'page_enabled': getattr(doc_type, 'page_enabled', True),
        'has_verification': getattr(doc_type, 'has_verification', False),
        'properties': doc_type.properties if hasattr(doc_type, 'properties') else [],
    }}
    
    # Render page
    render_item_management_page(config_dict, core)
else:
    st.error("{code} doc type not found in project configuration")
'''


def generate_pages(config_path: Path, pages_dir: Path):
    """Generate all page files from configuration."""
    # Load configuration
    config = load_config(config_path)
    doc_types = config.get('doc_types', [])
    
    # Filter doc types that have pages enabled
    page_doc_types = [
        dt for dt in doc_types 
        if dt.get('page_enabled', False) and dt.get('page_number')
    ]
    
    # Sort by page number
    page_doc_types.sort(key=lambda dt: dt.get('page_number', 999))
    
    print(f"🔍 Found {len(page_doc_types)} doc types with pages enabled")
    
    # Generate each page file
    generated_files = []
    for doc_type in page_doc_types:
        page_number = doc_type['page_number']
        name = doc_type.get('name', doc_type['code'])
        code = doc_type['code']
        
        # Create filename: {number}_{Name}.py
        filename = f"{page_number}_{name.replace(' ', '_')}.py"
        filepath = pages_dir / filename
        
        # Generate content
        content = generate_page_content(doc_type)
        
        # Write file
        with open(filepath, 'w') as f:
            f.write(content)
        
        generated_files.append(filename)
        print(f"  ✅ Generated: {filename} ({code})")
    
    # Clean up old page files (except universal_page_template.py)
    existing_files = list(pages_dir.glob('[0-9]*.py'))
    for existing_file in existing_files:
        if existing_file.name not in generated_files:
            existing_file.unlink()
            print(f"  🗑️  Removed: {existing_file.name}")
    
    print(f"\n✨ Page generation complete! Generated {len(generated_files)} pages.")
    print(f"📁 Pages directory: {pages_dir}")
    print("\n📋 Generated pages:")
    for filename in generated_files:
        print(f"   - {filename}")


def main():
    """Main entry point."""
    # Determine paths
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "DHF" / "config" / "project_config.yaml"
    pages_dir = script_dir / "pages"
    
    print("=" * 60)
    print("🚀 Streamlit Page Generator")
    print("=" * 60)
    print(f"📄 Config: {config_path}")
    print(f"📁 Pages:  {pages_dir}")
    print()
    
    if not config_path.exists():
        print(f"❌ Error: Configuration file not found at {config_path}")
        return 1
    
    if not pages_dir.exists():
        print(f"❌ Error: Pages directory not found at {pages_dir}")
        return 1
    
    # Generate pages
    generate_pages(config_path, pages_dir)
    
    print("\n" + "=" * 60)
    print("✅ Done! Restart Streamlit to see changes.")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
