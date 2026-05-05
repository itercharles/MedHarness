"""CI artifact fetchers for DHF test result integration.

Fetches JUnit XML artifacts from GitHub Actions, GitLab CI, or Jenkins runs
and parses them into ExecutionResult objects using the existing junit_parser
module.

Each fetcher exposes a ``fetch(run_id, commit_sha) -> dict`` interface and a
``from_environment(dhf_path)`` constructor that reads credentials from env vars:

- GitHub Actions: ``GITHUB_TOKEN``
- GitLab CI:      ``GITLAB_TOKEN``, ``GITLAB_URL`` (default: https://gitlab.com),
                  ``GITLAB_PROJECT_ID``
- Jenkins:        ``JENKINS_TOKEN``, ``JENKINS_URL``, ``JENKINS_USER``
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

from dhfkit.junit_parser import ExecutionResult, parse_junit_xml

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


class GitLabArtifactFetcher:
    """Fetch test results from GitLab CI job artifacts.

    Reads ``GITLAB_TOKEN``, ``GITLAB_URL`` (default: https://gitlab.com),
    and ``GITLAB_PROJECT_ID`` from the environment.

    Usage::

        fetcher = GitLabArtifactFetcher.from_environment(dhf_path)
        result = fetcher.fetch(run_id="12345")
        # result = {
        #     "results": List[ExecutionResult],
        #     "run_id":  "12345",
        #     "run_url": "https://gitlab.com/<project>/-/pipelines/12345",
        # }

    ``run_id`` is a GitLab **pipeline** ID.  All jobs in the pipeline whose
    artifacts contain ``*.xml`` files are downloaded and parsed.
    """

    def __init__(self, base_url: str, project_id: str, token: str, dhf_path: Path):
        self._base_url = base_url.rstrip("/")
        self._project_id = project_id
        self._token = token
        self._dhf_path = dhf_path

    @classmethod
    def from_environment(cls, dhf_path: Path) -> "GitLabArtifactFetcher":
        token = os.environ.get("GITLAB_TOKEN", "")
        base_url = os.environ.get("GITLAB_URL", "https://gitlab.com")
        project_id = os.environ.get("GITLAB_PROJECT_ID", "")
        if not project_id:
            project_id = cls._detect_project_id(base_url, dhf_path)
        return cls(base_url=base_url, project_id=project_id, token=token, dhf_path=dhf_path)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def fetch(self, run_id: str = "", commit_sha: str = "") -> dict:
        """Fetch all test results for a pipeline or commit.

        Args:
            run_id: GitLab pipeline ID (takes priority).
            commit_sha: Commit SHA to find the latest pipeline for.
                If neither is provided, auto-detects HEAD SHA.

        Returns:
            ``{"results": List[ExecutionResult], "run_id": str, "run_url": str}``

        Raises:
            ValueError: If credentials are missing or no pipeline is found.
        """
        if not self._token:
            raise ValueError(
                "GITLAB_TOKEN environment variable is not set. "
                "Export it before running 'test pull --provider gitlab'."
            )
        if not self._project_id:
            raise ValueError(
                "Could not detect GitLab project ID. "
                "Set GITLAB_PROJECT_ID or ensure the git remote points to a GitLab instance."
            )

        if run_id:
            pipeline_id = run_id
        else:
            sha = commit_sha or self._get_current_commit_sha()
            if not sha:
                raise ValueError(
                    "No run_id or commit_sha provided and could not detect HEAD SHA."
                )
            pipeline_id = self._find_latest_pipeline_id(sha)

        run_url = f"{self._base_url}/{self._project_id}/-/pipelines/{pipeline_id}"
        results = self._fetch_by_pipeline_id(pipeline_id)
        return {"results": results, "run_id": pipeline_id, "run_url": run_url}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_latest_pipeline_id(self, commit_sha: str) -> str:
        data = self._api_get(
            f"/api/v4/projects/{self._project_id}/pipelines"
            f"?sha={commit_sha}&status=success&order_by=id&sort=desc&per_page=1"
        )
        if not data:
            raise ValueError(
                f"No successful GitLab pipeline found for commit {commit_sha[:8]}."
            )
        return str(data[0]["id"])

    def _fetch_by_pipeline_id(self, pipeline_id: str) -> List[ExecutionResult]:
        jobs = self._api_get(
            f"/api/v4/projects/{self._project_id}/pipelines/{pipeline_id}/jobs"
        )
        results: List[ExecutionResult] = []
        for job in jobs:
            job_id = str(job["id"])
            artifact_url = (
                f"{self._base_url}/api/v4/projects/{self._project_id}"
                f"/jobs/{job_id}/artifacts"
            )
            try:
                raw = self._download_raw(artifact_url)
            except Exception:
                continue
            results.extend(self._parse_zip(raw))
        return results

    def _parse_zip(self, raw: bytes) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            zip_path.write_bytes(raw)
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    for name in zf.namelist():
                        if name.endswith(".xml"):
                            zf.extract(name, tmp)
                            results.extend(parse_junit_xml(Path(tmp) / name))
            except zipfile.BadZipFile:
                pass
        return results

    def _api_get(self, path: str) -> object:
        url = f"{self._base_url}{path}" if path.startswith("/") else path
        req = Request(url, headers={"PRIVATE-TOKEN": self._token})
        with urlopen(req) as resp:
            return json.loads(resp.read())

    def _download_raw(self, url: str) -> bytes:
        req = Request(url, headers={"PRIVATE-TOKEN": self._token})
        with urlopen(req) as resp:
            return resp.read()

    @staticmethod
    def _detect_project_id(base_url: str, dhf_path: Path) -> str:
        """Parse namespace/project from the git remote URL for this GitLab host."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, cwd=dhf_path, timeout=5,
            )
            url = result.stdout.strip()
            host = re.sub(r"^https?://", "", base_url).rstrip("/")
            pattern = rf"{re.escape(host)}[:/]([^/]+/[^/]+?)(?:\.git)?$"
            m = re.search(pattern, url)
            if m:
                return m.group(1)
        except Exception:
            pass
        return os.environ.get("CI_PROJECT_ID", "")

    def _get_current_commit_sha(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self._dhf_path, timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            return ""


class JenkinsArtifactFetcher:
    """Fetch test results from Jenkins build artifacts.

    Reads ``JENKINS_URL``, ``JENKINS_USER``, ``JENKINS_TOKEN``, and
    ``JENKINS_JOB_NAME`` from the environment.

    Usage::

        fetcher = JenkinsArtifactFetcher.from_environment(dhf_path)
        result = fetcher.fetch(run_id="42")
        # result = {
        #     "results": List[ExecutionResult],
        #     "run_id":  "42",
        #     "run_url": "https://jenkins.example.com/job/<job>/42/",
        # }

    ``run_id`` is a Jenkins **build number**.  All XML files found in the
    build's artifact tree are downloaded and parsed.
    """

    def __init__(self, jenkins_url: str, job_name: str, user: str, token: str, dhf_path: Path):
        self._jenkins_url = jenkins_url.rstrip("/")
        self._job_name = job_name
        self._user = user
        self._token = token
        self._dhf_path = dhf_path

    @classmethod
    def from_environment(cls, dhf_path: Path) -> "JenkinsArtifactFetcher":
        jenkins_url = os.environ.get("JENKINS_URL", "")
        job_name = os.environ.get("JENKINS_JOB_NAME", "")
        user = os.environ.get("JENKINS_USER", "")
        token = os.environ.get("JENKINS_TOKEN", "")
        return cls(jenkins_url=jenkins_url, job_name=job_name, user=user, token=token, dhf_path=dhf_path)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def fetch(self, run_id: str = "", commit_sha: str = "") -> dict:  # noqa: ARG002
        """Fetch all test results for a Jenkins build.

        Args:
            run_id: Jenkins build number (required — Jenkins has no reliable
                commit-to-build lookup without plugins).
            commit_sha: Ignored for Jenkins; included for interface parity.

        Returns:
            ``{"results": List[ExecutionResult], "run_id": str, "run_url": str}``

        Raises:
            ValueError: If credentials or URL are missing, or run_id is empty.
        """
        if not self._jenkins_url:
            raise ValueError(
                "JENKINS_URL environment variable is not set. "
                "Export it before running 'test pull --provider jenkins'."
            )
        if not self._token:
            raise ValueError(
                "JENKINS_TOKEN environment variable is not set. "
                "Export it before running 'test pull --provider jenkins'."
            )
        if not self._job_name:
            raise ValueError(
                "JENKINS_JOB_NAME environment variable is not set."
            )
        if not run_id:
            raise ValueError(
                "Jenkins requires an explicit --run-id (build number). "
                "Jenkins has no reliable commit-to-build lookup without plugins."
            )

        run_url = f"{self._jenkins_url}/job/{self._job_name}/{run_id}/"
        results = self._fetch_build_artifacts(run_id)
        return {"results": results, "run_id": run_id, "run_url": run_url}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_build_artifacts(self, build_number: str) -> List[ExecutionResult]:
        """Download all XML artifacts from the build's artifact tree."""
        artifact_list_url = (
            f"{self._jenkins_url}/job/{self._job_name}/{build_number}"
            f"/api/json?tree=artifacts[fileName,relativePath]"
        )
        data = self._api_get(artifact_list_url)
        artifacts = data.get("artifacts", [])
        results: List[ExecutionResult] = []
        for artifact in artifacts:
            if not artifact.get("fileName", "").endswith(".xml"):
                continue
            rel_path = artifact["relativePath"]
            download_url = (
                f"{self._jenkins_url}/job/{self._job_name}/{build_number}"
                f"/artifact/{rel_path}"
            )
            try:
                raw = self._download_raw(download_url)
            except Exception:
                continue
            with tempfile.TemporaryDirectory() as tmp:
                xml_path = Path(tmp) / artifact["fileName"]
                xml_path.write_bytes(raw)
                results.extend(parse_junit_xml(xml_path))
        return results

    def _api_get(self, url: str) -> dict:
        req = Request(url, headers=self._auth_headers())
        with urlopen(req) as resp:
            return json.loads(resp.read())

    def _download_raw(self, url: str) -> bytes:
        req = Request(url, headers=self._auth_headers())
        with urlopen(req) as resp:
            return resp.read()

    def _auth_headers(self) -> dict:
        import base64
        credentials = base64.b64encode(f"{self._user}:{self._token}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}
