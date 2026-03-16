"""GitHub Actions artifact fetcher for DHF test result integration.

Fetches JUnit XML artifacts from GitHub Actions runs and parses them
into ExecutionResult objects using the existing junit_parser module.

All GitHub API details are encapsulated here; callers only see
ExecutionResult lists. The fetcher is constructed via
``GitHubArtifactFetcher.from_environment(dhf_path)`` which reads
``GITHUB_TOKEN`` and auto-detects the repository from the git remote.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import List
import urllib.error
import urllib.request
from urllib.request import Request, urlopen

from utils.junit_parser import ExecutionResult, parse_junit_xml

_GITHUB_API = "https://api.github.com"

# Artifact names uploaded by the CI pipeline
_ARTIFACT_NAMES = {"unit-test-results", "sys-test-results", "crs-test-results"}


class GitHubArtifactFetcher:
    """Fetch test results from GitHub Actions artifacts.

    Usage::

        fetcher = GitHubArtifactFetcher.from_environment(dhf_path)
        result = fetcher.fetch(run_id="12345")
        # result = {
        #     "results": List[ExecutionResult],
        #     "run_id":  "12345",
        #     "run_url": "https://github.com/owner/repo/actions/runs/12345",
        # }
    """

    def __init__(self, repo: str, token: str, dhf_path: Path):
        self._repo = repo          # "owner/repo"
        self._token = token
        self._dhf_path = dhf_path

    @classmethod
    def from_environment(cls, dhf_path: Path) -> "GitHubArtifactFetcher":
        """Construct using GITHUB_TOKEN env var and git remote auto-detection."""
        token = os.environ.get("GITHUB_TOKEN", "")
        repo = cls._detect_repo(dhf_path)
        return cls(repo=repo, token=token, dhf_path=dhf_path)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def fetch(self, run_id: str = "", commit_sha: str = "") -> dict:
        """Fetch all test results for a run or commit.

        Args:
            run_id: Specific GitHub Actions run ID (takes priority).
            commit_sha: Commit SHA to find the latest completed run for.
                If neither is provided, auto-detects HEAD SHA.

        Returns:
            ``{"results": List[ExecutionResult], "run_id": str, "run_url": str}``

        Raises:
            ValueError: If GITHUB_TOKEN is unset, repo cannot be detected,
                or no completed run is found for the commit.
        """
        if not self._repo:
            raise ValueError(
                "Could not detect GitHub repository from git remote. "
                "Ensure 'origin' remote points to github.com, "
                "or set GITHUB_REPOSITORY env var to 'owner/repo'."
            )
        if not self._token:
            raise ValueError(
                "GITHUB_TOKEN environment variable is not set. "
                "Export it before running 'test pull'."
            )

        if run_id:
            actual_run_id = run_id
        else:
            sha = commit_sha or self._get_current_commit_sha()
            if not sha:
                raise ValueError(
                    "No run_id or commit_sha provided and could not detect HEAD SHA."
                )
            actual_run_id = self._find_latest_run_id(sha)

        run_url = f"https://github.com/{self._repo}/actions/runs/{actual_run_id}"
        results = self._fetch_by_run_id(actual_run_id)
        return {"results": results, "run_id": actual_run_id, "run_url": run_url}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_latest_run_id(self, commit_sha: str) -> str:
        """Return the most recent completed workflow run ID for the given commit."""
        data = self._api_get(
            f"/repos/{self._repo}/actions/runs"
            f"?head_sha={commit_sha}&status=completed"
        )
        runs = data.get("workflow_runs", [])
        if not runs:
            raise ValueError(
                f"No completed CI runs found for commit {commit_sha[:8]}. "
                "The CI may still be running, or the commit has no associated run."
            )
        return str(runs[0]["id"])

    def _fetch_by_run_id(self, run_id: str) -> List[ExecutionResult]:
        data = self._api_get(
            f"/repos/{self._repo}/actions/runs/{run_id}/artifacts"
        )
        results: List[ExecutionResult] = []
        for artifact in data.get("artifacts", []):
            if artifact["name"] not in _ARTIFACT_NAMES:
                continue
            results.extend(self._download_and_parse(artifact["archive_download_url"]))
        return results

    def _download_and_parse(self, download_url: str) -> List[ExecutionResult]:
        raw = self._api_get_raw(download_url)
        results: List[ExecutionResult] = []
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            zip_path.write_bytes(raw)
            with zipfile.ZipFile(zip_path) as zf:
                for name in zf.namelist():
                    if name.endswith(".xml"):
                        zf.extract(name, tmp)
                        results.extend(parse_junit_xml(Path(tmp) / name))
        return results

    def _api_get(self, path: str) -> dict:
        url = f"{_GITHUB_API}{path}"
        req = Request(url, headers=self._auth_headers())
        with urlopen(req) as resp:
            return json.loads(resp.read())

    def _api_get_raw(self, url: str) -> bytes:
        """Download raw bytes from a GitHub API URL that redirects to storage.

        GitHub artifact downloads redirect to Azure Blob Storage (or similar)
        using a pre-signed URL.  Python's default urllib handler forwards the
        Authorization header to the redirect target, which causes the storage
        service to return 401 (conflicting auth).  We handle the redirect
        manually so the auth header is only sent to api.github.com.
        """
        # Step 1: authenticated request to GitHub API — get the redirect URL.
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
                return None  # do not follow; raise HTTPError instead

        no_follow = urllib.request.build_opener(_NoRedirect())
        req = Request(url, headers=self._auth_headers())
        try:
            with no_follow.open(req) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (301, 302, 303, 307, 308):
                raise
            redirect_url = exc.headers.get("Location")
            if not redirect_url:
                raise ValueError(f"Redirect from {url} had no Location header") from exc

        # Step 2: unauthenticated download from the pre-signed storage URL.
        with urlopen(redirect_url) as resp:
            return resp.read()

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @staticmethod
    def _detect_repo(dhf_path: Path) -> str:
        """Parse 'owner/repo' from the git remote URL."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, cwd=dhf_path, timeout=5,
            )
            url = result.stdout.strip()
            m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
            if m:
                return m.group(1)
        except Exception:
            pass
        # Fallback: GITHUB_REPOSITORY is set in GitHub Actions environments
        return os.environ.get("GITHUB_REPOSITORY", "")

    def _get_current_commit_sha(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self._dhf_path, timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            return ""
