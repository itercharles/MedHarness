"""Change request tracker - CRUD operations for change requests."""

import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..models.change_request import ChangeRequest, ChangeStatus
from ..repository.git import GitRepository


class ChangeTracker:
    """
    Manages change request lifecycle and storage.
    
    Change requests are stored as YAML files in DHF/change_requests/
    """
    
    def __init__(self, dhf_root: Path, git_repo: Optional[GitRepository] = None):
        """
        Initialize change tracker.
        
        Args:
            dhf_root: Path to DHF root directory
            git_repo: Optional Git repository for version control
        """
        self.dhf_root = Path(dhf_root)
        self.changes_dir = self.dhf_root / "change_requests"
        self.git_repo = git_repo
        
        # Create directory if it doesn't exist
        self.changes_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_next_id(self) -> str:
        """
        Generate next change request ID.
        
        Returns:
            Next available ID (e.g., CR-001, CR-002, etc.)
        """
        existing_files = list(self.changes_dir.glob("CR-*.yaml"))
        if not existing_files:
            return "CR-001"
        
        # Extract numbers from existing IDs
        numbers = []
        for f in existing_files:
            try:
                num = int(f.stem.split('-')[1])
                numbers.append(num)
            except (IndexError, ValueError):
                continue
        
        if not numbers:
            return "CR-001"
        
        next_num = max(numbers) + 1
        return f"CR-{next_num:03d}"
    
    def _get_file_path(self, change_id: str) -> Path:
        """Get file path for a change request ID."""
        return self.changes_dir / f"{change_id}.yaml"
    
    def create_change_request(
        self,
        data: Dict[str, Any],
        author: Optional[str] = None
    ) -> ChangeRequest:
        """
        Create a new change request.
        
        Args:
            data: Change request data (without ID)
            author: Author name for git commit
            
        Returns:
            Created ChangeRequest object
        """
        # Auto-generate ID if not provided
        if 'id' not in data:
            data['id'] = self._get_next_id()
        
        # Set created_date if not provided
        if 'created_date' not in data:
            data['created_date'] = datetime.now()
        
        # Validate and create model
        change_request = ChangeRequest.model_validate(data)
        
        # Save to file
        file_path = self._get_file_path(change_request.id)
        with open(file_path, 'w') as f:
            # Convert to dict and handle datetime serialization
            data_dict = change_request.model_dump(mode='json')
            yaml.dump(data_dict, f, default_flow_style=False, sort_keys=False)
        
        # Git commit if repository provided
        if self.git_repo:
            commit_msg = f"Create change request {change_request.id}: {change_request.title}"
            self.git_repo.commit_file(
                file_path,
                commit_msg,
                author_name=author,
                author_email=f"{author}@compliantflow.local" if author else None
            )
        
        return change_request
    
    def get_change_request(self, change_id: str) -> Optional[ChangeRequest]:
        """
        Get a change request by ID.
        
        Args:
            change_id: Change request ID
            
        Returns:
            ChangeRequest object or None if not found
        """
        file_path = self._get_file_path(change_id)
        if not file_path.exists():
            return None
        
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return ChangeRequest.model_validate(data)
    
    def list_change_requests(
        self,
        status: Optional[ChangeStatus] = None
    ) -> List[ChangeRequest]:
        """
        List all change requests, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of ChangeRequest objects
        """
        change_requests = []
        
        for file_path in self.changes_dir.glob("CR-*.yaml"):
            try:
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                cr = ChangeRequest.model_validate(data)
                
                # Apply status filter if provided
                if status is None or cr.status == status:
                    change_requests.append(cr)
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}")
                continue
        
        # Sort by ID (most recent first)
        change_requests.sort(key=lambda x: x.id, reverse=True)
        
        return change_requests
    
    def update_change_request(
        self,
        change_id: str,
        data: Dict[str, Any],
        author: Optional[str] = None
    ) -> Optional[ChangeRequest]:
        """
        Update an existing change request.
        
        Args:
            change_id: Change request ID
            data: Updated data (partial or full)
            author: Author name for git commit
            
        Returns:
            Updated ChangeRequest object or None if not found
        """
        # Load existing
        existing = self.get_change_request(change_id)
        if not existing:
            return None
        
        # Merge with updates
        updated_data = existing.model_dump()
        updated_data.update(data)
        
        # Validate
        change_request = ChangeRequest.model_validate(updated_data)
        
        # Save
        file_path = self._get_file_path(change_id)
        with open(file_path, 'w') as f:
            data_dict = change_request.model_dump(mode='json')
            yaml.dump(data_dict, f, default_flow_style=False, sort_keys=False)
        
        # Git commit
        if self.git_repo:
            commit_msg = f"Update change request {change_id}"
            self.git_repo.commit_file(
                file_path,
                commit_msg,
                author_name=author,
                author_email=f"{author}@compliantflow.local" if author else None
            )
        
        return change_request
    
    def delete_change_request(
        self,
        change_id: str,
        author: Optional[str] = None
    ) -> bool:
        """
        Delete a change request.
        
        Args:
            change_id: Change request ID
            author: Author name for git commit
            
        Returns:
            True if deleted successfully, False if not found
        """
        file_path = self._get_file_path(change_id)
        if not file_path.exists():
            return False
        
        file_path.unlink()
        
        # Git commit
        if self.git_repo:
            commit_msg = f"Delete change request {change_id}"
            self.git_repo.commit_file(
                file_path,
                commit_msg,
                author_name=author,
                author_email=f"{author}@compliantflow.local" if author else None
            )
        
        return True
