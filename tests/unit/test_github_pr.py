"""Unit tests for medharness.services.github_pr."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from medharness.services.github_pr import post_pr_comment


class TestPostPrComment:
    def test_returns_url_on_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/org/repo/pull/1#issuecomment-123\n"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            url = post_pr_comment(42, "hello")
        assert url == "https://github.com/org/repo/pull/1#issuecomment-123"
        args = mock_run.call_args[0][0]
        assert args[:4] == ["gh", "pr", "comment", "42"]
        assert "--body" in args
        assert "hello" in args

    def test_returns_empty_on_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            url = post_pr_comment(42, "hello")
        assert url == ""

    def test_returns_empty_on_exception(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            url = post_pr_comment(42, "hello")
        assert url == ""

    def test_injects_token_into_env(self):
        mock_result = MagicMock(returncode=0, stdout="url\n")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            post_pr_comment(1, "body", token="tok123")
        env = mock_run.call_args[1]["env"]
        assert env.get("GH_TOKEN") == "tok123"
        assert env.get("GITHUB_TOKEN") == "tok123"
