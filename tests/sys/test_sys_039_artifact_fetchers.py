"""
Tests for CR-028: GitLab CI and Jenkins Artifact Fetcher integration.

Verifies that GitLabArtifactFetcher and JenkinsArtifactFetcher raise clear
errors when credentials are missing, and that the --provider CLI flag is
wired correctly into the test pull command.

@links: SYS-007
"""

import io
import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from click.testing import CliRunner
from utils.artifact_fetcher import GitLabArtifactFetcher, JenkinsArtifactFetcher
from utils.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def dhf_str(test_dhf_root):
    return str(test_dhf_root)


# ---------------------------------------------------------------------------
# GitLabArtifactFetcher — unit tests
# ---------------------------------------------------------------------------

class TestGitLabArtifactFetcherCredentialChecks:
    def test_raises_when_token_missing(self, test_dhf_root):
        fetcher = GitLabArtifactFetcher(
            base_url="https://gitlab.com",
            project_id="owner/repo",
            token="",
            dhf_path=test_dhf_root,
        )
        with pytest.raises(ValueError, match="GITLAB_TOKEN"):
            fetcher.fetch(run_id="123")

    def test_raises_when_project_id_missing(self, test_dhf_root):
        fetcher = GitLabArtifactFetcher(
            base_url="https://gitlab.com",
            project_id="",
            token="glpat-fake",
            dhf_path=test_dhf_root,
        )
        with pytest.raises(ValueError, match="project ID"):
            fetcher.fetch(run_id="123")

    def test_raises_when_run_id_and_commit_both_missing(self, test_dhf_root):
        """With no run_id and no HEAD commit detectable (mocked), raises ValueError."""
        fetcher = GitLabArtifactFetcher(
            base_url="https://gitlab.com",
            project_id="owner/repo",
            token="glpat-fake",
            dhf_path=test_dhf_root,
        )
        with patch.object(fetcher, "_get_current_commit_sha", return_value=""), \
             pytest.raises(ValueError, match="No run_id"):
            fetcher.fetch()


class TestGitLabArtifactFetcherHappyPath:
    def _make_zip(self, xml_content: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("results.xml", xml_content)
        return buf.getvalue()

    def test_fetch_by_run_id_returns_results(self, test_dhf_root):
        junit_xml = (
            '<?xml version="1.0"?>'
            '<testsuites><testsuite name="s">'
            '<testcase name="test_TC_001_001_pass">'
            '<properties><property name="compliantflow.id" value="TC-001-001"/></properties>'
            "</testcase>"
            "</testsuite></testsuites>"
        )
        jobs_response = [{"id": 99}]
        zip_bytes = self._make_zip(junit_xml)

        fetcher = GitLabArtifactFetcher(
            base_url="https://gitlab.com",
            project_id="owner/repo",
            token="glpat-fake",
            dhf_path=test_dhf_root,
        )

        with patch.object(fetcher, "_api_get", return_value=jobs_response), \
             patch.object(fetcher, "_download_raw", return_value=zip_bytes):
            result = fetcher.fetch(run_id="42")

        assert result["run_id"] == "42"
        assert "gitlab.com" in result["run_url"]
        assert len(result["results"]) == 1
        assert result["results"][0].id == "TC-001-001"

    def test_jobs_with_no_xml_are_skipped(self, test_dhf_root):
        jobs_response = [{"id": 1}, {"id": 2}]
        fetcher = GitLabArtifactFetcher(
            base_url="https://gitlab.com",
            project_id="owner/repo",
            token="glpat-fake",
            dhf_path=test_dhf_root,
        )
        with patch.object(fetcher, "_api_get", return_value=jobs_response), \
             patch.object(fetcher, "_download_raw", side_effect=Exception("no artifact")):
            result = fetcher.fetch(run_id="10")

        assert result["results"] == []


# ---------------------------------------------------------------------------
# JenkinsArtifactFetcher — unit tests
# ---------------------------------------------------------------------------

class TestJenkinsArtifactFetcherCredentialChecks:
    def test_raises_when_jenkins_url_missing(self, test_dhf_root):
        fetcher = JenkinsArtifactFetcher(
            jenkins_url="",
            job_name="my-job",
            user="admin",
            token="tok",
            dhf_path=test_dhf_root,
        )
        with pytest.raises(ValueError, match="JENKINS_URL"):
            fetcher.fetch(run_id="1")

    def test_raises_when_token_missing(self, test_dhf_root):
        fetcher = JenkinsArtifactFetcher(
            jenkins_url="https://jenkins.example.com",
            job_name="my-job",
            user="admin",
            token="",
            dhf_path=test_dhf_root,
        )
        with pytest.raises(ValueError, match="JENKINS_TOKEN"):
            fetcher.fetch(run_id="1")

    def test_raises_when_job_name_missing(self, test_dhf_root):
        fetcher = JenkinsArtifactFetcher(
            jenkins_url="https://jenkins.example.com",
            job_name="",
            user="admin",
            token="tok",
            dhf_path=test_dhf_root,
        )
        with pytest.raises(ValueError, match="JENKINS_JOB_NAME"):
            fetcher.fetch(run_id="1")

    def test_raises_when_run_id_missing(self, test_dhf_root):
        fetcher = JenkinsArtifactFetcher(
            jenkins_url="https://jenkins.example.com",
            job_name="my-job",
            user="admin",
            token="tok",
            dhf_path=test_dhf_root,
        )
        with pytest.raises(ValueError, match="--run-id"):
            fetcher.fetch()


class TestJenkinsArtifactFetcherHappyPath:
    def test_fetch_by_run_id_returns_results(self, test_dhf_root):
        junit_xml = (
            '<?xml version="1.0"?>'
            '<testsuites><testsuite name="s">'
            '<testcase name="test_TC_002_001_pass">'
            '<properties><property name="compliantflow.id" value="TC-002-001"/></properties>'
            "</testcase>"
            "</testsuite></testsuites>"
        )
        build_api_response = {
            "artifacts": [{"fileName": "results.xml", "relativePath": "results/results.xml"}]
        }
        fetcher = JenkinsArtifactFetcher(
            jenkins_url="https://jenkins.example.com",
            job_name="my-job",
            user="admin",
            token="tok",
            dhf_path=test_dhf_root,
        )
        with patch.object(fetcher, "_api_get", return_value=build_api_response), \
             patch.object(fetcher, "_download_raw", return_value=junit_xml.encode()):
            result = fetcher.fetch(run_id="42")

        assert result["run_id"] == "42"
        assert "jenkins.example.com" in result["run_url"]
        assert len(result["results"]) == 1
        assert result["results"][0].id == "TC-002-001"

    def test_non_xml_artifacts_are_skipped(self, test_dhf_root):
        build_api_response = {
            "artifacts": [
                {"fileName": "binary.tar.gz", "relativePath": "dist/binary.tar.gz"},
                {"fileName": "report.html", "relativePath": "report.html"},
            ]
        }
        fetcher = JenkinsArtifactFetcher(
            jenkins_url="https://jenkins.example.com",
            job_name="my-job",
            user="admin",
            token="tok",
            dhf_path=test_dhf_root,
        )
        with patch.object(fetcher, "_api_get", return_value=build_api_response):
            result = fetcher.fetch(run_id="5")

        assert result["results"] == []


# ---------------------------------------------------------------------------
# CLI --provider flag wiring
# ---------------------------------------------------------------------------

class TestTestPullProviderFlag:
    def test_provider_github_is_default(self, runner, dhf_str, test_dhf_root):
        with patch("utils.local_adapter.GitHubArtifactFetcher") as mock_gh:
            mock_instance = MagicMock()
            mock_instance.fetch.return_value = {"results": [], "run_id": "1", "run_url": "http://x"}
            mock_gh.from_environment.return_value = mock_instance
            result = runner.invoke(main, ["--dhf", dhf_str, "test", "pull", "--run-id", "1"])

        assert result.exit_code == 0
        mock_gh.from_environment.assert_called_once()

    def test_provider_gitlab_dispatches_to_gitlab_fetcher(self, runner, dhf_str):
        with patch("utils.local_adapter.GitLabArtifactFetcher") as mock_gl:
            mock_instance = MagicMock()
            mock_instance.fetch.return_value = {"results": [], "run_id": "5", "run_url": "http://y"}
            mock_gl.from_environment.return_value = mock_instance
            result = runner.invoke(
                main, ["--dhf", dhf_str, "test", "pull", "--provider", "gitlab", "--run-id", "5"]
            )

        assert result.exit_code == 0
        mock_gl.from_environment.assert_called_once()

    def test_provider_jenkins_dispatches_to_jenkins_fetcher(self, runner, dhf_str):
        with patch("utils.local_adapter.JenkinsArtifactFetcher") as mock_j:
            mock_instance = MagicMock()
            mock_instance.fetch.return_value = {"results": [], "run_id": "42", "run_url": "http://z"}
            mock_j.from_environment.return_value = mock_instance
            result = runner.invoke(
                main, ["--dhf", dhf_str, "test", "pull", "--provider", "jenkins", "--run-id", "42"]
            )

        assert result.exit_code == 0
        mock_j.from_environment.assert_called_once()

    def test_invalid_provider_rejected(self, runner, dhf_str):
        result = runner.invoke(
            main, ["--dhf", dhf_str, "test", "pull", "--provider", "bamboo"]
        )
        assert result.exit_code != 0
        assert "bamboo" in result.output or "invalid" in result.output.lower()
