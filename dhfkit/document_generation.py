"""Document generation engine for DHF."""

from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown


def load_weasyprint():
    """WeasyPrint's ``HTML`` class, imported without touching stdout.

    When its native libraries are missing, WeasyPrint prints an install banner
    to stdout on import — and stdout is where every command writes its JSON
    answer. Raises ImportError or OSError as the import itself would.
    """
    import contextlib
    import sys

    with contextlib.redirect_stdout(sys.stderr):
        from weasyprint import HTML
    return HTML

class DocumentGenerator:
    """Generate regulatory documents from templates."""

    def __init__(self, loader, config, template_dirs: list[Path]):
        self.loader = loader
        self.config = config
        self.template_dirs = list(template_dirs)

        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dirs),
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

    @staticmethod
    def _links(data: dict, link_fields) -> list[str]:
        """The IDs an item links to, through the link fields its type declares."""
        found: list[str] = []
        for field in link_fields:
            value = data.get(field)
            for uid in ([value] if isinstance(value, str) else value or []):
                if isinstance(uid, str) and uid and uid not in found:
                    found.append(uid)
        return found

    def render_markdown_spec(self, doc_type_code: str, doc_specs: dict, version: str) -> str:
        """A specification of one doc type's items, as Markdown, at ``version``.

        The version is the release the document ships in: a specification is
        rendered for a release, and its revision history is the items' history.
        """
        if doc_type_code not in doc_specs:
            raise ValueError(f"No document specification configured for {doc_type_code}")
        spec_config = doc_specs[doc_type_code]
        doc_type_config = self.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            raise ValueError(f"Unknown document type: {doc_type_code}")

        # Match on the configured prefix, not the bare code: "SYSARCH-001"
        # startswith("SYS") is true.
        prefix = doc_type_config.prefix
        link_fields = self.config.link_properties(doc_type_code)
        items = sorted(
            ({**data, 'links': self._links(data, link_fields)}
             for data in (item.model_dump(by_alias=True, exclude_none=True)
                          for item in self.loader.load_all() if item.uid.startswith(prefix))),
            key=lambda x: x['id'],
        )
        template = self.jinja_env.get_template(spec_config.get('source') or spec_config['template'])
        return template.render(
            doc_type_code=doc_type_code,
            doc_type_name=spec_config.get('doc_type_name', doc_type_config.name),
            test_type=spec_config.get('test_type', ''),
            project_name=self.config.project_name,
            version=version,
            generation_date=datetime.now().isoformat()[:10],
            status='Draft',
            items=items,
        )

    def export(self, doc_type_code: str, markdown_content: str, fmt: str, out_dir: Path,
               version: str) -> Path:
        """Write a rendered specification to ``out_dir`` as ``html`` or ``pdf``.

        HTML needs no native libraries; PDF needs WeasyPrint's cairo/pango stack.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{doc_type_code}_Specification_{version}.{fmt}"
        if fmt == "pdf":
            return self._export_pdf(markdown_content, output_path)
        output_path.write_text(self._build_html(markdown_content), encoding="utf-8")
        return output_path

    def _build_html(self, markdown_content: str) -> str:
        """Render markdown to a self-contained HTML document with inline CSS."""
        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'toc', 'md_in_html']
        )

        css_path = next((d / 'styles' / 'default.css' for d in self.template_dirs
                         if (d / 'styles' / 'default.css').exists()), None)
        css_content = css_path.read_text(encoding="utf-8") if css_path else self._get_default_css()

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
            HTML = load_weasyprint()
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
