"""Document generation engine for CompliantFlow."""

from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown
from weasyprint import HTML, CSS


class DocumentGenerator:
    """Generate regulatory documents from templates."""
    
    def __init__(self, core, template_dir: Path):
        """
        Initialize document generator.
        
        Args:
            core: CompliantFlowCore instance
            template_dir: Path to templates directory
        """
        self.core = core
        self.template_dir = template_dir
        
        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register custom filters
        self._register_filters()
    
    def _register_filters(self):
        """Register custom Jinja2 filters."""
        self.jinja_env.filters['status_badge'] = self._status_badge
        self.jinja_env.filters['format_date'] = self._format_date
        
    def _status_badge(self, status: str) -> str:
        """Format status as text badge (no emojis for PDF)."""
        # Return uppercase text-only status for professional documents
        return status.upper() if status else 'UNKNOWN'
    
    def _format_date(self, date_str) -> str:
        """Format ISO date or date object."""
        if not date_str:
            return 'N/A'
        # Handle date objects
        if hasattr(date_str, 'isoformat'):
            return date_str.isoformat()[:10]
        # Handle strings
        return str(date_str)[:10]
    
    def generate_requirements_spec(self, doc_type_code: str) -> Path:
        """
        Generate requirements specification PDF document.
        
        Args:
            doc_type_code: Document type code (e.g., 'CRS', 'SYS', 'SDS')
            
        Returns:
            Path to generated PDF file
        """
        # Get doc type config
        config = self.core.config.get_doc_type(doc_type_code)
        if not config:
            raise ValueError(f"Unknown document type: {doc_type_code}")
        
        # Gather all items of this type
        all_items = self.core.get_all_items()
        items = [
            item for item in all_items 
            if item['id'].startswith(doc_type_code)
        ]
        
        # Sort by ID
        items.sort(key=lambda x: x['id'])
        
        # Prepare template data
        data = {
            'doc_type_code': doc_type_code,
            'doc_type_name': config.name,
            'project_name': 'CompliantFlow Project',
            'version': '1.0',
            'generation_date': datetime.now().isoformat()[:10],
            'status': 'Draft',
            'items': items
        }
        
        # Render template
        template = self.jinja_env.get_template('requirements_specification.md.j2')
        markdown_content = template.render(**data)
        
        # Export to PDF
        return self._export_pdf(markdown_content, f"{doc_type_code}_Specification")
    
    def generate_markdown_spec(self, doc_type_code: str) -> Tuple[str, Path]:
        """
        Generate markdown specification and save to static file location.
        
        Args:
            doc_type_code: Document type code (e.g., 'CRS', 'SYS', 'TC-CRS')
            
        Returns:
            Tuple of (markdown_content, output_path)
        """
        # Load document specification config
        config_path = self.core.repo_root / 'config' / 'project_config.yaml'
        import yaml
        with open(config_path, 'r') as f:
            project_config = yaml.safe_load(f)
        
        doc_specs = project_config.get('document_specifications', {})
        if doc_type_code not in doc_specs:
            raise ValueError(f"No document specification configured for {doc_type_code}")
        
        spec_config = doc_specs[doc_type_code]
        template_name = spec_config['template']
        output_rel_path = spec_config['output']
        output_path = self.core.repo_root.parent / output_rel_path
        
        # Get doc type config
        doc_type_config = self.core.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            raise ValueError(f"Unknown document type: {doc_type_code}")
        
        # Read existing version if file exists
        current_version = "1.0"
        if output_path.exists():
            existing_content = output_path.read_text()
            # Extract version from table format: | **Version** | 1.2 |
            import re
            version_match = re.search(r'\|\s*\*\*Version\*\*\s*\|\s*(\d+)\.(\d+)\s*\|', existing_content)
            if version_match:
                major = int(version_match.group(1))
                minor = int(version_match.group(2))
                # Increment minor version
                current_version = f"{major}.{minor + 1}"
        
        # Gather all items of this type
        all_items = self.core.get_all_items()
        items = [
            item for item in all_items 
            if item['id'].startswith(doc_type_code)
        ]
        
        # Sort by ID
        items.sort(key=lambda x: x['id'])
        
        # Prepare template data
        data = {
            'doc_type_code': doc_type_code,
            'doc_type_name': spec_config.get('doc_type_name', doc_type_config.name),
            'test_type': spec_config.get('test_type', ''),
            'project_name': 'CompliantFlow Project',
            'version': current_version,
            'generation_date': datetime.now().isoformat()[:10],
            'status': 'Draft',  # Always reset to Draft on regeneration
            'items': items,
            'directory': doc_type_config.directory if hasattr(doc_type_config, 'directory') else ''
        }
        
        # Render template
        template = self.jinja_env.get_template(template_name)
        markdown_content = template.render(**data)
        
        # Write to output file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_content)
        
        return markdown_content, output_path
    
    def export_static_doc_to_pdf(self, doc_type_code: str) -> Path:
        """
        Export existing static markdown document to PDF.
        
        Args:
            doc_type_code: Document type code (e.g., 'CRS', 'SYS', 'TC-CRS')
            
        Returns:
            Path to generated PDF file
        """
        # Load document specification config
        config_path = self.core.repo_root / 'config' / 'project_config.yaml'
        import yaml
        with open(config_path, 'r') as f:
            project_config = yaml.safe_load(f)
        
        doc_specs = project_config.get('document_specifications', {})
        if doc_type_code not in doc_specs:
            raise ValueError(f"No document specification configured for {doc_type_code}")
        
        spec_config = doc_specs[doc_type_code]
        static_file_path = self.core.repo_root.parent / spec_config['output']
        
        if not static_file_path.exists():
            raise FileNotFoundError(f"Static document not found: {static_file_path}")
        
        # Read static markdown file
        markdown_content = static_file_path.read_text()
        
        # Export to PDF
        filename = f"{doc_type_code}_Specification_{datetime.now().strftime('%Y%m%d')}"
        return self._export_pdf(markdown_content, filename)
    
    def generate_traceability_matrix(self) -> Path:
        """
        Generate traceability matrix PDF.
        
        Returns:
            Path to generated PDF file
        """
        # Build traceability chains
        chains = self._build_traceability_chains()
        coverage = self._calculate_coverage()
        orphans = self._find_orphans()
        
        data = {
            'generation_date': datetime.now().isoformat()[:10],
            'project_name': 'CompliantFlow Project',
            'traceability_chains': chains,
            'coverage': coverage,
            'orphans': orphans
        }
        
        template = self.jinja_env.get_template('traceability_matrix.md.j2')
        markdown_content = template.render(**data)
        
        return self._export_pdf(markdown_content, "Traceability_Matrix")
    
    def _build_traceability_chains(self) -> List[Dict[str, Any]]:
        """Build CRS → SYS → SDS → Test chains."""
        chains = []
        all_items = self.core.get_all_items()
        
        # Get all CRS items
        crs_items = [item for item in all_items if item['id'].startswith('CRS')]
        
        for crs in crs_items:
            # Find linked SYS items
            sys_items = [item for item in all_items 
                        if item['id'].startswith('SYS') and crs['id'] in item.get('links', [])]
            
            if not sys_items:
                # CRS with no SYS
                chains.append({
                    'crs_id': crs['id'],
                    'crs_title': crs.get('title', 'N/A'),
                    'sys_id': None,
                    'sys_title': None,
                    'sds_id': None,
                    'test_id': None,
                    'status': crs.get('status', 'draft')
                })
            else:
                for sys in sys_items:
                    # Find linked SDS items
                    sds_items = [item for item in all_items 
                                if item['id'].startswith('SDS') and sys['id'] in item.get('links', [])]
                    
                    # Find test items
                    test_items = [item for item in all_items 
                                 if item['id'].startswith('TC-') and sys['id'] in item.get('links', [])]
                    
                    chains.append({
                        'crs_id': crs['id'],
                        'crs_title': crs.get('title', 'N/A'),
                        'sys_id': sys['id'],
                        'sys_title': sys.get('title', 'N/A'),
                        'sds_id': sds_items[0]['id'] if sds_items else None,
                        'test_id': test_items[0]['id'] if test_items else None,
                        'status': sys.get('status', 'draft')
                    })
        
        return chains
    
    def _calculate_coverage(self) -> Dict[str, Any]:
        """Calculate traceability coverage metrics."""
        all_items = self.core.get_all_items()
        
        crs_items = [item for item in all_items if item['id'].startswith('CRS')]
        sys_items = [item for item in all_items if item['id'].startswith('SYS')]
        sds_items = [item for item in all_items if item['id'].startswith('SDS')]
        test_items = [item for item in all_items if item['id'].startswith('TC-')]
        
        # CRS to SYS coverage
        crs_with_sys = sum(1 for crs in crs_items 
                          if any(sys for sys in sys_items if crs['id'] in sys.get('links', [])))
        crs_to_sys = int((crs_with_sys / len(crs_items) * 100)) if crs_items else 0
        
        # SYS to SDS coverage
        sys_with_sds = sum(1 for sys in sys_items 
                          if any(sds for sds in sds_items if sys['id'] in sds.get('links', [])))
        sys_to_sds = int((sys_with_sds / len(sys_items) * 100)) if sys_items else 0
        
        # Requirements to test coverage
        req_items = crs_items + sys_items + sds_items
        req_with_test = sum(1 for req in req_items 
                           if any(test for test in test_items if req['id'] in test.get('links', [])))
        req_to_test = int((req_with_test / len(req_items) * 100)) if req_items else 0
        
        return {
            'crs_to_sys': crs_to_sys,
            'crs_with_sys': crs_with_sys,
            'total_crs': len(crs_items),
            'sys_to_sds': sys_to_sds,
            'sys_with_sds': sys_with_sds,
            'total_sys': len(sys_items),
            'req_to_test': req_to_test,
            'req_with_test': req_with_test,
            'total_req': len(req_items)
        }
    
    def _find_orphans(self) -> Dict[str, List[str]]:
        """Find orphaned items."""
        all_items = self.core.get_all_items()
        
        crs_items = [item for item in all_items if item['id'].startswith('CRS')]
        sys_items = [item for item in all_items if item['id'].startswith('SYS')]
        sds_items = [item for item in all_items if item['id'].startswith('SDS')]
        test_items = [item for item in all_items if item['id'].startswith('TC-')]
        req_items = crs_items + sys_items + sds_items
        
        # CRS without SYS
        crs_no_sys = [crs['id'] for crs in crs_items 
                     if not any(sys for sys in sys_items if crs['id'] in sys.get('links', []))]
        
        # SYS without SDS
        sys_no_sds = [sys['id'] for sys in sys_items 
                     if not any(sds for sds in sds_items if sys['id'] in sds.get('links', []))]
        
        # Requirements without tests
        req_no_test = [req['id'] for req in req_items 
                      if not any(test for test in test_items if req['id'] in test.get('links', []))]
        
        return {
            'crs': crs_no_sys,
            'sys': sys_no_sds,
            'req_no_test': req_no_test
        }
    
    def _export_pdf(self, markdown_content: str, filename: str) -> Path:
        """
        Export markdown to PDF using WeasyPrint.
        
        Args:
            markdown_content: Markdown content to convert
            filename: Output filename (without extension)
            
        Returns:
            Path to generated PDF file
        """
        # Convert markdown to HTML
        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'toc']
        )
        
        # Load CSS
        css_path = self.template_dir / 'styles' / 'default.css'
        css_content = css_path.read_text() if css_path.exists() else self._get_default_css()
        
        # Wrap in HTML template
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                {css_content}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Generate PDF
        output_path = Path(f"/tmp/{filename}.pdf")
        HTML(string=full_html).write_pdf(output_path)
        return output_path
    
    def _get_default_css(self) -> str:
        """Get default CSS for PDF styling."""
        return """
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 2cm;
        }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; }
        h2 { color: #34495e; margin-top: 1.5em; }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th { background-color: #3498db; color: white; }
        """
