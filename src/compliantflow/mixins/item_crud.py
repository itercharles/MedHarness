"""Item CRUD mixin."""

from typing import List, Optional, Dict, Any

from traceability.models.item import Item


class _ItemCRUDMixin:

    def get_all_items(self) -> List[Dict[str, Any]]:
        """
        Get all items as dictionaries, including automated tests from code.

        Returns:
            List of item dictionaries (YAML items + scanned automated tests)
        """
        items = []
        for node_id in self.graph.graph.nodes:
            item: Item = self.graph.graph.nodes[node_id]['item']
            item_dict = item.model_dump(by_alias=True, exclude_none=True)
            item_dict['all_linked_uids'] = item.all_linked_uids
            items.append(item_dict)

        # Append TC items from the external ResultStore (no YAML files for TCs).
        try:
            existing_ids = {item['id'] for item in items}
            for tc_item in self.result_store.as_tc_items():
                if tc_item['id'] not in existing_ids:
                    items.append(tc_item)
        except Exception as e:
            print(f"Warning: Could not load test results: {e}")

        return items

    def get_items_filtered(
        self,
        doc_type_code: str,
        status_filter: Optional[List[str]] = None,
        search: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Return items for a document type, optionally filtered by status and search text.

        Args:
            doc_type_code: Document type code (e.g. 'SRS').
            status_filter: List of status values to include. None means all statuses.
            search: Case-insensitive substring matched against item id and title.

        Returns:
            Filtered list of item dictionaries.
        """
        doc_type_config = self.config.get_doc_type(doc_type_code) if self.config else None
        prefix = doc_type_config.prefix if doc_type_config else f"{doc_type_code}-"
        initial_state = self.get_initial_state(doc_type_code) if doc_type_config else None

        all_items = self.get_all_items()
        result = []
        search_lower = search.lower() if search else ""

        for item in all_items:
            if not item["id"].startswith(prefix):
                continue
            if status_filter is not None:
                item_status = item.get("status") or initial_state
                if item_status not in status_filter:
                    continue
            if search_lower:
                if search_lower not in item["id"].lower() and search_lower not in item.get("title", "").lower():
                    continue
            result.append(item)

        return result

    def get_item(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific item by UID.

        Args:
            uid: Item UID

        Returns:
            Item dictionary or None
        """
        if not self.graph.graph.has_node(uid):
            return None

        item: Item = self.graph.graph.nodes[uid]['item']
        return item.model_dump(by_alias=True, exclude_none=True)

    def create_item(self, item_data: dict, author: str = "system", cr_id: Optional[str] = None) -> dict:
        """
        Create a new item.

        Args:
            item_data: Item data dictionary (ID is optional - will be auto-generated if not provided)
            author: Author of the change
            cr_id: Optional CR ID for change control

        Returns:
            Created item as dictionary
        """
        if 'id' not in item_data or not item_data['id']:
            from utils.id_generator import get_next_id

            prefix = None
            if 'type' in item_data:
                doc_type = self.config.get_doc_type(item_data['type'])
                if doc_type:
                    prefix = doc_type.prefix

            if not prefix:
                raise ValueError("Cannot auto-generate ID: document type not specified")

            all_items = self.get_all_items()
            existing_ids = [item['id'] for item in all_items if item['id'].startswith(prefix)]
            item_data['id'] = get_next_id(prefix, existing_ids)

        doc_type_code = item_data['id'].split('-')[0]
        initial_state = self.get_initial_state(doc_type_code)
        item_data['status'] = initial_state

        item = Item.model_validate(item_data)
        self.saver.save(item, author=author, cr_id=cr_id)
        self.refresh()

        return item.model_dump(by_alias=True, exclude_none=True)

    def update_item(
        self,
        uid: str,
        data: Dict[str, Any],
        author: Optional[str] = None,
        cr_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing item.

        Args:
            uid: Item UID
            data: Updated item data
            author: Author name for git commit
            cr_id: Optional Change Request ID for git commit reference

        Returns:
            Updated item dictionary or None
        """
        existing = self.loader.load_by_uid(uid)
        if not existing:
            return None

        updated_data = existing.model_dump(exclude_unset=True)
        updated_data.update(data)

        doc_type_config = self.config.get_doc_type_by_prefix(existing.prefix)
        if doc_type_config and doc_type_config.lifecycle:
            if 'status' not in data:
                initial_status = self.get_initial_state(doc_type_config.code)
                updated_data['status'] = initial_status

            old_status = existing.status if hasattr(existing, 'status') else None
            if old_status:
                old_state_info = self.get_state_info(old_status)
                if old_state_info.get('is_stable', False):
                    initial_state = self.get_initial_state(doc_type_config.code)
                    updated_data['status'] = initial_state

                    approval_fields = ['approved_by', 'approved_date', 'reviewer', 'review_date',
                                       'verified_by', 'verified_date', 'released_by', 'released_date',
                                       'manual_verifications']
                    for field in approval_fields:
                        if field in updated_data:
                            del updated_data[field]

        item = Item.model_validate(updated_data)
        self.saver.save(item, author=author, cr_id=cr_id)
        self.refresh()

        return item.model_dump(by_alias=True, exclude_none=True)

    def delete_item(self, uid: str, author: Optional[str] = None) -> bool:
        """
        Delete an item.

        Args:
            uid: Item UID
            author: Author name for git commit

        Returns:
            True if deleted successfully
        """
        success = self.saver.delete(uid, author=author)
        if success:
            self.refresh()
        return success
