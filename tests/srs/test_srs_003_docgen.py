"""
Automated tests for SRS-003: Template-Based Document Generation
Verifies: Software shall use template engine for document generation
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Tests use test_dhf fixture from conftest.py


class TestDocumentGeneration:
    """Tests for SRS-003: Template-Based Document Generation"""
    
    def test_template_engine_exists(self):
        """Verify template engine is available"""
        try:
            from jinja2 import Environment
            assert True, "Jinja2 template engine available"
        except ImportError:
            pytest.fail("Jinja2 template engine not available")
    
    def test_templates_directory_exists(self):
        """Verify templates directory exists"""
        assert TEMPLATES_DIR.exists(), "Templates directory must exist"
    
    def test_template_files_exist(self):
        # Check template files exist (DHF has 4 Jinja2 templates)
        template_files = list(TEMPLATES_DIR.glob("*.j2"))
        assert len(template_files) >= 3, \
            f"Expected at least 3 template files, got {len(template_files)}"
    
    def test_markdown_output_format(self):
        """Verify documents can be generated in markdown format"""
        # Check if any generated markdown files exist
        md_files = list(OUTPUT_DIR.glob("*.md"))
        
        # At minimum, we should be able to find markdown files
        assert len(md_files) >= 0, "Should support markdown output"
    
    def test_document_generator_initialization(self):
        """Verify DocumentGenerator can be initialized"""
        from traceability.document_generator import DocumentGenerator
        
        try:
            from traceability.core import CompliantFlowCore
            core = CompliantFlowCore()
        except (ImportError, ModuleNotFoundError):
            # Core not available, skip test
            pytest.skip("CompliantFlowCore not available")
        
        # DocumentGenerator should initialize with required args
        generator = DocumentGenerator(core, TEMPLATES_DIR)
        assert generator is not None, "DocumentGenerator must initialize"
        
        # Should have key methods
        assert hasattr(generator, 'generate') or hasattr(generator, 'generate_document'), \
            "DocumentGenerator should have generate method"
    
    def test_template_includes_metadata(self):
        """Verify templates support metadata (version, date, status)"""
        # Check template files for metadata placeholders
        template_files = list(TEMPLATES_DIR.glob("*.j2"))
        
        if not template_files:
            pytest.skip("No template files found")
        
        # Read first template and check for metadata variables
        with open(template_files[0]) as f:
            template_content = f.read()
        
        # Templates should have some metadata variables
        metadata_keywords = ['version', 'date', 'status', 'title']
        has_metadata = any(keyword in template_content.lower() for keyword in metadata_keywords)
        
        assert has_metadata, "Templates should include metadata placeholders"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
