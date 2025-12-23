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
    
    def create_item(
        self,
        data: Dict[str, Any],
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new item.
        
        Args:
            data: Item data
            author: Author name for git commit
            
        Returns:
            Created item dictionary
        """
        # Validate and create item
        item = Item.model_validate(data)
        
        # Save to file
        self.saver.save(item, author=author)
        
        # Refresh graph
        self.refresh()
        
        return item.model_dump(by_alias=True, exclude_none=True)
    
    def update_item(
        self,
        uid: str,
        data: Dict[str, Any],
        author: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing item.
        
        Args:
            uid: Item UID
            data: Updated item data
            author: Author name for git commit
            
        Returns:
            Updated item dictionary or None
        """
        # Load existing item
        existing = self.loader.load_by_uid(uid)
        if not existing:
            return None
        
        # Update with new data
        updated_data = existing.model_dump()
        updated_data.update(data)
        
        # Validate
        item = Item.model_validate(updated_data)
        
        # Save
        self.saver.save(item, author=author)
        
        # Refresh graph
        self.refresh()
        
        return item.model_dump(by_alias=True, exclude_none=True)
    
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

    # Change Management Methods
    
    def create_change_request(
        self,
        data: Dict[str, Any],
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new change request.
        
        Args:
            data: Change request data
            author: Author name for git commit
            
        Returns:
            Created change request dictionary
        """
        change_request = self.change_tracker.create_change_request(data, author=author)
        return change_request.model_dump(mode='json')
    
    def get_change_request(self, change_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a change request by ID.
        
        Args:
            change_id: Change request ID
            
        Returns:
            Change request dictionary or None
        """
        change_request = self.change_tracker.get_change_request(change_id)
        if not change_request:
            return None
        return change_request.model_dump(mode='json')
    
    def list_change_requests(
        self,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all change requests, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of change request dictionaries
        """
        status_enum = ChangeStatus(status) if status else None
        change_requests = self.change_tracker.list_change_requests(status=status_enum)
        return [cr.model_dump(mode='json') for cr in change_requests]
    
    def analyze_change_impact(self, change_id: str) -> Optional[Dict[str, Any]]:
        """
        Analyze the impact of a change request.
        
        Args:
            change_id: Change request ID
            
        Returns:
            Change impact analysis dictionary or None
        """
        change_request = self.change_tracker.get_change_request(change_id)
        if not change_request:
            return None
        
        impact = self.impact_analyzer.analyze_impact(change_request)
        return impact.model_dump(mode='json')
    
    def approve_change(
        self,
        change_id: str,
        reviewer: str,
        comments: str = ""
    ) -> Dict[str, Any]:
        """
        Approve a change request.
        
        Args:
            change_id: Change request ID
            reviewer: Name of reviewer
            comments: Review comments
            
        Returns:
            Result dictionary with success status and message
        """
        success, message = ChangeWorkflow.approve_change(
            self.change_tracker,
            change_id,
            reviewer,
            comments
        )
        return {'success': success, 'message': message}
    
    def reject_change(
        self,
        change_id: str,
        reviewer: str,
        comments: str
    ) -> Dict[str, Any]:
        """
        Reject a change request.
        
        Args:
            change_id: Change request ID
            reviewer: Name of reviewer
            comments: Reason for rejection
            
        Returns:
            Result dictionary with success status and message
        """
        success, message = ChangeWorkflow.reject_change(
            self.change_tracker,
            change_id,
            reviewer,
            comments
        )
        return {'success': success, 'message': message}
