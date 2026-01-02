"""Test Case Scanner - Extract test case metadata from Python test files.

Scans pytest test files and extracts test case information from docstrings,
allowing test code to be the single source of truth for automated tests.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional


class AutomatedTestScanner:
    """Scans Python test files to extract test case metadata."""
    
    def __init__(self, tests_dir: Path):
        """Initialize scanner with tests directory.
        
        Args:
            tests_dir: Path to tests directory
        """
        self.tests_dir = Path(tests_dir)
    
    def scan_all_tests(self) -> List[Dict]:
        """Scan all test files and extract test cases.
        
        Returns:
            List of test case dictionaries with metadata
        """
        test_cases = []
        
        for test_file in self.tests_dir.glob("test_*.py"):
            test_cases.extend(self._scan_file(test_file))
        
        return test_cases
    
    def _scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single test file.
        
        Args:
            file_path: Path to test file
        
        Returns:
            List of test cases from this file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            test_cases = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    test_case = self._extract_test_case(node, file_path)
                    if test_case:
                        test_cases.append(test_case)
            
            return test_cases
        
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            return []
    
    def _extract_test_case(self, node: ast.FunctionDef, file_path: Path) -> Optional[Dict]:
        """Extract test case metadata from function node.
        
        Args:
            node: AST function definition node
            file_path: Source file path
        
        Returns:
            Test case dictionary or None if not a valid test case
        """
        docstring = ast.get_docstring(node)
        if not docstring:
            return None
        
        # Extract test ID from function name or docstring
        test_id = self._extract_test_id(node.name, docstring)
        if not test_id:
            return None
        
        # Parse docstring for metadata
        metadata = self._parse_docstring(docstring)
        
        # Build test case object
        test_case = {
            'id': test_id,
            'test_type': 'automated',
            'title': metadata.get('title', ''),
            'content': metadata.get('content', ''),
            'verifies': metadata.get('links', []),  # Map @links to verifies for traceability
            'status': 'approved',  # Automated tests are approved when merged to main
            'prerequisites': metadata.get('prerequisites', ''),
            'steps': metadata.get('steps', []),
            'expected_result': metadata.get('expected_result', ''),
            '_source_file': str(file_path),
            '_function_name': node.name,
        }
        
        return test_case
    
    def _extract_test_id(self, function_name: str, docstring: str) -> Optional[str]:
        """Extract test case ID from function name or docstring.
        
        Supports formats:
        - test_TC_SYS_001_description
        - test_TC_CRS_009_001_description (with sub-number)
        - test_tc_sys_001_description
        - Docstring: "TC-SYS-001: Title"
        
        Args:
            function_name: Test function name
            docstring: Function docstring
        
        Returns:
            Test ID in format TC-XXX-YYY or TC-XXX-YYY-ZZZ or None
        """
        # Try function name first - support optional sub-number
        # Pattern: test_TC_XXX_123_456_description or test_TC_XXX_123_description
        pattern = r'test_(TC|tc)[_-]([A-Z]+|[a-z]+)[_-](\d+)(?:[_-](\d+))?'
        match = re.search(pattern, function_name)
        if match:
            prefix = match.group(1).upper()
            doc_type = match.group(2).upper()
            number = match.group(3)
            sub_number = match.group(4)
            
            if sub_number:
                return f"{prefix}-{doc_type}-{number}-{sub_number}"
            else:
                return f"{prefix}-{doc_type}-{number}"
        
        # Try docstring - support optional sub-number
        pattern = r'(TC-[A-Z]+-\d+(?:-\d+)?)'
        match = re.search(pattern, docstring)
        if match:
            return match.group(1)
        
        return None
    
    def _parse_docstring(self, docstring: str) -> Dict:
        """Parse test case metadata from docstring.
        
        Supports formats:
        - First line: "TC-XXX-YYY: Title"
        - @links: SYS-001, SYS-002
        - @prerequisites: Description
        - Steps: (numbered list)
        - Expected Result: Description
        
        Note: Status is not needed - automated tests are approved when merged.
        
        Args:
            docstring: Function docstring
        
        Returns:
            Dictionary of extracted metadata
        """
        lines = docstring.strip().split('\n')
        metadata = {
            'title': '',
            'content': '',
            'links': [],
            'prerequisites': '',
            'steps': [],
            'expected_result': '',
        }
        
        # Extract title from first line
        if lines:
            first_line = lines[0].strip()
            if ':' in first_line:
                metadata['title'] = first_line.split(':', 1)[1].strip()
            else:
                metadata['title'] = first_line
        
        # Parse metadata tags and sections
        current_section = None
        section_content = []
        
        for line in lines[1:]:
            line = line.strip()
            
            # Check for metadata tags
            if line.startswith('@links:'):
                links_str = line.split(':', 1)[1].strip()
                metadata['links'] = [l.strip() for l in links_str.split(',')]
                continue
            
            if line.startswith('@prerequisites:') or line.startswith('Prerequisites:'):
                metadata['prerequisites'] = line.split(':', 1)[1].strip()
                continue
            
            # Check for section headers
            if line.lower().startswith('steps:'):
                if current_section and section_content:
                    self._save_section(metadata, current_section, section_content)
                current_section = 'steps'
                section_content = []
                continue
            
            if line.lower().startswith('expected result:') or line.lower().startswith('expected:'):
                if current_section and section_content:
                    self._save_section(metadata, current_section, section_content)
                current_section = 'expected_result'
                section_content = []
                # Get content after colon
                if ':' in line:
                    section_content.append(line.split(':', 1)[1].strip())
                continue
            
            # Add to current section or content
            if line:
                if current_section:
                    # Remove leading numbers/bullets for steps
                    cleaned = re.sub(r'^\d+\.\s*|\-\s*', '', line)
                    if cleaned:
                        section_content.append(cleaned)
                else:
                    # General content
                    if metadata['content']:
                        metadata['content'] += '\n' + line
                    else:
                        metadata['content'] = line
        
        # Save last section
        if current_section and section_content:
            self._save_section(metadata, current_section, section_content)
        
        return metadata
    
    def _save_section(self, metadata: Dict, section: str, content: List[str]):
        """Save section content to metadata.
        
        Args:
            metadata: Metadata dictionary
            section: Section name
            content: Section content lines
        """
        if section == 'steps':
            metadata['steps'] = content
        elif section == 'expected_result':
            metadata['expected_result'] = ' '.join(content)
