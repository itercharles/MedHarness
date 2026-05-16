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


def test_get_session_returns_empty_when_jq_emits_null(monkeypatch):
    """jq outputs literal 'null' when no marker comment exists; get_session must return ''."""
    import subprocess as _sp
    from unittest.mock import MagicMock, patch

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "null\n"  # what gh --jq emits when [] | last has no match
    with patch("subprocess.run", return_value=mock_result):
        sid = get_session(42)
    assert sid == "", f"expected empty string, got {sid!r}"


def test_get_session_parses_valid_session_id(monkeypatch):
    from unittest.mock import MagicMock, patch

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "abc-session-123\n"
    with patch("subprocess.run", return_value=mock_result):
        sid = get_session(42)
    assert sid == "abc-session-123"


def test_marker_format():
    from medharness.services.github_session import _MARKER_START, _MARKER_END

    body = f"{_MARKER_START} my-session-id {_MARKER_END}"
    assert "claude-session:" in body
    assert "my-session-id" in body
    assert body.endswith("-->")
