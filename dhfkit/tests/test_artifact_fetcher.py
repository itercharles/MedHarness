"""Tests for the CI artifact fetchers.

This module had no test file at all — 250 statements reachable only through
`test pull`, which needs a live CI provider. A code review raised four
suspected defects in the GitLab path; these tests exist to settle them against
a faked ``urlopen`` rather than by reading.

The fake records every requested URL, so assertions can be made about the
requests themselves, not only about the parsed result.
"""

from __future__ import annotations

import io
import json
import urllib.error
import zipfile
from pathlib import Path

import pytest

from dhfkit.artifact_fetcher import (
    GitHubArtifactFetcher,
    GitLabArtifactFetcher,
    JenkinsArtifactFetcher,
)

# parse_junit_xml skips any testcase without a recognisable TC ID, so the
# fixture carries the medharness.* properties the pytest plugin emits.
_JUNIT_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="2" failures="1">
    <testcase classname="t" name="test_ok" time="0.01">
      <properties>
        <property name="medharness.id" value="TC-SRS-001"/>
        <property name="medharness.links" value="SRS-001"/>
      </properties>
    </testcase>
    <testcase classname="t" name="test_bad" time="0.02">
      <properties>
        <property name="medharness.id" value="TC-SRS-002"/>
        <property name="medharness.links" value="SRS-002"/>
      </properties>
      <failure message="boom">assert False</failure>
    </testcase>
  </testsuite>
</testsuites>
"""


def _junit_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("results.xml", _JUNIT_XML)
    return buf.getvalue()


class FakeHTTP:
    """Records requested URLs and serves canned responses.

    Routes are matched by substring, longest first, so a specific path wins over
    a general one regardless of insertion order.
    """

    def __init__(self, routes: dict[str, object], errors: dict[str, int] | None = None):
        self.routes = routes
        self.errors = errors or {}
        self.urls: list[str] = []

    def __call__(self, req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        self.urls.append(url)

        for fragment, code in self.errors.items():
            if fragment in url:
                raise urllib.error.HTTPError(url, code, "denied", {}, None)

        for fragment in sorted(self.routes, key=len, reverse=True):
            if fragment in url:
                payload = self.routes[fragment]
                body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                return _Response(body)

        raise urllib.error.HTTPError(url, 404, "no route", {}, None)

    # GitHub's artifact download goes through build_opener() rather than
    # urlopen(), to keep the auth header off the redirect target. Standing in
    # for the opener too keeps that path off the network.
    open = __call__

    def install(self, monkeypatch) -> "FakeHTTP":
        monkeypatch.setattr("dhfkit.artifact_fetcher.urlopen", self)
        monkeypatch.setattr(
            "dhfkit.artifact_fetcher.urllib.request.build_opener", lambda *a, **k: self
        )
        return self


class _Response:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return tmp_path


# ---------------------------------------------------------------------------
# GitLab — where the review's findings sit
# ---------------------------------------------------------------------------

def _gitlab(repo: Path, project_id: str = "acme-med/contour-lab") -> GitLabArtifactFetcher:
    return GitLabArtifactFetcher(
        base_url="https://gitlab.com", project_id=project_id,
        token="t", dhf_path=repo,
    )


class TestGitLabProjectPathEncoding:
    """GitLab addresses projects as ``namespace%2Fproject`` in the API path."""

    def test_detected_path_is_url_encoded_in_requests(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({
            "/pipelines?": [{"id": 77}],
            "/pipelines/77/jobs": [],
        })
        http.install(monkeypatch)

        _gitlab(repo).fetch(commit_sha="abc123")

        pipelines_url = next(u for u in http.urls if "/pipelines?" in u)
        assert "acme-med%2Fcontour-lab" in pipelines_url, (
            f"project path was interpolated unencoded: {pipelines_url}"
        )
        assert "projects/acme-med/contour-lab" not in pipelines_url

    def test_numeric_project_id_is_left_alone(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({"/pipelines?": [{"id": 5}], "/jobs": []})
        http.install(monkeypatch)

        _gitlab(repo, project_id="4815").fetch(commit_sha="abc123")

        assert "projects/4815/" in http.urls[0]
        assert "%2F" not in http.urls[0]

    def test_job_artifact_url_is_encoded_too(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({
            "/pipelines?": [{"id": 77}],
            "/pipelines/77/jobs": [{"id": 900}],
            "/jobs/900/artifacts": _junit_zip(),
        })
        http.install(monkeypatch)

        _gitlab(repo).fetch(commit_sha="abc123")

        artifact_url = next(u for u in http.urls if "/artifacts" in u)
        assert "acme-med%2Fcontour-lab" in artifact_url


class TestGitLabPipelineSelection:
    def test_failed_pipelines_are_reachable(self, repo: Path, monkeypatch) -> None:
        """A DHF records FAIL evidence, so a red pipeline must be fetchable.

        Filtering on status=success made failing runs invisible — the exact runs
        whose results the DHF needs to capture.
        """
        http = FakeHTTP({
            "/pipelines?": [{"id": 42, "status": "failed"}],
            "/pipelines/42/jobs": [{"id": 900}],
            "/jobs/900/artifacts": _junit_zip(),
        })
        http.install(monkeypatch)

        result = _gitlab(repo).fetch(commit_sha="deadbeef")

        query = next(u for u in http.urls if "/pipelines?" in u)
        assert "status=success" not in query, (
            "filtering on success makes failing pipelines unfetchable"
        )
        assert result["run_id"] == "42"
        assert len(result["results"]) == 2  # one pass, one failure

    def test_no_pipeline_raises_a_clear_error(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({"/pipelines?": []})
        http.install(monkeypatch)

        with pytest.raises(ValueError, match="pipeline"):
            _gitlab(repo).fetch(commit_sha="deadbeef")


class TestGitLabDownloadFailures:
    def test_denied_artifact_download_is_not_swallowed(self, repo: Path, monkeypatch) -> None:
        """A 403 must not be reported as 'no evidence'.

        The bare `except Exception: continue` turned an auth failure into an
        empty result set, which downstream records as every requirement being
        unverified — a false negative in regulatory evidence.
        """
        http = FakeHTTP(
            routes={
                "/pipelines?": [{"id": 7}],
                "/pipelines/7/jobs": [{"id": 900}],
            },
            errors={"/jobs/900/artifacts": 403},
        )
        http.install(monkeypatch)

        with pytest.raises(Exception) as exc:
            _gitlab(repo).fetch(commit_sha="abc")
        assert "403" in str(exc.value) or "denied" in str(exc.value).lower()

    def test_job_without_artifacts_is_skipped_quietly(self, repo: Path, monkeypatch) -> None:
        """404 on artifacts is normal — most jobs upload nothing."""
        http = FakeHTTP(
            routes={
                "/pipelines?": [{"id": 7}],
                "/pipelines/7/jobs": [{"id": 900}, {"id": 901}],
                "/jobs/901/artifacts": _junit_zip(),
            },
            errors={"/jobs/900/artifacts": 404},
        )
        http.install(monkeypatch)

        result = _gitlab(repo).fetch(commit_sha="abc")
        assert len(result["results"]) == 2


class TestGitLabRunUrl:
    def test_run_url_uses_the_project_path(self, repo: Path, monkeypatch) -> None:
        """run_url is persisted into DHF execution records as the audit trail."""
        http = FakeHTTP({"/pipelines?": [{"id": 77}], "/jobs": []})
        http.install(monkeypatch)

        result = _gitlab(repo).fetch(commit_sha="abc")
        assert result["run_url"] == (
            "https://gitlab.com/acme-med/contour-lab/-/pipelines/77"
        )


class TestGitLabCredentials:
    def test_missing_token_is_reported(self, repo: Path) -> None:
        fetcher = GitLabArtifactFetcher("https://gitlab.com", "1", "", repo)
        with pytest.raises(ValueError, match="GITLAB_TOKEN"):
            fetcher.fetch(run_id="1")

    def test_missing_project_id_is_reported(self, repo: Path) -> None:
        fetcher = GitLabArtifactFetcher("https://gitlab.com", "", "tok", repo)
        with pytest.raises(ValueError, match="project ID"):
            fetcher.fetch(run_id="1")


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

class TestGitHub:
    def _fetcher(self, repo: Path) -> GitHubArtifactFetcher:
        return GitHubArtifactFetcher(repo="acme/contourlab", token="t", dhf_path=repo)

    def test_parses_artifacts_for_a_run(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({
            "/runs/55/artifacts": {"artifacts": [
                {"name": "unit-test-results", "archive_download_url": "https://dl/1"},
            ]},
            "https://dl/1": _junit_zip(),
        })
        http.install(monkeypatch)

        result = self._fetcher(repo).fetch(run_id="55")
        assert result["run_id"] == "55"
        assert len(result["results"]) == 2

    def test_unrecognised_artifact_names_are_ignored(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({
            "/runs/55/artifacts": {"artifacts": [
                {"name": "coverage-html", "archive_download_url": "https://dl/1"},
            ]},
        })
        http.install(monkeypatch)

        assert self._fetcher(repo).fetch(run_id="55")["results"] == []

    def test_completed_runs_include_failures(self, repo: Path, monkeypatch) -> None:
        """GitHub filters on status=completed, so red runs stay reachable."""
        http = FakeHTTP({
            "/actions/runs?": {"workflow_runs": [{"id": 91, "conclusion": "failure"}]},
            "/runs/91/artifacts": {"artifacts": []},
        })
        http.install(monkeypatch)

        result = self._fetcher(repo).fetch(commit_sha="cafe1234")
        assert result["run_id"] == "91"
        assert "status=completed" in http.urls[0]

    def test_no_run_raises_a_clear_error(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({"/actions/runs?": {"workflow_runs": []}})
        http.install(monkeypatch)

        with pytest.raises(ValueError, match="No completed CI runs"):
            self._fetcher(repo).fetch(commit_sha="cafe1234")


# ---------------------------------------------------------------------------
# Jenkins
# ---------------------------------------------------------------------------

class TestJenkins:
    def test_missing_credentials_are_reported(self, repo: Path) -> None:
        fetcher = JenkinsArtifactFetcher(
            jenkins_url="https://ci.example", job_name="dhf",
            user="", token="", dhf_path=repo,
        )
        with pytest.raises(ValueError):
            fetcher.fetch(run_id="12")


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class TestPagination:
    """Provider defaults truncate silently: GitHub lists 30, GitLab 20."""

    def test_gitlab_jobs_listing_requests_a_full_page(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({"/pipelines?": [{"id": 1}], "/jobs": []})
        http.install(monkeypatch)

        _gitlab(repo).fetch(commit_sha="abc")

        jobs_url = next(u for u in http.urls if "/jobs" in u)
        assert "per_page=100" in jobs_url

    def test_github_artifacts_listing_requests_a_full_page(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({"/artifacts": {"artifacts": []}})
        http.install(monkeypatch)

        GitHubArtifactFetcher(repo="acme/cl", token="t", dhf_path=repo).fetch(run_id="9")

        assert "per_page=100" in http.urls[0]

    def test_github_runs_listing_requests_a_full_page(self, repo: Path, monkeypatch) -> None:
        http = FakeHTTP({
            "/actions/runs?": {"workflow_runs": [{"id": 3}]},
            "/runs/3/artifacts": {"artifacts": []},
        })
        http.install(monkeypatch)

        GitHubArtifactFetcher(repo="acme/cl", token="t", dhf_path=repo).fetch(commit_sha="abc")

        assert "per_page=100" in http.urls[0]
