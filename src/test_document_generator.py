"""Test document generator functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from traceability.compliant_flow_core import CompliantFlowCore
from traceability.document_generator import DocumentGenerator

def test_document_generator():
    """Test document generation."""
    print("Testing Document Generator...")
    
    # Initialize core
    dhf_path = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_path)
    
    # Initialize document generator
    template_dir = dhf_path / "templates"
    generator = DocumentGenerator(core, template_dir)
    
    print(f"✓ Document generator initialized")
    print(f"  Template dir: {template_dir}")
    
    # Test requirements specification generation
    print("\n1. Testing Requirements Specification Generation...")
    try:
        pdf_path = generator.generate_requirements_spec('SYS')
        print(f"✓ Generated SYS specification: {pdf_path}")
        print(f"  File exists: {pdf_path.exists()}")
        print(f"  File size: {pdf_path.stat().st_size} bytes")
    except Exception as e:
        print(f"✗ Error generating SYS spec: {e}")
    
    # Test traceability matrix generation
    print("\n2. Testing Traceability Matrix Generation...")
    try:
        pdf_path = generator.generate_traceability_matrix()
        print(f"✓ Generated traceability matrix: {pdf_path}")
        print(f"  File exists: {pdf_path.exists()}")
        print(f"  File size: {pdf_path.stat().st_size} bytes")
    except Exception as e:
        print(f"✗ Error generating matrix: {e}")
    
    print("\n✓ All tests completed!")

if __name__ == "__main__":
    test_document_generator()
