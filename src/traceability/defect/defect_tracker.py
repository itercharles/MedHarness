"""Defect tracker for managing defect lifecycle and storage."""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import yaml

from ..models.defect import Defect, DefectStatus, DefectSeverity
from ..repository.git import GitRepository


class DefectTracker:
    """
    Manages defect lifecycle and storage.
    
    Defects are stored as YAML files in DHF/defects/ directory.
    """
    
    def __init__(self, dhf_root: Path, git_repo: Optional[GitRepository] = None):
        """
        Initialize defect tracker.
        
        Args:
            dhf_root: Path to DHF root directory
            git_repo: Optional GitRepository for version control
        """
        self.dhf_root = Path(dhf_root)
        self.defects_dir = self.dhf_root / "defects"
        self.defects_dir.mkdir(parents=True, exist_ok=True)
        self.git_repo = git_repo
    
    def _get_next_id(self) -> str:
        """Generate next defect ID."""
        existing_defects = list(self.defects_dir.glob("DEF-*.yaml"))
        if not existing_defects:
            return "DEF-001"
        
        # Extract numbers from existing IDs
        numbers = []
        for file in existing_defects:
            try:
                num = int(file.stem.split('-')[1])
                numbers.append(num)
            except (IndexError, ValueError):
                continue
        
        next_num = max(numbers) + 1 if numbers else 1
        return f"DEF-{next_num:03d}"
    
    def create_defect(
        self,
        data: Dict[str, Any],
        author: Optional[str] = None
    ) -> Defect:
        """
        Create a new defect.
        
        Args:
            data: Defect data (without ID)
            author: Author for git commit
            
        Returns:
            Created Defect object
        """
        # Generate ID if not provided
        if 'id' not in data:
            data['id'] = self._get_next_id()
        
        # Set reported_date if not provided
        if 'reported_date' not in data:
            data['reported_date'] = datetime.now()
        
        # Validate and create defect
        defect = Defect.model_validate(data)
        
        # Save to file
        file_path = self.defects_dir / f"{defect.id}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(
                defect.model_dump(mode='json'),
                f,
                default_flow_style=False,
                sort_keys=False
            )
        
        # Git commit
        if self.git_repo:
            self.git_repo.commit_file(
                file_path,
                f"Created defect {defect.id}",
                author_name=author or defect.reported_by,
                author_email=f"{author or defect.reported_by}@compliantflow.local"
            )
        
        return defect
    
    def get_defect(self, defect_id: str) -> Optional[Defect]:
        """
        Get defect by ID.
        
        Args:
            defect_id: Defect ID
            
        Returns:
            Defect object or None
        """
        file_path = self.defects_dir / f"{defect_id}.yaml"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            return Defect.model_validate(data)
        except Exception as e:
            print(f"Error loading defect {defect_id}: {e}")
            return None
    
    def list_defects(
        self,
        status: Optional[DefectStatus] = None,
        severity: Optional[DefectSeverity] = None,
        assigned_to: Optional[str] = None
    ) -> List[Defect]:
        """
        List defects with optional filters.
        
        Args:
            status: Filter by status
            severity: Filter by severity
            assigned_to: Filter by assigned person
            
        Returns:
            List of Defect objects
        """
        defects = []
        
        for file_path in self.defects_dir.glob("DEF-*.yaml"):
            try:
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                defect = Defect.model_validate(data)
                
                # Apply filters
                if status and defect.status != status:
                    continue
                if severity and defect.severity != severity:
                    continue
                if assigned_to and defect.assigned_to != assigned_to:
                    continue
                
                defects.append(defect)
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}")
                continue
        
        # Sort by ID (most recent first)
        defects.sort(key=lambda x: x.id, reverse=True)
        
        return defects
    
    def update_defect(
        self,
        defect_id: str,
        updates: Dict[str, Any],
        author: Optional[str] = None
    ) -> Optional[Defect]:
        """
        Update an existing defect.
        
        Args:
            defect_id: Defect ID
            updates: Dictionary of fields to update
            author: Author for git commit
            
        Returns:
            Updated Defect object or None
        """
        defect = self.get_defect(defect_id)
        if not defect:
            return None
        
        # Update fields
        current_data = defect.model_dump()
        current_data.update(updates)
        
        # Validate updated defect
        updated_defect = Defect.model_validate(current_data)
        
        # Save to file
        file_path = self.defects_dir / f"{defect_id}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(
                updated_defect.model_dump(mode='json'),
                f,
                default_flow_style=False,
                sort_keys=False
            )
        
        # Git commit
        if self.git_repo:
            self.git_repo.commit_file(
                file_path,
                f"Updated defect {defect_id}",
                author_name=author,
                author_email=f"{author}@compliantflow.local" if author else None
            )
        
        return updated_defect
    
    def delete_defect(
        self,
        defect_id: str,
        author: Optional[str] = None
    ) -> bool:
        """
        Delete a defect.
        
        Args:
            defect_id: Defect ID
            author: Author for git commit
            
        Returns:
            True if deleted successfully
        """
        file_path = self.defects_dir / f"{defect_id}.yaml"
        if not file_path.exists():
            return False
        
        file_path.unlink()
        
        # Git commit
        if self.git_repo:
            self.git_repo.commit_file(
                file_path,
                f"Deleted defect {defect_id}",
                author_name=author,
                author_email=f"{author}@compliantflow.local" if author else None
            )
        
        return True
