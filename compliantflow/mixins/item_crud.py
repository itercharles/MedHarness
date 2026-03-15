"""Item CRUD mixin."""

from typing import List, Optional, Dict, Any


class _ItemCRUDMixin:

    def get_all_items(self) -> List[Dict[str, Any]]:
        """
        Get all items as dictionaries, including automated tests from ResultStore.

        Returns:
            List of item dictionaries (YAML items + TC items from ResultStore)
        """
        items = []
        for node_id in self.graph.graph.nodes:
            item: dict = self.graph.graph.nodes[node_id]['item']
            items.append(dict(item))
        return items

    def get_items_filtered(
        self,
        type_name: str,
        status_filter: Optional[List[str]] = None,
        search: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Return items for a type, optionally filtered by status and search text.
        """
        item_type = self.config.get_type(type_name) if self.config else None
        prefix = item_type.id_prefix if item_type else f"{type_name}-"

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
        item: dict = self.graph.graph.nodes[uid]['item']
        return dict(item)

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

        prefix = existing.get('id', '').split('-')[0] + '-'
        item_type = self.config.get_type_by_prefix(prefix) if self.config else None
        if item_type and item_type.lifecycle:
            if 'status' not in data:
                initial_status = self.get_initial_state(item_type.name)
                data = {**data, 'status': initial_status}

            old_status = existing.get('status')
            if old_status:
                old_state_info = self.get_state_info(old_status)
                if old_state_info.get('is_stable', False):
                    initial_state = self.get_initial_state(item_type.name)
                    data = {**data, 'status': initial_state}
                    approval_fields = ['approved_by', 'approved_date', 'reviewer', 'review_date',
                                       'verified_by', 'verified_date', 'released_by', 'released_date']
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
