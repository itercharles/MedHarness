"""Change Request mixin."""

from typing import Optional, Dict, Tuple


class _ChangeRequestMixin:

    def get_cr_for_item(self, item_id: str) -> Optional[Dict]:
        """Return the first CR that lists *item_id* in its affected_items, or None."""
        from utils.cr_manager import is_change_control_enabled, get_cr_doc_type, get_affected_items_field
        if not is_change_control_enabled(self):
            return None
        cr_type = get_cr_doc_type(self)
        affected_field = get_affected_items_field(self)
        for item in self.get_all_items():
            if not item["id"].startswith(f"{cr_type}-"):
                continue
            if item_id in (item.get(affected_field) or []):
                return item
        return None

    def get_non_stable_cr(self) -> Optional[Dict]:
        """Return the first CR that is not in a stable workflow state, or None."""
        from utils.cr_manager import is_change_control_enabled, get_cr_doc_type
        if not is_change_control_enabled(self):
            return None
        cr_type = get_cr_doc_type(self)
        for item in self.get_all_items():
            if not item["id"].startswith(f"{cr_type}-"):
                continue
            state_info = self.get_state_info(item.get("status", ""))
            if not state_info.get("is_stable", False):
                return item
        return None

    def is_cr_stable(self, cr: Dict) -> bool:
        """Return True if *cr* is in a stable workflow state (or is missing)."""
        if not cr:
            return True
        state_info = self.get_state_info(cr.get("status", ""))
        return state_info.get("is_stable", False)

    def add_item_to_cr(self, cr_id: str, item_id: str) -> bool:
        """
        Add *item_id* to the affected_items list of *cr_id*.

        Returns True on success, False if the CR does not exist, is stable,
        or change control is disabled.
        """
        from utils.cr_manager import is_change_control_enabled, get_affected_items_field
        if not is_change_control_enabled(self):
            return False
        cr = self.get_item(cr_id)
        if not cr:
            return False
        if self.is_cr_stable(cr):
            return False
        affected_field = get_affected_items_field(self)
        affected = list(cr.get(affected_field) or [])
        if item_id not in affected:
            affected.append(item_id)
            cr[affected_field] = affected
            self.update_item(cr_id, cr)
        return True

    def can_edit_item(self, uid: str) -> Tuple[bool, str, Optional[str], Optional[Dict]]:
        """
        Check if an item can be edited based on its status and CR requirements.

        Args:
            uid: Item UID

        Returns:
            Tuple of (can_edit, button_label, cr_id, available_cr)
        """
        from utils.cr_manager import is_change_control_enabled

        item = self.get_item(uid)
        if not item:
            return False, "Item not found", None, None

        doc_type_config = self.config.get_doc_type_by_prefix(item['id'].split('-')[0] + '-')
        if not doc_type_config or not doc_type_config.lifecycle:
            return True, "✏️ Edit", None, None

        current_status = item.get('status')
        if not current_status:
            return True, "✏️ Edit", None, None

        state_info = self.get_state_info(current_status)
        is_stable = state_info.get('is_stable', False)

        if not is_stable:
            return True, "✏️ Edit", None, None

        if not is_change_control_enabled(self):
            return False, "🔒 Locked", None, None

        existing_cr = self.get_cr_for_item(uid)

        if existing_cr:
            if self.is_cr_stable(existing_cr):
                return False, "🔒 Locked", None, None
            else:
                return True, f"✏️ Edit ({existing_cr['id']})", existing_cr['id'], None
        else:
            available_cr = self.get_non_stable_cr()
            if available_cr:
                return False, f"📝 Add to {available_cr['id']}", None, available_cr
            else:
                return False, "🔒 Locked", None, None
