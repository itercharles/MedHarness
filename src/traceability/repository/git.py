"""Git integration for version control."""

from git import Repo, InvalidGitRepositoryError
from pathlib import Path
from typing import Optional
from datetime import datetime


class GitRepository:
    """
    Git integration for auto-committing changes.
    
    Provides automatic version control for item changes.
    """
    
    def __init__(self, repo_path: Path, auto_commit: bool = False):
        """
        Initialize Git repository.
        
        Args:
            repo_path: Path to repository root
            auto_commit: Whether to auto-commit changes
        """
        self.repo_path = repo_path
        self.auto_commit = auto_commit
        self.repo: Optional[Repo] = None
        
        try:
            self.repo = Repo(repo_path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            print(f"Warning: {repo_path} is not a Git repository")
    
    def is_available(self) -> bool:
        """Check if Git is available."""
        return self.repo is not None
    
    def commit_file(
        self,
        file_path: Path,
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None
    ) -> bool:
        """
        Commit a file change.
        
        Args:
            file_path: Path to file to commit
            message: Commit message
            author_name: Author name (optional)
            author_email: Author email (optional)
            
        Returns:
            True if committed successfully
        """
        if not self.repo:
            return False
        
        try:
            # Get relative path
            relative_path = file_path.relative_to(self.repo.working_dir)
            
            # Stage the file
            self.repo.index.add([str(relative_path)])
            
            # Check if there are changes to commit
            if not self.repo.index.diff("HEAD"):
                print(f"No changes to commit for {relative_path}")
                return False
            
            # Prepare commit kwargs
            commit_kwargs = {'message': message}
            
            if author_name and author_email:
                from git import Actor
                commit_kwargs['author'] = Actor(author_name, author_email)
            
            # Commit
            self.repo.index.commit(**commit_kwargs)
            print(f"Committed: {message}")
            return True
            
        except Exception as e:
            print(f"Git commit failed: {e}")
            return False
    
    def commit_item_change(
        self,
        item_uid: str,
        file_path: Path,
        action: str = "updated",
        author: Optional[str] = None
    ) -> bool:
        """
        Commit an item change with auto-generated message.
        
        Args:
            item_uid: Item UID
            file_path: Path to item file
            action: Action performed (created, updated, deleted)
            author: Author name
            
        Returns:
            True if committed successfully
        """
        if not self.auto_commit or not self.repo:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"{action.capitalize()} {item_uid} [{timestamp}]"
        
        author_email = f"{author}@compliantflow.local" if author else None
        
        return self.commit_file(
            file_path,
            message,
            author_name=author,
            author_email=author_email
        )
    
    def get_file_history(self, file_path: Path, max_count: int = 10) -> list:
        """
        Get commit history for a file.
        
        Args:
            file_path: Path to file
            max_count: Maximum number of commits to return
            
        Returns:
            List of commit information
        """
        if not self.repo:
            return []
        
        try:
            relative_path = file_path.relative_to(self.repo.working_dir)
            commits = list(self.repo.iter_commits(paths=str(relative_path), max_count=max_count))
            
            history = []
            for commit in commits:
                history.append({
                    "sha": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                })
            
            return history
            
        except Exception as e:
            print(f"Failed to get file history: {e}")
            return []
