"""Reading the repository a DHF lives in.

Read-only by design. The DHF is committed by whatever workflow carries the
change, so who changed an item is the author of that commit; `dhfkit` writing
its own commits would fight the change-request branch it is running inside.
"""

import sys
from git import Repo, InvalidGitRepositoryError
from pathlib import Path
from typing import Optional


class GitRepository:
    """Read the history of the repository holding a DHF."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.repo: Optional[Repo] = None

        try:
            self.repo = Repo(repo_path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            print(f"Warning: {repo_path} is not a Git repository", file=sys.stderr)

    def is_available(self) -> bool:
        """Check if Git is available."""
        return self.repo is not None

    def item_ids_ever_added(self, items_dir: Path) -> set[str]:
        """Every item ID this repository has ever held, deleted ones included.

        An ID that once meant one requirement must not later mean another. The
        next-ID calculation looked only at items present, so deleting SRS-003
        and creating a new item produced SRS-003 again — while git still held
        the original, and every CR, approval record and `dhf_links` marker
        pointing at SRS-003 silently retargeted.

        Returns an empty set when there is no repository, so a DHF outside git
        behaves as it did.
        """
        if not self.is_available():
            return set()
        try:
            rel = items_dir.resolve().relative_to(Path(self.repo.working_tree_dir).resolve())
        except (ValueError, TypeError):
            return set()
        try:
            output = self.repo.git.log(
                "--all", "--pretty=format:", "--name-only",
                "--diff-filter=A", "--", str(rel),
            )
        except Exception:  # noqa: BLE001
            # A shallow clone or an unborn HEAD: fall back to what is present
            # rather than failing item creation.
            return set()
        return {
            Path(line).stem
            for line in output.splitlines()
            if line.strip().endswith((".yaml", ".yml"))
        }

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
                    # Full hash: an approval record identifies the state it
                    # accepted by its commit, and a truncated hash is not an
                    # identifier an audit can rely on.
                    "sha": commit.hexsha,
                    "short_sha": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                })

            return history

        except Exception as e:
            print(f"Failed to get file history: {e}", file=sys.stderr)
            return []
