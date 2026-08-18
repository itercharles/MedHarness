"""Tests for soup_vuln_gate()."""

from __future__ import annotations

import importlib.resources
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dhfkit.cli import main as dhfkit_main
from medharness.cli import main
from medharness.services.ci import soup_vuln_gate


def _make_dhf(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
    soup_src = importlib.resources.files("dhfkit").joinpath("templates/config/doc_types/soup.yaml")
    (dhf / "config" / "doc_types" / "soup.yaml").write_bytes(soup_src.read_bytes())
    return dhf


def _write_soup(dhf: Path, soup_id: str, name: str, version: str, ecosystem: str | None = None,
                accepted_vulns: list | None = None) -> None:
    soup_dir = dhf / "items" / "09_soup"
    soup_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {soup_id}", f"title: {name}", f"name: {name}", f"version: '{version}'"]
    if ecosystem:
        lines.append(f"ecosystem: {ecosystem}")
    if accepted_vulns is not None:
        lines.append("accepted_vulns:")
        for entry in accepted_vulns:
            if isinstance(entry, dict):
                first = True
                for key, value in entry.items():
                    prefix = "  - " if first else "    "
                    lines.append(f'{prefix}{key}: "{value}"')
                    first = False
            else:
                lines.append(f"  - {entry}")
    (soup_dir / f"{soup_id}.yaml").write_text("\n".join(lines) + "\n")


def _osv(mock_open, response: dict) -> None:
    """Wire a mocked urlopen to return *response* as the osv.dev body."""
    mock_open.return_value.__enter__ = lambda s: s
    mock_open.return_value.__exit__ = MagicMock(return_value=False)
    mock_open.return_value.read.return_value = json.dumps(response).encode()


# osv.dev's querybatch returns only id + modified — summary and severity come
# from the per-vulnerability endpoint, so batch fixtures must not invent them.
_VULN = {"id": "GHSA-x84v-xcm2-53pg", "modified": "2024-01-01T00:00:00Z"}


# ---------------------------------------------------------------------------
# Service-level tests (osv.dev mocked)
# ---------------------------------------------------------------------------

class TestSoupVulnGate:
    def test_no_soup_items_passes(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        result = soup_vuln_gate(dhf)
        assert result["passed"] is True
        assert result["soup_count"] == 0
        assert result["checked_count"] == 0

    def test_soup_without_ecosystem_skipped(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.25.0")  # no ecosystem
        result = soup_vuln_gate(dhf)
        assert result["passed"] is True
        assert result["checked_count"] == 0
        assert any("ecosystem" in s["reason"] for s in result["skipped"])

    def test_clean_soup_passes(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.28.0", ecosystem="PyPI")
        osv_response = {"results": [{"vulns": []}]}
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.read.return_value = json.dumps(osv_response).encode()
            result = soup_vuln_gate(dhf)
        assert result["passed"] is True
        assert result["checked_count"] == 1
        assert result["vulnerable"] == []

    def test_vulnerable_soup_fails(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI")
        with patch("urllib.request.urlopen") as mock_open:
            _osv(mock_open, {"results": [{"vulns": [_VULN]}]})
            result = soup_vuln_gate(dhf)
        assert result["passed"] is False
        assert len(result["vulnerable"]) == 1
        assert result["vulnerable"][0]["soup_id"] == "SOUP-001"
        assert result["vulnerable"][0]["vulns"][0]["id"] == "GHSA-x84v-xcm2-53pg"

    def test_network_error_fails(self, tmp_path: Path) -> None:
        import urllib.error
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.28.0", ecosystem="PyPI")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            result = soup_vuln_gate(dhf)
        assert result["passed"] is False
        assert result["error"] is not None
        assert "unreachable" in result["error"]

    def test_network_error_tolerated_in_warn_mode(self, tmp_path: Path) -> None:
        import urllib.error
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.28.0", ecosystem="PyPI")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            result = soup_vuln_gate(dhf, offline_mode="warn")
        assert result["passed"] is True
        assert "unreachable" in result["error"]
        assert "offline process" in result["summary"]

    def test_multiple_items_batched(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.28.0", ecosystem="PyPI")
        _write_soup(dhf, "SOUP-002", "flask", "2.0.0", ecosystem="PyPI")
        osv_response = {"results": [{"vulns": []}, {"vulns": []}]}
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.read.return_value = json.dumps(osv_response).encode()
            result = soup_vuln_gate(dhf)
        assert result["passed"] is True
        assert result["checked_count"] == 2
        # Verify it was a single batch call
        assert mock_open.call_count == 1

    def test_soup_without_name_skipped(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        soup_dir = dhf / "items" / "09_soup"
        soup_dir.mkdir(parents=True, exist_ok=True)
        (soup_dir / "SOUP-001.yaml").write_text(
            "id: SOUP-001\ntitle: Unnamed\nversion: '1.0'\necosystem: PyPI\n"
        )
        result = soup_vuln_gate(dhf)
        assert result["checked_count"] == 0
        assert any("name" in s["reason"] for s in result["skipped"])


# ---------------------------------------------------------------------------
# Vulnerability detail enrichment
#
# osv.dev's querybatch returns only {id, modified}; summary and severity have to
# come from the per-vulnerability endpoint. These tests pin that behaviour so the
# gate never reports a bare ID with no way to act on it.
# ---------------------------------------------------------------------------

class TestVulnDetail:
    def test_summary_fetched_from_detail_endpoint(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI")
        batch = {"results": [{"vulns": [_VULN]}]}
        detail = {"summary": "CRLF injection in requests",
                  "database_specific": {"severity": "HIGH"}}

        def _responses(*args, **kwargs):
            url = args[0] if isinstance(args[0], str) else args[0].full_url
            body = detail if "/vulns/" in url else batch
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.read.return_value = json.dumps(body).encode()
            return resp

        with patch("urllib.request.urlopen", side_effect=_responses):
            result = soup_vuln_gate(dhf)
        vuln = result["vulnerable"][0]["vulns"][0]
        assert vuln["summary"] == "CRLF injection in requests"
        assert vuln["severity"] == "HIGH"

    def test_url_present_when_detail_lookup_fails(self, tmp_path: Path) -> None:
        """A failed enrichment must still leave the finding actionable."""
        import urllib.error
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI")
        batch = {"results": [{"vulns": [_VULN]}]}
        calls = {"n": 0}

        def _responses(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] > 1:  # the detail lookup
                raise urllib.error.URLError("detail endpoint down")
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.read.return_value = json.dumps(batch).encode()
            return resp

        with patch("urllib.request.urlopen", side_effect=_responses):
            result = soup_vuln_gate(dhf)
        vuln = result["vulnerable"][0]["vulns"][0]
        assert result["passed"] is False
        assert vuln["summary"] == ""
        assert vuln["url"] == "https://osv.dev/vulnerability/GHSA-x84v-xcm2-53pg"

    def test_cli_falls_back_to_url_when_summary_empty(self, tmp_path: Path) -> None:
        import urllib.error
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI")
        batch = {"results": [{"vulns": [_VULN]}]}
        calls = {"n": 0}

        def _responses(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] > 1:
                raise urllib.error.URLError("detail endpoint down")
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.read.return_value = json.dumps(batch).encode()
            return resp

        with patch("urllib.request.urlopen", side_effect=_responses):
            r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "soup"])
        assert r.exit_code != 0
        assert "https://osv.dev/vulnerability/GHSA-x84v-xcm2-53pg" in r.output
        assert "— \n" not in r.output  # no dangling separator

    def test_detail_lookups_are_budgeted(self, tmp_path: Path) -> None:
        """A large finding set must not fan out into unbounded requests."""
        from medharness.services.ci import _VULN_DETAIL_BUDGET

        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI")
        many = [{"id": f"GHSA-{i:04d}", "modified": "2024-01-01T00:00:00Z"}
                for i in range(_VULN_DETAIL_BUDGET + 10)]
        batch = {"results": [{"vulns": many}]}
        calls = {"n": 0}

        def _responses(*args, **kwargs):
            calls["n"] += 1
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            body = batch if calls["n"] == 1 else {"summary": "x"}
            resp.read.return_value = json.dumps(body).encode()
            return resp

        with patch("urllib.request.urlopen", side_effect=_responses):
            result = soup_vuln_gate(dhf)
        assert len(result["vulnerable"][0]["vulns"]) == _VULN_DETAIL_BUDGET + 10
        assert calls["n"] == _VULN_DETAIL_BUDGET + 1  # batch + budgeted lookups

    def test_budget_resets_between_calls(self, tmp_path: Path) -> None:
        """Budget is per-invocation, not process-global."""
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI")
        batch = {"results": [{"vulns": [_VULN]}]}

        def _run() -> int:
            calls = {"n": 0}

            def _responses(*args, **kwargs):
                calls["n"] += 1
                resp = MagicMock()
                resp.__enter__ = lambda s: s
                resp.__exit__ = MagicMock(return_value=False)
                body = batch if calls["n"] == 1 else {"summary": "enriched"}
                resp.read.return_value = json.dumps(body).encode()
                return resp

            with patch("urllib.request.urlopen", side_effect=_responses):
                result = soup_vuln_gate(dhf)
            return result["vulnerable"][0]["vulns"][0]["summary"]

        assert _run() == "enriched"
        assert _run() == "enriched"  # second call still has budget


# ---------------------------------------------------------------------------
# Documented vulnerability acceptance (IEC 62304 §8.1.2)
# ---------------------------------------------------------------------------

class TestAcceptedVulns:
    def test_documented_acceptance_does_not_block(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(
            dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI",
            accepted_vulns=[{"id": "GHSA-x84v-xcm2-53pg",
                             "rationale": "Affected API not reachable from our code paths."}],
        )
        with patch("urllib.request.urlopen") as mock_open:
            _osv(mock_open, {"results": [{"vulns": [_VULN]}]})
            result = soup_vuln_gate(dhf)
        assert result["passed"] is True
        assert result["vulnerable"] == []
        assert len(result["accepted"]) == 1
        assert result["accepted"][0]["vuln_id"] == "GHSA-x84v-xcm2-53pg"
        assert "not reachable" in result["accepted"][0]["rationale"]

    def test_unlisted_vuln_still_blocks(self, tmp_path: Path) -> None:
        """Acceptance is per-ID, so a newly published CVE is not absorbed."""
        dhf = _make_dhf(tmp_path)
        _write_soup(
            dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI",
            accepted_vulns=[{"id": "GHSA-old-known-issue", "rationale": "Assessed in CR-004."}],
        )
        with patch("urllib.request.urlopen") as mock_open:
            _osv(mock_open, {"results": [{"vulns": [_VULN]}]})
            result = soup_vuln_gate(dhf)
        assert result["passed"] is False
        assert result["vulnerable"][0]["vulns"][0]["id"] == "GHSA-x84v-xcm2-53pg"
        assert result["accepted"] == []

    def test_acceptance_without_rationale_still_blocks(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(
            dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI",
            accepted_vulns=[{"id": "GHSA-x84v-xcm2-53pg"}],
        )
        with patch("urllib.request.urlopen") as mock_open:
            _osv(mock_open, {"results": [{"vulns": [_VULN]}]})
            result = soup_vuln_gate(dhf)
        assert result["passed"] is False
        assert any("rationale" in p for p in result["acceptance_problems"])

    def test_bare_string_entry_still_blocks(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(
            dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI",
            accepted_vulns=["GHSA-x84v-xcm2-53pg"],
        )
        with patch("urllib.request.urlopen") as mock_open:
            _osv(mock_open, {"results": [{"vulns": [_VULN]}]})
            result = soup_vuln_gate(dhf)
        assert result["passed"] is False
        assert any("mapping" in p for p in result["acceptance_problems"])

    def test_partial_acceptance_blocks_on_remainder(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        other = {"id": "GHSA-second-vuln", "modified": "2024-01-01T00:00:00Z"}
        _write_soup(
            dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI",
            accepted_vulns=[{"id": "GHSA-x84v-xcm2-53pg", "rationale": "Assessed, not exploitable."}],
        )
        with patch("urllib.request.urlopen") as mock_open:
            _osv(mock_open, {"results": [{"vulns": [_VULN, other]}]})
            result = soup_vuln_gate(dhf)
        assert result["passed"] is False
        assert len(result["accepted"]) == 1
        assert [v["id"] for v in result["vulnerable"][0]["vulns"]] == ["GHSA-second-vuln"]


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestVerifySoupCLI:
    def test_verify_soup_no_items_exits_zero(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "soup"])
        assert r.exit_code == 0, r.output
        payload = json.loads(r.output.splitlines()[0])
        assert payload["passed"] is True

    def test_verify_soup_vulnerable_exits_nonzero(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI")
        osv_response = {
            "results": [{
                "vulns": [{"id": "GHSA-test", "summary": "test vuln"}]
            }]
        }
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.read.return_value = json.dumps(osv_response).encode()
            r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "soup"])
        assert r.exit_code != 0
        payload = json.loads(r.output.splitlines()[0])
        assert payload["passed"] is False
        assert "FAIL [soup-vuln]" in r.output

    def test_offline_mode_warn_exits_zero(self, tmp_path: Path) -> None:
        import urllib.error
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.28.0", ecosystem="PyPI")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no route")):
            r = CliRunner().invoke(
                main, ["--dhf", str(dhf), "verify", "soup", "--offline-mode", "warn"]
            )
        assert r.exit_code == 0, r.output
        assert json.loads(r.output.splitlines()[0])["passed"] is True
        assert "WARN [soup-vuln]" in r.output

    def test_offline_mode_defaults_to_fail(self, tmp_path: Path) -> None:
        import urllib.error
        dhf = _make_dhf(tmp_path)
        _write_soup(dhf, "SOUP-001", "requests", "2.28.0", ecosystem="PyPI")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no route")):
            r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "soup"])
        assert r.exit_code != 0
        assert "ERROR [soup-vuln]" in r.output

    def test_accepted_vuln_reported_and_exits_zero(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_soup(
            dhf, "SOUP-001", "requests", "2.6.0", ecosystem="PyPI",
            accepted_vulns=[{"id": "GHSA-x84v-xcm2-53pg", "rationale": "Not exploitable here."}],
        )
        with patch("urllib.request.urlopen") as mock_open:
            _osv(mock_open, {"results": [{"vulns": [_VULN]}]})
            r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "soup"])
        assert r.exit_code == 0, r.output
        assert "ACCEPTED [soup-vuln]" in r.output
        assert "Not exploitable here." in r.output
