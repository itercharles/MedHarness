"""Item CRUD mixin."""

from typing import List, Optional, Dict, Any

from utils.models.item import Item


class _ItemCRUDMixin:

    def get_all_items(self) -> List[Dict[str, Any]]:
        """
        Get all items as dictionaries, including automated tests from ResultStore.

        Returns:
            List of item dictionaries (YAML items + TC items from ResultStore)
        """
        items = []
        for node_id in self.graph.graph.nodes:
            item: Item = self.graph.graph.nodes[node_id]['item']
            item_dict = item.model_dump(by_alias=True, exclude_none=True)
            item_dict['all_linked_uids'] = item.all_linked_uids
            items.append(item_dict)
        return items

    def get_items_filtered(
        self,
        doc_type_code: str,
        status_filter: Optional[List[str]] = None,
        search: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Return items for a document type, optionally filtered by status and search text.
        """
        doc_type_config = self.config.get_doc_type(doc_type_code) if self.config else None
        prefix = doc_type_config.prefix if doc_type_config else f"{doc_type_code}-"

        all_items = self.get_all_items()
        result = []
        search_lower = search.lower() if search else ""

        for item in all_items:
            if not item["id"].startswith(prefix):
                continue
            if status_filter is not None:
                item_status = item.get("status")
                if item_status not in status_filter:
                    continue
            if search_lower:
                if search_lower not in item["id"].lower() and search_lower not in item.get("title", "").lower():
                    continue
            result.append(item)

        return result

    def get_item(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get a specific item by UID."""
        if not self.graph.graph.has_node(uid):
            return None

        item: Item = self.graph.graph.nodes[uid]['item']
        return item.model_dump(by_alias=True, exclude_none=True)

    def create_item(self, item_data: dict, author: str = "system", cr_id: Optional[str] = None) -> dict:
        """Create a new item."""
        result = self._adapter.create_item(item_data, author=author, cr_id=cr_id)
        self.refresh()
        return result

    def update_item(
        self,
        uid: str,
        data: Dict[str, Any],
        author: Optional[str] = None,
        cr_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing item."""
        existing = self.get_item(uid)
        if not existing:
            return None

        doc_type_config = self.config.get_doc_type_by_prefix(existing.get('id', '').split('-')[0] + '-') if self.config else None
        if doc_type_config and doc_type_config.lifecycle:
            if 'status' not in data:
                initial_status = self.get_initial_state(doc_type_config.code)
                data = {**data, 'status': initial_status}

            old_status = existing.get('status')
            if old_status:
                old_state_info = self.get_state_info(old_status)
                if old_state_info.get('is_stable', False):
                    initial_state = self.get_initial_state(doc_type_config.code)
                    data = {**data, 'status': initial_state}
                    approval_fields = ['approved_by', 'approved_date', 'reviewer', 'review_date',
                                       'verified_by', 'verified_date', 'released_by', 'released_date']
                    # Remove from incoming data and explicitly null them to clear existing values
                    data = {k: v for k, v in data.items() if k not in approval_fields}
                    for field in approval_fields:
                        data[field] = None

        result = self._adapter.update_item(uid, data, author=author, cr_id=cr_id)
        if result:
            self.refresh()
        return result

    def delete_item(self, uid: str, author: Optional[str] = None) -> bool:
        """Delete an item."""
        success = self._adapter.delete_item(uid, author=author)
        if success:
            self.refresh()
        return success
