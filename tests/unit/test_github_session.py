"""Tests for medharness.services.github_session."""

from medharness.services.github_session import get_session, put_session


def test_put_session_graceful_on_no_gh_cli(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("GH_TOKEN", "")
    monkeypatch.setenv("PATH", "/nonexistent")

    url = put_session(42, "session-abc")
    assert url == ""


def test_get_session_graceful_on_no_gh_cli(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("GH_TOKEN", "")
    monkeypatch.setenv("PATH", "/nonexistent")

    sid = get_session(42)
    assert sid == ""


def test_marker_format():
    from medharness.services.github_session import _MARKER_START, _MARKER_END

    body = f"{_MARKER_START} my-session-id {_MARKER_END}"
    assert "claude-session:" in body
    assert "my-session-id" in body
    assert body.endswith("-->")
