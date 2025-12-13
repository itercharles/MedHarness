"""Checklist engine for review guidance."""

from pathlib import Path
from typing import Optional, List
import yaml
from ..models.review import ReviewChecklist, GuidancePoint


class ChecklistEngine:
    """
    Manages review checklists.
    
    Checklists provide optional guidance for reviewers.
    """
    
    def __init__(self, config_path: Path):
        """
        Initialize checklist engine.
        
        Args:
            config_path: Path to review_checklists.yaml
        """
        self.config_path = Path(config_path)
        self.checklists: List[ReviewChecklist] = []
        self._load_checklists()
    
    def _load_checklists(self):
        """Load checklists from configuration file."""
        if not self.config_path.exists():
            print(f"Warning: Checklist config not found at {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data or 'checklists' not in data:
                return
            
            for checklist_data in data['checklists']:
                # Convert guidance_points to GuidancePoint objects
                guidance_points = []
                for point_data in checklist_data.get('guidance_points', []):
                    guidance_points.append(GuidancePoint(**point_data))
                
                checklist = ReviewChecklist(
                    id=checklist_data['id'],
                    name=checklist_data['name'],
                    description=checklist_data.get('description'),
                    applicable_to=checklist_data.get('applicable_to', []),
                    guidance_points=guidance_points
                )
                self.checklists.append(checklist)
        
        except Exception as e:
            print(f"Error loading checklists: {e}")
    
    def get_checklist(self, checklist_id: str) -> Optional[ReviewChecklist]:
        """
        Get checklist by ID.
        
        Args:
            checklist_id: Checklist ID
            
        Returns:
            ReviewChecklist or None
        """
        for checklist in self.checklists:
            if checklist.id == checklist_id:
                return checklist
        return None
    
    def get_applicable_checklists(self, doc_type: str) -> List[ReviewChecklist]:
        """
        Get checklists applicable to a document type.
        
        Args:
            doc_type: Document type code (e.g., 'CRS', 'SYS', 'SDS')
            
        Returns:
            List of applicable ReviewChecklists
        """
        applicable = []
        for checklist in self.checklists:
            if doc_type in checklist.applicable_to:
                applicable.append(checklist)
        return applicable
    
    def list_all_checklists(self) -> List[ReviewChecklist]:
        """
        Get all available checklists.
        
        Returns:
            List of all ReviewChecklists
        """
        return self.checklists.copy()
