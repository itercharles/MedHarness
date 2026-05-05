"""Document generation engine for DHF."""

from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown
import re


class DocumentGenerator:
    """Generate regulatory documents from templates."""

    def __init__(self, loader, config, template_dir: Path):
        """
        Initialize document generator.

        Args:
            loader: ItemLoader instance
            config: ProjectConfig instance
            template_dir: Path to templates directory
        """
        self.loader = loader
        self.config = config
        self.template_dir = template_dir

        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        self._register_filters()

    def _register_filters(self):
        """Register custom Jinja2 filters."""
        self.jinja_env.filters['status_badge'] = self._status_badge
        self.jinja_env.filters['format_date'] = self._format_date

    def _status_badge(self, status: str) -> str:
        """Format status as text badge."""
        return status.upper() if status else 'UNKNOWN'

    def _format_date(self, date_str) -> str:
        """Format ISO date or date object."""
        if not date_str:
            return 'N/A'
        if hasattr(date_str, 'isoformat'):
            return date_str.isoformat()[:10]
        return str(date_str)[:10]

    def generate_markdown_spec(self, doc_type_code: str, doc_specs: dict, dhf_root: Path) -> Tuple[str, Path]:
        """
        Generate markdown specification and save to static file location.

        Args:
            doc_type_code: Document type code (e.g., 'CRS', 'SYS')
            doc_specs: document_specifications dict from global config
            dhf_root: Path to DHF root directory

        Returns:
            Tuple of (markdown_content, output_path)
        """
        if doc_type_code not in doc_specs:
            raise ValueError(f"No document specification configured for {doc_type_code}")

        spec_config = doc_specs[doc_type_code]
        template_name = spec_config['template']
        output_rel_path = spec_config['output']
        output_path = dhf_root.parent / output_rel_path

        doc_type_config = self.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            raise ValueError(f"Unknown document type: {doc_type_code}")

        current_version = "1.0"
        if output_path.exists():
            existing_content = output_path.read_text(encoding="utf-8")
            version_match = re.search(r'\|\s*\*\*Version\*\*\s*\|\s*(\d+)\.(\d+)\s*\|', existing_content)
            if version_match:
                major = int(version_match.group(1))
                minor = int(version_match.group(2))
                current_version = f"{major}.{minor + 1}"

        # Gather all items of this type
        all_items = self.loader.load_all()
        items = [
            item.model_dump(by_alias=True, exclude_none=True)
            for item in all_items
            if item.uid.startswith(doc_type_code)
        ]
        items.sort(key=lambda x: x['id'])

        project_name = getattr(self.config, 'project_name', 'DHF Project')
        data = {
            'doc_type_code': doc_type_code,
            'doc_type_name': spec_config.get('doc_type_name', doc_type_config.name),
            'test_type': spec_config.get('test_type', ''),
            'project_name': project_name,
            'version': current_version,
            'generation_date': datetime.now().isoformat()[:10],
            'status': 'Draft',
            'items': items,
            'directory': doc_type_config.directory if hasattr(doc_type_config, 'directory') else ''
        }

        template = self.jinja_env.get_template(template_name)
        markdown_content = template.render(**data)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_content, encoding="utf-8")

        return markdown_content, output_path

    def export_static_doc_to_pdf(self, doc_type_code: str, doc_specs: dict, dhf_root: Path) -> Path:
        """
        Export existing static markdown document to PDF.

        Args:
            doc_type_code: Document type code
            doc_specs: document_specifications dict from global config
            dhf_root: Path to DHF root directory

        Returns:
            Path to generated PDF file
        """
        if doc_type_code not in doc_specs:
            raise ValueError(f"No document specification configured for {doc_type_code}")

        spec_config = doc_specs[doc_type_code]
        static_file_path = dhf_root.parent / spec_config['output']

        if not static_file_path.exists():
            raise FileNotFoundError(f"Static document not found: {static_file_path}")

        markdown_content = static_file_path.read_text(encoding="utf-8")

        filename = f"{doc_type_code}_Specification_{datetime.now().strftime('%Y%m%d')}"
        return self._export_pdf(markdown_content, filename)

    def _export_pdf(self, markdown_content: str, filename: str) -> Path:
        """Export markdown to PDF using WeasyPrint."""
        from weasyprint import HTML

        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'toc', 'md_in_html']
        )

        css_path = self.template_dir / 'styles' / 'default.css'
        css_content = css_path.read_text(encoding="utf-8") if css_path.exists() else self._get_default_css()

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
