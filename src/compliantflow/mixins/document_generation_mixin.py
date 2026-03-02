"""Document generation mixin for CompliantFlowCore."""

import re
import yaml
from pathlib import Path
from traceability.document_generator import DocumentGenerator


class _DocumentGenerationMixin:

    def _get_doc_generator(self) -> DocumentGenerator:
        template_dir = self.repo_root / "documents" / "specifications" / "templates"
        return DocumentGenerator(self, template_dir)

    def get_available_doc_types(self) -> list:
        """Return doc type codes that have a document_specifications entry."""
        with open(self.config_path) as f:
            cfg = yaml.safe_load(f)
        return list(cfg.get("document_specifications", {}).keys())

    def generate_spec(self, doc_type_code: str) -> dict:
        """Generate (or regenerate) the markdown spec for one doc type.

        Returns {"doc_type", "output_path", "version"}.
        Raises ValueError if doc_type_code is not configured.
        """
        gen = self._get_doc_generator()
        content, output_path = gen.generate_markdown_spec(doc_type_code)
        version = "unknown"
        m = re.search(r'\|\s*\*\*Version\*\*\s*\|\s*([\d.]+)\s*\|', content)
        if m:
            version = m.group(1)
        return {
            "doc_type": doc_type_code,
            "output_path": str(output_path),
            "version": version,
        }
