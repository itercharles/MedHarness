"""Schema / Form mixin — form schema, relationship options, metrics."""

from typing import List, Optional, Dict, Any


class _SchemaFormMixin:

    def get_form_schema(self, doc_type_code: str, item_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get form schema for creating/editing items.

        Args:
            doc_type_code: Document type code (e.g., 'SYS', 'RISK')
            item_id: Optional item ID for edit mode (to get current values)

        Returns:
            Dictionary with form field definitions
        """
        from utils.models.config import PropertyConfig, PropertyFormat

        doc_type_config = self.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            return {'fields': []}

        current_item = self.get_item(item_id) if item_id else {}
        properties = doc_type_config.properties if hasattr(doc_type_config, 'properties') else []

        skip_fields = {'id', 'file_path', 'status', 'active', 'reviewer', 'review_date',
                       'verified_by', 'verified_date', 'approved_by', 'approved_date',
                       'released_by', 'released_date', 'timestamp'}

        fields = []

        for prop in properties:
            prop_name = None
            if isinstance(prop, str):
                prop_name = prop
            elif isinstance(prop, PropertyConfig):
                prop_name = prop.name
            elif isinstance(prop, dict) and 'name' in prop:
                prop_name = prop['name']

            if prop_name in skip_fields:
                continue

            if isinstance(prop, str):
                raise ValueError(
                    f"Invalid property configuration: '{prop}'. String shorthand is no longer "
                    "supported. Please use a full PropertyConfig dictionary with a 'name' field."
                )
            elif isinstance(prop, PropertyConfig):
                prop_config = prop
            else:
                if isinstance(prop, dict):
                    if 'name' not in prop:
                        raise ValueError(
                            f"Invalid property configuration: {prop}. Property dictionary MUST "
                            "include a 'name' field."
                        )
                    prop_config = PropertyConfig(**prop)
                else:
                    raise ValueError(
                        f"Invalid property configuration: {prop}. Must be a string or a "
                        "PropertyConfig dict with a 'name' field."
                    )

            field = {
                'name': prop_name,
                'label': prop_config.display_label,
                'current_value': current_item.get(prop_name, prop_config.default or ''),
                'required': prop_config.required,
                'type': self._format_to_ui_type(prop_config.format),
                'placeholder': prop_config.placeholder,
                'help': prop_config.help,
            }

            if prop_config.format in [PropertyFormat.SELECT, PropertyFormat.MULTISELECT, PropertyFormat.RADIO]:
                field['options'] = prop_config.options or []

            if prop_config.format in [PropertyFormat.LONG_TEXT, PropertyFormat.MARKDOWN]:
                field['height'] = prop_config.height or 150

            if prop_config.format in [PropertyFormat.NUMBER, PropertyFormat.SLIDER]:
                field['min_value'] = prop_config.min_value
                field['max_value'] = prop_config.max_value
                if prop_config.format == PropertyFormat.SLIDER:
                    field['step'] = prop_config.step or 1

            if prop_config.format in [PropertyFormat.ITEM_REFERENCE, PropertyFormat.ITEM_MULTISELECT]:
                field['target_types'] = prop_config.target_types
                field['options'] = self._get_item_options(prop_config.target_types, item_id)

            fields.append(field)

        return {'fields': fields}

    def get_relationship_options(self, item_id: str, relationship_field: str) -> List[str]:
        """
        Get allowed item IDs for a relationship field based on doc_type relations config.

        Args:
            item_id: ID of the item being edited
            relationship_field: Name of the relationship field (e.g., 'design', 'mitigated_by')

        Returns:
            List of allowed item IDs that can be selected for this relationship
        """
        item = self.get_item(item_id)
        if not item:
            return []

        item_prefix = item['id'].split('-')[0] + '-'
        doc_type_config = self.config.get_doc_type_by_prefix(item_prefix)
        if not doc_type_config:
            return []

        all_items = self.get_all_items()

        allowed_prefixes = set()
        if hasattr(doc_type_config, 'relations') and doc_type_config.relations:
            for relation in doc_type_config.relations:
                if isinstance(relation, dict):
                    rel_label = relation.get('label')
                    rel_target = relation.get('target')
                else:
                    rel_label = getattr(relation, 'label', None)
                    rel_target = getattr(relation, 'target', None)

                if rel_label == relationship_field and rel_target:
                    target_doc_type = self.config.get_doc_type(rel_target)
                    if target_doc_type and target_doc_type.prefix:
                        allowed_prefixes.add(target_doc_type.prefix)

        if allowed_prefixes:
            return [i['id'] for i in all_items
                    if i['id'] != item_id
                    and any(i['id'].startswith(prefix) for prefix in allowed_prefixes)]
        else:
            return [i['id'] for i in all_items if i['id'] != item_id]

    def get_doc_type_metrics(self, doc_type_code: str) -> Dict[str, Any]:
        """
        Calculate metrics for a document type.

        Args:
            doc_type_code: Document type code (e.g., 'SYS', 'RISK')

        Returns:
            Dictionary with metrics: total, by_status, completion_rate
        """
        doc_type_config = self.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            return {'total': 0, 'by_status': {}, 'completion_rate': 0.0}

        prefix = doc_type_config.prefix
        all_items = self.get_all_items()
        items = [i for i in all_items if i['id'].startswith(prefix)]

        total = len(items)
        if total == 0:
            return {'total': 0, 'by_status': {}, 'completion_rate': 0.0}

        by_status: Dict[str, int] = {}
        for item in items:
            status = item.get('status', 'unknown')
            by_status[status] = by_status.get(status, 0) + 1

        lifecycle = doc_type_config.lifecycle
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

    def _format_to_ui_type(self, format) -> str:
        """Convert PropertyFormat to UI type string."""
        from utils.models.config import PropertyFormat

        mapping = {
            PropertyFormat.SHORT_TEXT: 'text',
            PropertyFormat.LONG_TEXT: 'textarea',
            PropertyFormat.MARKDOWN: 'markdown',
            PropertyFormat.URL: 'url',
            PropertyFormat.SELECT: 'select',
            PropertyFormat.MULTISELECT: 'multiselect',
            PropertyFormat.RADIO: 'radio',
            PropertyFormat.CHECKBOX: 'checkbox',
            PropertyFormat.TOGGLE: 'toggle',
            PropertyFormat.NUMBER: 'number',
            PropertyFormat.SLIDER: 'slider',
            PropertyFormat.DATE: 'date',
            PropertyFormat.DATETIME: 'datetime',
            PropertyFormat.ITEM_REFERENCE: 'item_reference',
            PropertyFormat.ITEM_MULTISELECT: 'item_multiselect',
            PropertyFormat.FILE_UPLOAD: 'file_upload',
        }
        return mapping.get(format, 'text')

    def _get_item_options(self, target_types: Optional[List[str]], exclude_item_id: Optional[str] = None) -> List[str]:
        """Get item IDs for item reference fields."""
        all_items = self.get_all_items()

        if target_types:
            filtered = [i for i in all_items if any(i['id'].startswith(f"{t}-") for t in target_types)]
        else:
            filtered = all_items

        if exclude_item_id:
            filtered = [i for i in filtered if i['id'] != exclude_item_id]

        return [i['id'] for i in filtered]
