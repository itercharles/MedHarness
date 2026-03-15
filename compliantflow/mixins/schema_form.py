"""Schema / Form mixin — metrics only."""

from typing import Dict, Any


class _SchemaFormMixin:

    def get_doc_type_metrics(self, doc_type_code: str) -> Dict[str, Any]:
        """
        Calculate metrics for a document type.

        Args:
            doc_type_code: Document type code or domain name (e.g., 'SYS', 'RISK')

        Returns:
            Dictionary with metrics: total, by_status, completion_rate
        """
        item_type = self.config.get_type(doc_type_code) if self.config else None
        if not item_type:
            return {'total': 0, 'by_status': {}, 'completion_rate': 0.0}

        prefix = item_type.id_prefix
        all_items = self.get_all_items()
        items = [i for i in all_items if i['id'].startswith(prefix)]

        total = len(items)
        if total == 0:
            return {'total': 0, 'by_status': {}, 'completion_rate': 0.0}

        by_status: Dict[str, int] = {}
        for item in items:
            status = item.get('status', 'unknown')
            by_status[status] = by_status.get(status, 0) + 1

        lifecycle = item_type.lifecycle
        if lifecycle:
            states = lifecycle.get('states', [])
            stable_states = [s.get('id') for s in states if s.get('is_stable', False)]
            stable_count = sum(by_status.get(state, 0) for state in stable_states)
            completion_rate = stable_count / total
        else:
            completion_rate = 0.0

        return {
            'total': total,
            'by_status': by_status,
            'completion_rate': completion_rate,
        }
