"""Tests for medharness.services.gh — the one place `gh` is run."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from medharness.services.gh import gh


def _env_seen(monkeypatch, token: str = "", **environ: str) -> dict:
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="")) as run:
        gh(["auth", "status"], token=token)
    return run.call_args.kwargs["env"]


@pytest.mark.parametrize("token,environ,expected", [
    ("explicit", {"GH_TOKEN": "a", "GITHUB_TOKEN": "b"}, "explicit"),
    ("", {"GH_TOKEN": "a", "GITHUB_TOKEN": "b"}, "a"),
    ("", {"GITHUB_TOKEN": "b"}, "b"),
])
def test_the_token_order_is_the_one_gh_uses(monkeypatch, token, environ, expected) -> None:
    env = _env_seen(monkeypatch, token, **environ)
    assert env["GH_TOKEN"] == env["GITHUB_TOKEN"] == expected


def test_no_token_sets_none(monkeypatch) -> None:
    env = _env_seen(monkeypatch)
    assert "GH_TOKEN" not in env and "GITHUB_TOKEN" not in env


def test_it_returns_the_exit_code_and_stripped_stdout() -> None:
    with patch("subprocess.run", return_value=MagicMock(returncode=3, stdout=" out\n")) as run:
        assert gh(["pr", "view", "1"]) == (3, "out")
    assert run.call_args.args[0] == ["gh", "pr", "view", "1"]


def test_a_missing_gh_is_a_failure_not_an_exception() -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError("gh")):
        rc, out = gh(["pr", "view", "1"])
    assert rc == 1 and "gh" in out
