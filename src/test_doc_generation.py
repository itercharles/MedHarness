"""Manual test script for document generation functionality."""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore
from traceability.document_generator import DocumentGenerator


def test_markdown_generation():
    """Test markdown specification generation."""
    print("=" * 60)
    print("Testing Markdown Document Generation")
    print("=" * 60)
    
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Initialize document generator
    template_dir = dhf_root / "templates"
    generator = DocumentGenerator(core, template_dir)
    
    print(f"\n✓ Initialized DocumentGenerator")
    print(f"  Template dir: {template_dir}")
    print(f"  DHF root: {dhf_root}")
    
    # Test 1: Generate CRS markdown specification
    print("\n" + "-" * 60)
    print("Test 1: Generate CRS Specification (Markdown)")
    print("-" * 60)
    try:
        markdown_content, output_path = generator.generate_markdown_spec('CRS')
        print(f"✓ Generated CRS specification")
        print(f"  Output path: {output_path}")
        print(f"  File exists: {output_path.exists()}")
        print(f"  File size: {output_path.stat().st_size} bytes")
        print(f"\n  Preview (first 500 chars):")
        print(f"  {markdown_content[:500]}...")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Generate TC-CRS test specification
    print("\n" + "-" * 60)
    print("Test 2: Generate TC-CRS Test Specification (Markdown)")
    print("-" * 60)
    try:
        markdown_content, output_path = generator.generate_markdown_spec('TC-CRS')
        print(f"✓ Generated TC-CRS test specification")
        print(f"  Output path: {output_path}")
        print(f"  File exists: {output_path.exists()}")
        print(f"  File size: {output_path.stat().st_size} bytes")
        print(f"\n  Preview (first 500 chars):")
        print(f"  {markdown_content[:500]}...")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Export static document to PDF
    print("\n" + "-" * 60)
    print("Test 3: Export Static CRS Document to PDF")
    print("-" * 60)
    try:
        pdf_path = generator.export_static_doc_to_pdf('CRS')
        print(f"✓ Generated PDF from static document")
        print(f"  PDF path: {pdf_path}")
        print(f"  File exists: {pdf_path.exists()}")
        print(f"  File size: {pdf_path.stat().st_size} bytes")
    except FileNotFoundError as e:
        print(f"⚠ Static document not found (expected on first run)")
        print(f"  Run Test 1 first to generate the static file")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Verify all configured doc types
    print("\n" + "-" * 60)
    print("Test 4: Verify All Configured Document Types")
    print("-" * 60)
    
    import yaml
    config_path = dhf_root / 'config' / 'project_config.yaml'
    with open(config_path, 'r') as f:
        project_config = yaml.safe_load(f)
    
    doc_specs = project_config.get('document_specifications', {})
    print(f"Found {len(doc_specs)} configured document types:")
    for doc_type, spec in doc_specs.items():
        print(f"  - {doc_type}: {spec['template']} → {spec['output']}")
    
    print("\n" + "=" * 60)
    print("All Tests Completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_markdown_generation()
