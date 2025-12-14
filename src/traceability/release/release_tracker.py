"""Release tracker for managing release lifecycle and storage."""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import yaml

from ..models.release import Release, ReleaseStatus
from ..repository.git import GitRepository


class ReleaseTracker:
    """
    Manages release lifecycle and storage.
    
    Releases are stored as YAML files in DHF/releases/ directory.
    """
    
    def __init__(self, dhf_root: Path, git_repo: Optional[GitRepository] = None):
        """
        Initialize release tracker.
        
        Args:
            dhf_root: Path to DHF root directory
            git_repo: Optional GitRepository for version control
        """
        self.dhf_root = Path(dhf_root)
        self.releases_dir = self.dhf_root / "releases"
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        self.git_repo = git_repo
    
    def create_release(
        self,
        data: Dict[str, Any],
        author: Optional[str] = None
    ) -> Release:
        """
        Create a new release.
        
        Args:
            data: Release data (must include version)
            author: Author for git commit
            
        Returns:
            Created Release object
        """
        # Set created_date if not provided
        if 'created_date' not in data:
            data['created_date'] = datetime.now()
        
        # Validate and create release
        release = Release.model_validate(data)
        
        # Save to file
        file_path = self.releases_dir / f"{release.version}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(
                release.model_dump(mode='json'),
                f,
                default_flow_style=False,
                sort_keys=False
            )
        
        # Git commit
        if self.git_repo:
            self.git_repo.commit_file(
                file_path,
                f"Created release {release.version}",
                author_name=author or release.created_by,
                author_email=f"{author or release.created_by}@compliantflow.local"
            )
        
        return release
    
    def get_release(self, version: str) -> Optional[Release]:
        """
        Get release by version.
        
        Args:
            version: Release version
            
        Returns:
            Release object or None
        """
        file_path = self.releases_dir / f"{version}.yaml"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            return Release.model_validate(data)
        except Exception as e:
            print(f"Error loading release {version}: {e}")
            return None
    
    def list_releases(
        self,
        status: Optional[ReleaseStatus] = None
    ) -> List[Release]:
        """
        List releases with optional filters.
        
        Args:
            status: Filter by status
            
        Returns:
            List of Release objects
        """
        releases = []
        
        for file_path in self.releases_dir.glob("*.yaml"):
            try:
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                release = Release.model_validate(data)
                
                # Apply filters
                if status and release.status != status:
                    continue
                
                releases.append(release)
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}")
                continue
        
        # Sort by version (most recent first)
        releases.sort(key=lambda x: x.version, reverse=True)
        
        return releases
    
    def update_release(
        self,
        version: str,
        updates: Dict[str, Any],
        author: Optional[str] = None
    ) -> Optional[Release]:
        """
        Update an existing release.
        
        Args:
            version: Release version
            updates: Dictionary of fields to update
            author: Author for git commit
            
        Returns:
            Updated Release object or None
        """
        release = self.get_release(version)
        if not release:
            return None
        
        # Update fields
        current_data = release.model_dump()
        current_data.update(updates)
        
        # Validate updated release
        updated_release = Release.model_validate(current_data)
        
        # Save to file
        file_path = self.releases_dir / f"{version}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(
                updated_release.model_dump(mode='json'),
                f,
                default_flow_style=False,
                sort_keys=False
            )
        
        # Git commit
        if self.git_repo:
            self.git_repo.commit_file(
                file_path,
                f"Updated release {version}",
                author_name=author,
                author_email=f"{author}@compliantflow.local" if author else None
            )
        
        return updated_release
