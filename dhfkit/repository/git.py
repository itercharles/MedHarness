"""Git integration for version control."""

import sys
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
            print(f"Warning: {repo_path} is not a Git repository", file=sys.stderr)

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
        """Commit a file change."""
        if not self.repo:
            return False

        try:
            relative_path = file_path.relative_to(self.repo.working_dir)
            self.repo.index.add([str(relative_path)])

            if not self.repo.index.diff("HEAD"):
                print(f"No changes to commit for {relative_path}", file=sys.stderr)
                return False

            commit_kwargs = {'message': message}

            if author_name and author_email:
                from git import Actor
                commit_kwargs['author'] = Actor(author_name, author_email)

            self.repo.index.commit(**commit_kwargs)
            print(f"Committed: {message}", file=sys.stderr)
            return True

        except Exception as e:
            print(f"Git commit failed: {e}", file=sys.stderr)
            return False

    def commit_item_change(
        self,
        item_uid: str,
        file_path: Path,
        action: str = "updated",
        author: Optional[str] = None,
        cr_id: Optional[str] = None
    ) -> bool:
        """Commit an item change with auto-generated message."""
        if not self.auto_commit or not self.repo:
            return False

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if cr_id:
            message = f"[{cr_id}] {action.capitalize()} {item_uid}\n\nChange Request: {cr_id}\nTimestamp: {timestamp}"
        else:
            message = f"{action.capitalize()} {item_uid} [{timestamp}]"

        author_email = f"{author}@medharness.local" if author else None

        return self.commit_file(
            file_path,
            message,
            author_name=author,
            author_email=author_email
        )

    def get_file_history(self, file_path: Path, max_count: int = 10) -> list:
        """Get commit history for a file."""
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
            print(f"Failed to get file history: {e}", file=sys.stderr)
            return []
