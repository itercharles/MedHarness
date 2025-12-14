"""Core CompliantFlow tree management."""

from pathlib import Path
import yaml
from typing import List, Optional, Dict, Any
from .models.item import Item
from .models.config import ProjectConfig
from .models.document import Document
from .models.change_request import ChangeRequest, ChangeStatus
from .graph.engine import GraphEngine
from .graph.analysis import generate_traceability_matrix
from .repository.loader import ItemLoader
from .repository.saver import ItemSaver
from .repository.git import GitRepository
from .change_management.change_tracker import ChangeTracker
from .change_management.workflow import ChangeWorkflow
from .change_management.impact_analyzer import ImpactAnalyzer
from .review.review_tracker import ReviewTracker
from .review.review_workflow import ReviewWorkflow as ReviewWorkflowEngine
from .review.checklist_engine import ChecklistEngine
from .defect.defect_tracker import DefectTracker
from .defect.defect_workflow import DefectWorkflow


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
        
        # Initialize change management
        self.change_tracker = ChangeTracker(self.repo_root, git_repo=self.git)
        self.impact_analyzer = ImpactAnalyzer(self.graph)
        
        # Initialize review system
        self.review_tracker = ReviewTracker(self.repo_root, git_repo=self.git)
        
        # Initialize checklist engine (always set attribute even if config missing)
        checklist_config = self.repo_root / "config" / "review_checklists.yaml"
        try:
            self.checklist_engine = ChecklistEngine(checklist_config)
        except Exception as e:
            print(f"Warning: Failed to initialize checklist engine: {e}")
            # Create a minimal checklist engine with empty config
            self.checklist_engine = ChecklistEngine(Path("/dev/null"))
        
        # Initialize defect tracking
        self.defect_tracker = DefectTracker(self.repo_root, git_repo=self.git)
        
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
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def refresh(self):
        """Reload all items and rebuild graph."""
        items = self.loader.load_all()
        self.graph.build_from_items(items)
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """
        Get all items as dictionaries.
        
        Returns:
            List of item dictionaries
        """
        items = []
        for node_id in self.graph.graph.nodes:
            item: Item = self.graph.graph.nodes[node_id]['item']
            items.append(item.model_dump(by_alias=True, exclude_none=True))
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

    # Review Management Methods
    
    def create_review(
        self,
        item_id: str,
        reviewer: str,
        checklist_id: Optional[str] = None,
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a review for an item."""
        review = self.review_tracker.create_review(item_id, reviewer, checklist_id, author)
        return review.model_dump(mode='json')
    
    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Get review by ID."""
        review = self.review_tracker.get_review(review_id)
        return review.model_dump(mode='json') if review else None
    
    def list_reviews(
        self,
        status: Optional[str] = None,
        reviewer: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List reviews with optional filters."""
        from .models.review import ReviewStatus
        status_enum = ReviewStatus(status) if status else None
        reviews = self.review_tracker.list_reviews(status=status_enum, reviewer=reviewer)
        return [r.model_dump(mode='json') for r in reviews]
    
    def approve_review(
        self,
        review_id: str,
        comments: str,
        signature: Optional[str] = None,
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve a review."""
        success, message = ReviewWorkflowEngine.approve_review(
            self.review_tracker,
            review_id,
            comments,
            signature,
            author
        )
        return {'success': success, 'message': message}
    
    def reject_review(
        self,
        review_id: str,
        comments: str,
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reject a review."""
        success, message = ReviewWorkflowEngine.reject_review(
            self.review_tracker,
            review_id,
            comments,
            author
        )
        return {'success': success, 'message': message}

    # Defect Management Methods
    
    def create_defect(
        self,
        data: Dict[str, Any],
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new defect."""
        defect = self.defect_tracker.create_defect(data, author=author)
        return defect.model_dump(mode='json')
    
    def get_defect(self, defect_id: str) -> Optional[Dict[str, Any]]:
        """Get defect by ID."""
        defect = self.defect_tracker.get_defect(defect_id)
        return defect.model_dump(mode='json') if defect else None
    
    def list_defects(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List defects with optional filters."""
        from .models.defect import DefectStatus, DefectSeverity
        
        status_enum = DefectStatus(status) if status else None
        severity_enum = DefectSeverity(severity) if severity else None
        
        defects = self.defect_tracker.list_defects(
            status=status_enum,
            severity=severity_enum,
            assigned_to=assigned_to
        )
        return [d.model_dump(mode='json') for d in defects]
    
    def assign_defect(
        self,
        defect_id: str,
        assigned_to: str,
        author: str
    ) -> Dict[str, Any]:
        """Assign defect to an investigator."""
        success, message = DefectWorkflow.assign_defect(
            self.defect_tracker,
            defect_id,
            assigned_to,
            author
        )
        return {'success': success, 'message': message}
    
    def start_defect_investigation(
        self,
        defect_id: str,
        author: str
    ) -> Dict[str, Any]:
        """Start investigating a defect."""
        success, message = DefectWorkflow.start_investigation(
            self.defect_tracker,
            defect_id,
            author
        )
        return {'success': success, 'message': message}
    
    def resolve_defect(
        self,
        defect_id: str,
        root_cause: str,
        resolution: str,
        author: str
    ) -> Dict[str, Any]:
        """Mark defect as resolved."""
        success, message = DefectWorkflow.resolve_defect(
            self.defect_tracker,
            defect_id,
            root_cause,
            resolution,
            author
        )
        return {'success': success, 'message': message}
    
    def verify_defect_resolution(
        self,
        defect_id: str,
        verification: str,
        author: str
    ) -> Dict[str, Any]:
        """Verify defect resolution."""
        success, message = DefectWorkflow.verify_resolution(
            self.defect_tracker,
            defect_id,
            verification,
            author
        )
        return {'success': success, 'message': message}
    
    def close_defect(
        self,
        defect_id: str,
        author: str
    ) -> Dict[str, Any]:
        """Close a defect."""
        success, message = DefectWorkflow.close_defect(
            self.defect_tracker,
            defect_id,
            author
        )
        return {'success': success, 'message': message}
    
    def defer_defect(
        self,
        defect_id: str,
        reason: str,
        author: str
    ) -> Dict[str, Any]:
        """Defer a defect to future release."""
        success, message = DefectWorkflow.defer_defect(
            self.defect_tracker,
            defect_id,
            reason,
            author
        )
        return {'success': success, 'message': message}
    
    def reopen_defect(
        self,
        defect_id: str,
        reason: str,
        author: str
    ) -> Dict[str, Any]:
        """Reopen a closed or resolved defect."""
        success, message = DefectWorkflow.reopen_defect(
            self.defect_tracker,
            defect_id,
            reason,
            author
        )
        return {'success': success, 'message': message}

