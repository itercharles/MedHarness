"""Document generation mixin for CompliantFlowCore."""


class _DocumentGenerationMixin:

    def get_available_doc_types(self) -> list:
        """Return doc type codes that have a document_specifications entry."""
        return self._adapter.get_available_doc_types()

    def generate_spec(self, doc_type_code: str) -> dict:
        """Generate (or regenerate) the markdown spec for one doc type.

        Returns {"doc_type", "output_path", "version"}.
        Raises ValueError if doc_type_code is not configured.
        """
        return self._adapter.generate_doc(doc_type_code)

    def export_pdf(self, doc_type_code: str) -> dict:
        """Regenerate the markdown spec then export to PDF.

        Returns {"doc_type", "md_path", "pdf_path", "version"}.
        Raises ValueError if doc_type_code is not configured.
        """
        return self._adapter.export_pdf(doc_type_code)
