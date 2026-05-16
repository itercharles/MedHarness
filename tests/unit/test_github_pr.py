"""Unit tests for medharness.services.github_pr."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from medharness.services.github_pr import add_label, post_pr_comment, remove_label


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


class TestRemoveLabel:
    def test_returns_true_on_success(self):
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            ok = remove_label(7, "cr:stage/cr")
        assert ok is True
        args = mock_run.call_args[0][0]
        assert "-X" in args
        assert "DELETE" in args
        assert "cr%3Astage%2Fcr" in args[-1]

    def test_returns_false_on_failure(self):
        mock_result = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock_result):
            ok = remove_label(7, "cr:stage/cr")
        assert ok is False

    def test_returns_false_on_exception(self):
        with patch("subprocess.run", side_effect=OSError):
            ok = remove_label(7, "cr:stage/cr")
        assert ok is False

    def test_url_encodes_label(self):
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            remove_label(5, "a b/c")
        args = mock_run.call_args[0][0]
        # space → %20, / → %2F
        assert "a%20b%2Fc" in args[-1]


class TestAddLabel:
    def test_returns_true_on_success(self):
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            ok = add_label(7, "cr:stage/design")
        assert ok is True
        args = mock_run.call_args[0][0]
        assert "-X" in args
        assert "POST" in args
        assert any("cr:stage/design" in a for a in args)

    def test_returns_false_on_failure(self):
        mock_result = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock_result):
            ok = add_label(7, "cr:stage/design")
        assert ok is False

    def test_returns_false_on_exception(self):
        with patch("subprocess.run", side_effect=OSError):
            ok = add_label(7, "cr:stage/design")
        assert ok is False
