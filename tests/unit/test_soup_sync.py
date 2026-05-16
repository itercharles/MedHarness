"""Unit tests for medharness.services.soup_sync."""

from pathlib import Path
from unittest.mock import patch

import pytest

from medharness.services.soup_sync import (
    _find_soup_item,
    _normalize_name,
    _normalize_version,
    _package_key,
    diff_against_dhf,
    parse_package_json,
    parse_requirements_txt,
    sync_soup_items,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req_txt(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "requirements.txt"
    p.write_text(content, encoding="utf-8")
    return p


def _pkg_json(tmp_path: Path, content: dict) -> Path:
    import json
    p = tmp_path / "package.json"
    p.write_text(json.dumps(content), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# parse_requirements_txt
# ---------------------------------------------------------------------------

class TestParseRequirementsTxt:
    def test_basic_pinned(self, tmp_path):
        path = _req_txt(tmp_path, "requests==2.31.0\n")
        pkgs = parse_requirements_txt(path)
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "requests"
        assert pkgs[0]["version"] == "2.31.0"
        assert pkgs[0]["ecosystem"] == "pypi"

    def test_extras_ignored(self, tmp_path):
        path = _req_txt(tmp_path, "medharness[llm]==0.6.3\n")
        pkgs = parse_requirements_txt(path)
        assert pkgs[0]["name"] == "medharness"
        assert pkgs[0]["version"] == "0.6.3"

    def test_comments_and_blanks_skipped(self, tmp_path):
        path = _req_txt(tmp_path, "# comment\n\nnumpy==1.26.0\n")
        pkgs = parse_requirements_txt(path)
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "numpy"

    def test_non_pinned_skipped(self, tmp_path):
        path = _req_txt(tmp_path, "requests>=2.0\nfoo\nbar!=1.0\n")
        pkgs = parse_requirements_txt(path)
        assert pkgs == []

    def test_multiple_packages(self, tmp_path):
        path = _req_txt(tmp_path, "click==8.1.7\nrich==13.7.0\n")
        pkgs = parse_requirements_txt(path)
        assert {p["name"] for p in pkgs} == {"click", "rich"}

    def test_source_field_set(self, tmp_path):
        path = _req_txt(tmp_path, "flask==3.0.0\n")
        pkgs = parse_requirements_txt(path)
        assert pkgs[0]["source"] == str(path)


# ---------------------------------------------------------------------------
# parse_package_json
# ---------------------------------------------------------------------------

class TestParsePackageJson:
    def test_dependencies(self, tmp_path):
        path = _pkg_json(tmp_path, {"dependencies": {"react": "^18.2.0"}})
        pkgs = parse_package_json(path)
        assert any(p["name"] == "react" and p["dev"] is False for p in pkgs)

    def test_dev_dependencies_flagged(self, tmp_path):
        path = _pkg_json(tmp_path, {"devDependencies": {"vitest": "^2.0.0"}})
        pkgs = parse_package_json(path)
        assert any(p["name"] == "vitest" and p["dev"] is True for p in pkgs)

    def test_version_stripping(self, tmp_path):
        path = _pkg_json(tmp_path, {"dependencies": {"lodash": "^4.17.21"}})
        pkgs = parse_package_json(path)
        assert pkgs[0]["version"] == "4.17.21"

    def test_empty_manifest(self, tmp_path):
        path = _pkg_json(tmp_path, {})
        pkgs = parse_package_json(path)
        assert pkgs == []

    def test_ecosystem_set(self, tmp_path):
        path = _pkg_json(tmp_path, {"dependencies": {"axios": "^1.6.0"}})
        pkgs = parse_package_json(path)
        assert pkgs[0]["ecosystem"] == "npm"


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

class TestNormalizeHelpers:
    def test_normalize_name_lowercases(self):
        assert _normalize_name("MyPackage") == "mypackage"

    def test_normalize_name_strips_separators(self):
        assert _normalize_name("my-package_v2.0") == "mypackagev20"

    def test_normalize_version_strips_caret(self):
        assert _normalize_version("^1.2.3") == "1.2.3"

    def test_normalize_version_strips_tilde(self):
        assert _normalize_version("~2.0.0") == "2.0.0"

    def test_normalize_version_strips_gte(self):
        assert _normalize_version(">=3.0") == "3.0"

    def test_normalize_version_leaves_plain(self):
        assert _normalize_version("4.5.6") == "4.5.6"


# ---------------------------------------------------------------------------
# diff_against_dhf
# ---------------------------------------------------------------------------

def _make_soup_item(uid: str, name: str, version: str) -> dict:
    return {"uid": uid, "type": "SOUP", "name": name, "version": version}


class TestDiffAgainstDhf:
    def test_new_package_goes_to_create(self):
        packages = [{"name": "click", "version": "8.0.0", "ecosystem": "pypi"}]
        diff = diff_against_dhf(packages, [])
        assert diff["to_create"] == [packages[0]]
        assert diff["to_update"] == []
        assert diff["orphans"] == []

    def test_matching_package_goes_to_matched(self):
        soup = [_make_soup_item("SOUP-001", "click", "8.0.0")]
        packages = [{"name": "click", "version": "8.0.0", "ecosystem": "pypi"}]
        diff = diff_against_dhf(packages, soup)
        assert diff["to_create"] == []
        assert diff["to_update"] == []
        assert diff["orphans"] == []
        assert len(diff["matched"]) == 1

    def test_version_drift_goes_to_update(self):
        soup = [_make_soup_item("SOUP-001", "click", "7.0.0")]
        packages = [{"name": "click", "version": "8.0.0", "ecosystem": "pypi"}]
        diff = diff_against_dhf(packages, soup)
        assert len(diff["to_update"]) == 1
        assert diff["to_update"][0]["old_version"] == "7.0.0"
        assert diff["to_update"][0]["pkg"]["version"] == "8.0.0"

    def test_extra_soup_item_is_orphan(self):
        soup = [_make_soup_item("SOUP-001", "oldlib", "1.0.0")]
        diff = diff_against_dhf([], soup)
        assert len(diff["orphans"]) == 1
        assert diff["orphans"][0]["uid"] == "SOUP-001"

    def test_fuzzy_name_matching(self):
        soup = [_make_soup_item("SOUP-001", "My_Package", "1.0.0")]
        packages = [{"name": "my-package", "version": "1.0.0", "ecosystem": "pypi"}]
        diff = diff_against_dhf(packages, soup)
        assert diff["to_create"] == []
        assert len(diff["matched"]) == 1

    def test_caret_stripped_when_comparing_versions(self):
        soup = [_make_soup_item("SOUP-001", "react", "18.2.0")]
        packages = [{"name": "react", "version": "^18.2.0", "ecosystem": "npm"}]
        diff = diff_against_dhf(packages, soup)
        assert diff["to_update"] == []
        assert len(diff["matched"]) == 1


# ---------------------------------------------------------------------------
# sync_soup_items (integration, mocked dhfkit)
# ---------------------------------------------------------------------------

class TestSyncSoupItems:
    def test_dry_run_returns_diff_without_writing(self, tmp_path):
        req = _req_txt(tmp_path, "requests==2.31.0\n")
        with patch("dhfkit.api.list_items", return_value=[]) as mock_list, \
             patch("dhfkit.api.create_item") as mock_create:
            result = sync_soup_items(tmp_path / "DHF", [req], write=False)

        assert result["outcome"] == "completed"
        assert "requests" in result["to_create"]
        mock_create.assert_not_called()

    def test_write_creates_new_items(self, tmp_path):
        req = _req_txt(tmp_path, "flask==3.0.0\n")
        with patch("dhfkit.api.list_items", return_value=[]), \
             patch("dhfkit.api.create_item", return_value={"uid": "SOUP-001"}) as mock_create:
            result = sync_soup_items(tmp_path / "DHF", [req], write=True)

        mock_create.assert_called_once()
        assert result["items_created"] == ["SOUP-001"]

    def test_write_updates_drifted_items(self, tmp_path):
        req = _req_txt(tmp_path, "click==8.1.7\n")
        existing = _make_soup_item("SOUP-001", "click", "8.0.0")
        with patch("dhfkit.api.list_items", return_value=[existing]), \
             patch("dhfkit.api.update_item", return_value=existing) as mock_update:
            result = sync_soup_items(tmp_path / "DHF", [req], write=True)

        mock_update.assert_called_once_with(
            tmp_path / "DHF", "SOUP-001", {"version": "8.1.7"},
            author="ci", cr_id=None,
        )
        assert result["items_updated"] == ["SOUP-001"]

    def test_invalid_manifest_adds_error(self, tmp_path):
        bad = tmp_path / "setup.cfg"
        bad.write_text("not a manifest", encoding="utf-8")
        with patch("dhfkit.api.list_items", return_value=[]):
            result = sync_soup_items(tmp_path / "DHF", [bad], write=False)

        assert result["outcome"] == "completed_with_errors"
        assert any("Unsupported manifest" in e for e in result["errors"])

    def test_author_and_cr_forwarded(self, tmp_path):
        req = _req_txt(tmp_path, "numpy==1.26.0\n")
        with patch("dhfkit.api.list_items", return_value=[]), \
             patch("dhfkit.api.create_item", return_value={"uid": "SOUP-002"}) as mock_create:
            sync_soup_items(tmp_path / "DHF", [req], write=True, author="agent", cr_id="CR-007")

        _, kwargs = mock_create.call_args
        assert kwargs.get("author") == "agent"
        assert kwargs.get("cr_id") == "CR-007"

    def test_multiple_manifests_merged(self, tmp_path):
        req = _req_txt(tmp_path, "flask==3.0.0\n")
        pkg = _pkg_json(tmp_path, {"dependencies": {"react": "^18.2.0"}})
        with patch("dhfkit.api.list_items", return_value=[]):
            result = sync_soup_items(tmp_path / "DHF", [req, pkg], write=False)

        assert set(result["to_create"]) == {"flask", "react"}
        assert len(result["manifests_parsed"]) == 2

    def test_dhf_list_failure_adds_error(self, tmp_path):
        req = _req_txt(tmp_path, "requests==2.31.0\n")
        with patch("dhfkit.api.list_items", side_effect=RuntimeError("boom")):
            result = sync_soup_items(tmp_path / "DHF", [req], write=False)

        assert result["outcome"] == "completed_with_errors"
        assert any("Failed to list SOUP" in e for e in result["errors"])
