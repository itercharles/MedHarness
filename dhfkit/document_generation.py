"""Document generation engine for DHF."""

from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown
import re


_VOLATILE_ROWS = re.compile(
    r'^\|\s*\*\*(?:Version|Generated)\*\*\s*\|.*$', re.MULTILINE
)

_GENERATED_DATE = re.compile(r'\|\s*\*\*Generated\*\*\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|')


def _body(markdown_content: str) -> str:
    """Strip the rows that change on every run, for content comparison.

    Version and generation date are metadata about the render, not about the
    document's substance; comparing with them in place would make every
    regeneration look like a revision.
    """
    return _VOLATILE_ROWS.sub('', markdown_content).strip()


class DocumentGenerator:
    """Generate regulatory documents from templates."""

    def __init__(self, loader, config, template_dir: Path):
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
        self.jinja_env.filters['status_badge'] = self._status_badge
        self.jinja_env.filters['format_date'] = self._format_date

    def _status_badge(self, status: str) -> str:
        return status.upper() if status else 'UNKNOWN'

    def _format_date(self, date_str) -> str:
        if not date_str:
            return 'N/A'
        if hasattr(date_str, 'isoformat'):
            return date_str.isoformat()[:10]
        return str(date_str)[:10]

    def generate_markdown_spec(self, doc_type_code: str, doc_specs: dict, dhf_root: Path) -> Tuple[str, Path]:
        if doc_type_code not in doc_specs:
            raise ValueError(f"No document specification configured for {doc_type_code}")

        spec_config = doc_specs[doc_type_code]
        template_name = spec_config.get('source') or spec_config['template']
        output_rel_path = spec_config['output']
        output_path = dhf_root.parent / output_rel_path

        doc_type_config = self.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            raise ValueError(f"Unknown document type: {doc_type_code}")

        existing_content = ""
        existing_version = None
        existing_date = None
        if output_path.exists():
            existing_content = output_path.read_text(encoding="utf-8")
            version_match = re.search(r'\|\s*\*\*Version\*\*\s*\|\s*(\d+)\.(\d+)\s*\|', existing_content)
            if version_match:
                existing_version = (int(version_match.group(1)), int(version_match.group(2)))
            date_match = _GENERATED_DATE.search(existing_content)
            if date_match:
                existing_date = date_match.group(1)

        # Match on the configured prefix, not the bare code: "SYSARCH-001"
        # startswith("SYS") is true, which put every architecture item into the
        # system requirements specification.
        prefix = getattr(doc_type_config, "prefix", None) or f"{doc_type_code}-"
        all_items = self.loader.load_all()
        items = [
            item.model_dump(by_alias=True, exclude_none=True)
            for item in all_items
            if item.uid.startswith(prefix)
        ]
        items.sort(key=lambda x: x['id'])

        project_name = getattr(self.config, 'project_name', 'DHF Project')
        template = self.jinja_env.get_template(template_name)

        today = datetime.now().isoformat()[:10]

        def _render(version: str, generation_date: str) -> str:
            return template.render(
                doc_type_code=doc_type_code,
                doc_type_name=spec_config.get('doc_type_name', doc_type_config.name),
                test_type=spec_config.get('test_type', ''),
                project_name=project_name,
                version=version,
                generation_date=generation_date,
                status='Draft',
                items=items,
                directory=getattr(doc_type_config, 'directory', ''),
            )

        # The document version is regulatory metadata: it must track content
        # revisions, not how many times the generator ran. Previously every
        # regeneration bumped the minor version and rewrote the file, so a CI
        # job that regenerates docs inflated the version of a controlled
        # document without anything having changed.
        base_major, base_minor = existing_version or (1, 0)

        if existing_content:
            # Compare a render that reuses the existing document's date. Masking
            # only the metadata rows was not enough — templates also print the
            # date in prose ("**Last Updated**: …"), so a regeneration on a later
            # day looked like a content change and bumped the version.
            candidate = _render(f"{base_major}.{base_minor}", existing_date or today)
            if _body(candidate) == _body(existing_content):
                return existing_content, output_path
            markdown_content = _render(f"{base_major}.{base_minor + 1}", today)
        else:
            markdown_content = _render(f"{base_major}.{base_minor}", today)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_content, encoding="utf-8")

        return markdown_content, output_path

    def _read_static_doc(self, doc_type_code: str, doc_specs: dict, dhf_root: Path) -> tuple[str, str]:
        """Return (markdown, stem) for a generated specification on disk."""
        if doc_type_code not in doc_specs:
            raise ValueError(f"No document specification configured for {doc_type_code}")

        static_file_path = dhf_root.parent / doc_specs[doc_type_code]['output']
        if not static_file_path.exists():
            raise FileNotFoundError(f"Static document not found: {static_file_path}")

        stem = f"{doc_type_code}_Specification_{datetime.now().strftime('%Y%m%d')}"
        return static_file_path.read_text(encoding="utf-8"), stem

    def export_static_doc_to_html(self, doc_type_code: str, doc_specs: dict,
                                  dhf_root: Path, out_dir: Path) -> Path:
        """Render a generated specification to a standalone, styled HTML file.

        Needs no native libraries, so it works on a base ``pip install
        medharness`` — unlike the PDF path, which requires WeasyPrint's
        cairo/pango stack.
        """
        markdown_content, stem = self._read_static_doc(doc_type_code, doc_specs, dhf_root)
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{stem}.html"
        output_path.write_text(self._build_html(markdown_content), encoding="utf-8")
        return output_path

    def export_static_doc_to_pdf(self, doc_type_code: str, doc_specs: dict,
                                 dhf_root: Path, out_dir: Path | None = None) -> Path:
        """Export a generated specification to PDF.

        Args:
            doc_type_code: Document type code
            doc_specs: document_specifications dict from global config
            dhf_root: Path to DHF root directory
            out_dir: Destination directory. Defaults to the DHF's exports
                directory — never a shared /tmp, where concurrent runs on one
                CI runner overwrite each other's evidence.

        Returns:
            Path to generated PDF file
        """
        markdown_content, stem = self._read_static_doc(doc_type_code, doc_specs, dhf_root)
        target = out_dir or (dhf_root / "documents" / "exports")
        target.mkdir(parents=True, exist_ok=True)
        return self._export_pdf(markdown_content, target / f"{stem}.pdf")

    def _build_html(self, markdown_content: str) -> str:
        """Render markdown to a self-contained HTML document with inline CSS."""
        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'toc', 'md_in_html']
        )

        css_path = self.template_dir / 'styles' / 'default.css'
        css_content = css_path.read_text(encoding="utf-8") if css_path.exists() else self._get_default_css()

        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<style>\n{css_content}\n</style>\n"
            "</head>\n"
            f"<body>\n{html_content}\n</body>\n"
            "</html>\n"
        )

    def _export_pdf(self, markdown_content: str, output_path: Path) -> Path:
        """Export markdown to PDF using WeasyPrint."""
        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise RuntimeError(
                "PDF export needs the 'docs' extra: pip install 'medharness[docs]'. "
                "WeasyPrint also requires native cairo/pango libraries. "
                "Use HTML export instead if those are unavailable."
            ) from exc
        except OSError as exc:
            # WeasyPrint imports cleanly but raises OSError when its native
            # libraries are missing — common on macOS without Homebrew pango.
            raise RuntimeError(
                f"PDF export unavailable — WeasyPrint cannot load its native "
                f"libraries: {exc}. Use HTML export instead."
            ) from exc

        HTML(string=self._build_html(markdown_content)).write_pdf(output_path)
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
