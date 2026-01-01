"""Core CompliantFlow tree management."""

from pathlib import Path
import yaml
from typing import List, Optional, Dict, Any
from .models.item import Item
from .models.config import ProjectConfig
from .graph.engine import GraphEngine
from .graph.analysis import generate_traceability_matrix
from .repository.loader import ItemLoader
from .repository.saver import ItemSaver
from .repository.git import GitRepository


class CompliantFlowCore:
    """
    Core CompliantFlow library.
    
    Provides a unified interface for managing requirements traceability
    using Pydantic v2, NetworkX, and GitPython.
    """
    
    def __init__(
        self,
        repo_root: Path,
        auto_commit: bool = False
    ):
        """
        Initialize CompliantFlow core.
        
        Args:
            repo_root: Path to repository root
            auto_commit: Whether to auto-commit changes
        """
        self.repo_root = Path(repo_root)
        self.specs_dir = self.repo_root / "items"
        self.config_path = self.repo_root / "config" / "project_config.yaml"
        
        # Initialize components
        self.config: Optional[ProjectConfig] = None
        self.git = GitRepository(self.repo_root, auto_commit=auto_commit)
        self.loader = ItemLoader(self.specs_dir)
        self.saver = ItemSaver(self.specs_dir, git_repo=self.git)
        self.graph = GraphEngine()
        
        # Load config and build graph
        self._load_config()
        self.refresh()
    
    def _load_config(self):
        """Load project configuration."""
        if not self.config_path.exists():
            print(f"Warning: Config not found at {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
            self.config = ProjectConfig.model_validate(data)
            self.graph.config = self.config
            # Pass config to saver for dynamic directory mapping
            self.saver.project_config = self.config
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def refresh(self):
        """Reload all items and rebuild graph."""
        items = self.loader.load_all()
        self.graph.build_from_items(items)
    
    def _aggregate_relationship_fields(self, item: Dict[str, Any], doc_type_code: str) -> List[str]:
        """
        Aggregate all relationship field values from an item.
        
        Args:
            item: Item dictionary
            doc_type_code: Document type code (e.g., 'SRS', 'TC-SRS')
            
        Returns:
            List of all linked item IDs from all relationship fields
        """
        all_links = []
        
        # Get document type config
        doc_type_config = self.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            return []
        
        # Get all relationship fields from properties
        properties = doc_type_config.properties if hasattr(doc_type_config, 'properties') else []
        for prop in properties:
            if isinstance(prop, dict):
                prop_format = prop.get('format')
                field_name = prop.get('name')
            elif hasattr(prop, 'format'):
                prop_format = prop.format
                field_name = prop.name
            else:
                continue
            
            # Check if it's a relationship field
            is_relationship = prop_format == 'relationship'
            
            if is_relationship and field_name in item:
                value = item[field_name]
                if isinstance(value, list):
                    all_links.extend([v for v in value if v])
                elif value:
                    all_links.append(value)
        
        return all_links
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """
        Get all items as dictionaries, including automated tests from code.
        
        Returns:
            List of item dictionaries (YAML items + scanned automated tests)
        """
        # Get items from YAML files
        items = []
        for node_id in self.graph.graph.nodes:
            item: Item = self.graph.graph.nodes[node_id]['item']
            item_dict = item.model_dump(by_alias=True, exclude_none=True)
            # Add computed property for traceability traversal
            item_dict['all_linked_uids'] = item.all_linked_uids
            items.append(item_dict)
        
        # Scan for automated test cases from Python code
        try:
            from test_results.test_case_scanner import AutomatedTestScanner
            
            # Find tests directory (sibling to src)
            tests_dir = self.repo_root.parent / "tests"
            if tests_dir.exists():
                scanner = AutomatedTestScanner(tests_dir)
                automated_tests = scanner.scan_all_tests()
                
                # Filter out duplicates (prefer YAML if exists)
                existing_ids = {item['id'] for item in items}
                for test in automated_tests:
                    if test['id'] not in existing_ids:
                        # Aggregate all relationship fields for automated tests
                        test_type_code = test['id'].split('-')[0]  # e.g., 'TC' from 'TC-SRS-001'
                        test['all_linked_uids'] = self._aggregate_relationship_fields(test, test_type_code)
                        items.append(test)
        except Exception as e:
            # Silently fail if scanner not available or tests dir missing
            print(f"Note: Could not scan automated tests: {e}")
        
        return items
    
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
        # Auto-generate ID if not provided
        if 'id' not in item_data or not item_data['id']:
            from utils.id_generator import get_next_id
            
            # Determine prefix from item data or infer from type
            prefix = None
            if 'type' in item_data:
                # Get prefix from document type
                doc_type = self.config.get_doc_type(item_data['type'])
                if doc_type:
                    prefix = doc_type.prefix
            
            if not prefix:
                raise ValueError("Cannot auto-generate ID: document type not specified")
            
            # Get existing IDs for this prefix
            all_items = self.get_all_items()
            existing_ids = [item['id'] for item in all_items if item['id'].startswith(prefix)]
            
            # Generate next ID
            item_data['id'] = get_next_id(prefix, existing_ids)
        
        # Set initial status only if not provided (backend responsibility)
        if 'status' not in item_data:
            doc_type_code = item_data['id'].split('-')[0]
            initial_state = self.get_initial_state(doc_type_code)
            item_data['status'] = initial_state
        
        # Validate and create item
        item = Item.model_validate(item_data)
        
        # Save to file
        self.saver.save(item, author=author, cr_id=cr_id)
        
        # Refresh graph
        self.refresh()
        
        return item.model_dump(by_alias=True, exclude_none=True)
    
    def update_item(
        self,
        uid: str,
        data: Dict[str, Any],
        author: Optional[str] = None,
        cr_id: Optional[str] = None
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
        # Load existing item
        existing = self.loader.load_by_uid(uid)
        if not existing:
            return None
        
        # Update with new data
        updated_data = existing.model_dump(exclude_unset=True)
        updated_data.update(data)
        
        # Check if item was in a stable status before update
        # If so, reset to draft and clear approval metadata (core business logic)
        doc_type_config = self.config.get_doc_type_by_prefix(existing.prefix)
        if doc_type_config and doc_type_config.lifecycle:
            # Only set initial status if status is not already provided in the update data
            if 'status' not in data:
                initial_status = self.get_initial_state(doc_type_config.code)
                updated_data['status'] = initial_status
            
            # Check if old status was stable
            old_status = existing.status if hasattr(existing, 'status') else None
            if old_status:
                old_state_info = self.get_state_info(old_status)
                if old_state_info.get('is_stable', False):
                    # Item was stable - reset to initial state and clear approval fields
                    initial_state = self.get_initial_state(doc_type_config.code)
                    updated_data['status'] = initial_state
                    
                    # Clear approval-related fields
                    approval_fields = ['approved_by', 'approved_date', 'reviewer', 'review_date',
                                     'verified_by', 'verified_date', 'released_by', 'released_date',
                                     'manual_verifications']
                    for field in approval_fields:
                        if field in updated_data:
                            del updated_data[field]
        
        # Validate
        item = Item.model_validate(updated_data)
        
        # Save with CR reference - only save fields that were explicitly set
        # This prevents default fields (active, history) from being added
        self.saver.save(item, author=author, cr_id=cr_id)
        
        # Refresh graph
        self.refresh()
        
        return item.model_dump(by_alias=True, exclude_none=True)
    
    def can_edit_item(self, uid: str) -> tuple[bool, str, Optional[str], Optional[Dict]]:
        """
        Check if an item can be edited based on its status and CR requirements.
        
        Args:
            uid: Item UID
            
        Returns:
            Tuple of (can_edit, button_label, cr_id, available_cr)
            - can_edit: Whether the item can be edited
            - button_label: Label for the edit button
            - cr_id: Active CR ID if applicable, None otherwise
            - available_cr: Available CR dict if item needs to be added, None otherwise
        """
        from utils.cr_manager import (
            is_change_control_enabled,
            get_cr_for_item,
            get_non_stable_cr,
            is_cr_stable,
            get_cr_doc_type
        )
        
        item = self.get_item(uid)
        if not item:
            return False, "Item not found", None, None
        
        # Check if item has a stable status
        doc_type_config = self.config.get_doc_type_by_prefix(item['id'].split('-')[0] + '-')
        if not doc_type_config or not doc_type_config.lifecycle:
            # No workflow - can edit
            return True, "✏️ Edit", None, None
        
        
        current_status = item.get('status')
        if not current_status:
            # No status - can edit
            return True, "✏️ Edit", None, None
        
        state_info = self.get_state_info(current_status)
        is_stable = state_info.get('is_stable', False)
        
        if not is_stable:
            # Not stable - can edit normally
            return True, "✏️ Edit", None, None
        
        # Item is stable - check change control
        if not is_change_control_enabled(self):
            # Change control not enabled - locked
            return False, "🔒 Locked", None, None
        
        # Change control enabled - check for CR
        existing_cr = get_cr_for_item(uid, self)
        
        if existing_cr:
            # Item is linked to a CR - check if CR is stable
            if is_cr_stable(existing_cr, self):
                # CR is stable - can't edit
                return False, "🔒 Locked", None, None
            else:
                # CR is non-stable - can edit
                return True, f"✏️ Edit ({existing_cr['id']})", existing_cr['id'], None
        else:
            # No CR - check if there's an available CR to add to
            available_cr = get_non_stable_cr(self)
            if available_cr:
                # Return info about available CR so UI can show "Add to CR" button
                return False, f"📝 Add to {available_cr['id']}", None, available_cr
            else:
                # No CR available - locked
                return False, "🔒 Locked", None, None
    
    def get_relationship_options(self, item_id: str, relationship_field: str) -> list[str]:
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
        
        # Get doc type config for this item
        item_prefix = item['id'].split('-')[0] + '-'
        doc_type_config = self.config.get_doc_type_by_prefix(item_prefix)
        if not doc_type_config:
            return []
        
        # Get all items
        all_items = self.get_all_items()
        
        # Get allowed target types from relations config
        allowed_prefixes = set()
        if hasattr(doc_type_config, 'relations') and doc_type_config.relations:
            for relation in doc_type_config.relations:
                # Handle both Pydantic model and dict for robustness
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
                        
        
        # Filter items by allowed prefixes
        if allowed_prefixes:
            return [i['id'] for i in all_items 
                   if i['id'] != item_id 
                   and any(i['id'].startswith(prefix) for prefix in allowed_prefixes)]
        else:
            # No specific restrictions - return all items except self
            return [i['id'] for i in all_items if i['id'] != item_id]
    
    def get_doc_type_metrics(self, doc_type_code: str) -> Dict[str, Any]:
        """
        Calculate metrics for a document type.
        
        Args:
            doc_type_code: Document type code (e.g., 'SYS', 'RISK')
            
        Returns:
            Dictionary with metrics:
            {
                'total': 42,
                'by_status': {'draft': 10, 'approved': 30, 'retired': 2},
                'completion_rate': 0.71
            }
        """
        doc_type_config = self.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            return {'total': 0, 'by_status': {}, 'completion_rate': 0.0}
        
        # Get all items for this doc type
        prefix = doc_type_config.prefix
        all_items = self.get_all_items()
        items = [i for i in all_items if i['id'].startswith(prefix)]
        
        total = len(items)
        if total == 0:
            return {'total': 0, 'by_status': {}, 'completion_rate': 0.0}
        
        # Count by status
        by_status = {}
        for item in items:
            status = item.get('status', 'unknown')
            by_status[status] = by_status.get(status, 0) + 1
        
        
        # Calculate completion rate (items in stable states)
        lifecycle = doc_type_config.lifecycle
        if lifecycle:
            states = lifecycle.get('states', [])
            stable_states = [s.get('id') for s in states if s.get('is_stable', False)]
            stable_count = sum(by_status.get(state, 0) for state in stable_states)
            completion_rate = stable_count / total if total > 0 else 0.0
        else:
            completion_rate = 0.0
        
        return {
            'total': total,
            'by_status': by_status,
            'completion_rate': completion_rate
        }
    
    def get_form_schema(self, doc_type_code: str, item_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get form schema for creating/editing items.
        
        Args:
            doc_type_code: Document type code (e.g., 'SYS', 'RISK')
            item_id: Optional item ID for edit mode (to get current values)
            
        Returns:
            Dictionary with form field definitions
        """
        from .models.config import PropertyConfig, PropertyFormat
        
        doc_type_config = self.config.get_doc_type(doc_type_code)
        if not doc_type_config:
            return {'fields': []}
        
        # Get current item data if editing
        current_item = self.get_item(item_id) if item_id else {}
        
        # Get properties from config
        properties = doc_type_config.properties if hasattr(doc_type_config, 'properties') else []
        
        # Fields to skip
        skip_fields = {'id', 'file_path', 'status', 'active', 'reviewer', 'review_date', 
                      'verified_by', 'verified_date', 'approved_by', 'approved_date', 
                      'released_by', 'released_date', 'manual_verifications', 'timestamp'}
        
        fields = []
        
        
        for prop in properties:
            # First, extract the property name (even from string shorthand) to check if we should skip it
            prop_name = None
            if isinstance(prop, str):
                prop_name = prop
            elif isinstance(prop, PropertyConfig):
                prop_name = prop.name
            elif isinstance(prop, dict) and 'name' in prop:
                prop_name = prop['name']
            
            # Skip system-managed fields BEFORE validation
            if prop_name in skip_fields:
                continue
            
            # Now validate property configuration (after we know it's not a skip field)
            # STRICT: All properties must be explicitly PropertyConfig
            if isinstance(prop, str):
                raise ValueError(f"Invalid property configuration: '{prop}'. String shorthand is no longer supported. Please use a full PropertyConfig dictionary with a 'name' field.")
            elif isinstance(prop, PropertyConfig):
                prop_config = prop
            else:
                # Handle dict format (from YAML)
                # STRICT: Must be a full config with 'name'
                if isinstance(prop, dict):
                    if 'name' not in prop:
                        raise ValueError(f"Invalid property configuration: {prop}. Property dictionary MUST include a 'name' field.")
                    
                    prop_config = PropertyConfig(**prop)
                else:
                    # Invalid format
                    raise ValueError(f"Invalid property configuration: {prop}. Must be a string or a PropertyConfig dict with a 'name' field.")

            
            # Build field definition from PropertyConfig
            field = {
                'name': prop_name,
                'label': prop_config.display_label,
                'current_value': current_item.get(prop_name, prop_config.default or ''),
                'required': prop_config.required,
                'type': self._format_to_ui_type(prop_config.format),
                'placeholder': prop_config.placeholder,
                'help': prop_config.help,
            }
            
            # Add format-specific options
            if prop_config.format in [PropertyFormat.SELECT, PropertyFormat.MULTISELECT, PropertyFormat.RADIO]:
                field['options'] = prop_config.options or []
            
            if prop_config.format in [PropertyFormat.LONG_TEXT, PropertyFormat.MARKDOWN]:
                field['height'] = prop_config.height or 150
            
            if prop_config.format in [PropertyFormat.NUMBER, PropertyFormat.SLIDER]:
                field['min_value'] = prop_config.min_value
                field['max_value'] = prop_config.max_value
                if prop_config.format == PropertyFormat.SLIDER:
                    field['step'] = prop_config.step or 1
            
            # Handle relationship fields
            if prop_config.format in [PropertyFormat.ITEM_REFERENCE, PropertyFormat.ITEM_MULTISELECT]:
                field['target_types'] = prop_config.target_types
                field['options'] = self._get_item_options( prop_config.target_types, item_id)
            
            fields.append(field)
        
        return {'fields': fields}
    
    def delete_item(
        self,
        uid: str,
        author: Optional[str] = None
    ) -> bool:
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
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.
        
        Returns:
            Graph statistics
        """
        return self.graph.get_stats()
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate the project.
        
        Returns:
            Validation results
        """
        return self.graph.validate()
    
    def get_config(self) -> Optional[Dict[str, Any]]:
        """
        Get project configuration.
        
        Returns:
            Configuration dictionary
        """
        if not self.config:
            return None
        return self.config.model_dump()

    def get_traceability_matrix(self, source_type: str, target_type: str) -> List[Dict[str, Any]]:
        """
        Generate traceability matrix.
        
        Args:
            source_type: Source document type code (e.g., 'TC')
            target_type: Target document type code (e.g., 'SYS')
            
        Returns:
            List of traceability relationships
        """
        if not self.config:
            return []
            
        source_doc = self.config.get_doc_type(source_type)
        target_doc = self.config.get_doc_type(target_type)
        
        if not source_doc or not target_doc:
            return []
            
        return generate_traceability_matrix(
            self.graph,
            source_doc.prefix,
            target_doc.prefix
        )

    def get_policy_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a policy group without running checks.
        
        Args:
            group_id: ID of the policy group
            
        Returns:
            PolicyGroup dictionary or None
        """
        from .compliance.engine import PolicyEngine
        
        engine = PolicyEngine(self)
        # Still using governance directory, but method reflects generic nature
        path = self.repo_root / "governance" / f"{group_id}.yaml"
        
        group = engine.load_policy_group(path)
        if not group:
            return None
            
        return group.model_dump()

    def check_compliance(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Check compliance against a specific policy group.
        
        Args:
            group_id: ID of the policy group
            
        Returns:
            Compliance report dictionary or None
        """
        from .compliance.engine import PolicyEngine
        
        engine = PolicyEngine(self)
        path = self.repo_root / "governance" / f"{group_id}.yaml"
        
        group = engine.load_policy_group(path)
        if not group:
            return None
            
        report = engine.check_compliance(group)
        return report.model_dump()


    

    
    def _format_to_ui_type(self, format):
        """Convert PropertyFormat to UI type string."""
        from .models.config import PropertyFormat
        
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
            # Filter by target types
            filtered = [i for i in all_items if any(i['id'].startswith(f"{t}-") for t in target_types)]
        else:
            filtered = all_items
        
        # Exclude current item
        if exclude_item_id:
            filtered = [i for i in filtered if i['id'] != exclude_item_id]
        
        return [i['id'] for i in filtered]
    
    # Import lifecycle management methods
    from .lifecycle_methods import (
        get_available_transitions,
        get_state_info,
        _validate_criteria,
        execute_transition,
        is_item_editable,
        get_initial_state
    )
