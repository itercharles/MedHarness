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


def _write_soup(dhf: Path, soup_id: str, name: str, version: str, ecosystem: str | None = None) -> None:
    soup_dir = dhf / "items" / "09_soup"
    soup_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {soup_id}", f"title: {name}", f"name: {name}", f"version: '{version}'"]
    if ecosystem:
        lines.append(f"ecosystem: {ecosystem}")
    (soup_dir / f"{soup_id}.yaml").write_text("\n".join(lines) + "\n")


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
        osv_response = {
            "results": [{
                "vulns": [{
                    "id": "GHSA-x84v-xcm2-53pg",
                    "summary": "CRLF injection in requests",
                    "database_specific": {"severity": "HIGH"},
                }]
            }]
        }
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.read.return_value = json.dumps(osv_response).encode()
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
