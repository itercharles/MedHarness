"""
Tests for CR-029: Multi-DHF and Multi-Project Support.

Verifies that MultiDHFAdapter correctly aggregates multiple DHF projects,
namespaces IDs, routes queries, and integrates with the CLI --project flag.

@links: SYS-008
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from click.testing import CliRunner
from compliantflow.adapters.multi import MultiDHFAdapter
from utils.cli import main as utils_main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def runner():
    return CliRunner()


def _make_mock_adapter(slug: str, item_ids: list[str]) -> MagicMock:
    """Build a minimal mock DHFAdapter with a few items."""
    adapter = MagicMock()
    items = [{"id": iid, "type": "SYS", "title": f"{slug} item {iid}"} for iid in item_ids]
    adapter.list_items.return_value = items
    adapter.get_item.side_effect = lambda uid: next(
        (i for i in items if i["id"] == uid), None
    )
    adapter.validate_schema.return_value = {}
    adapter.get_project_config.return_value = MagicMock()
    adapter.get_all_test_results.return_value = {
        f"TC-{iid}": {"testing_status": "passed"} for iid in item_ids
    }
    adapter.get_test_result_items.return_value = []
    adapter.list_documents.return_value = [f"DOC-{iid}" for iid in item_ids]
    adapter.get_document.side_effect = lambda doc_id: f"content of {doc_id}"
    return adapter


@pytest.fixture
def two_project_multi():
    """MultiDHFAdapter with two mock projects: alpha and beta."""
    alpha = _make_mock_adapter("alpha", ["SYS-001", "SYS-002"])
    beta = _make_mock_adapter("beta", ["SYS-001", "SYS-003"])
    return MultiDHFAdapter({"alpha": alpha, "beta": beta}), alpha, beta


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestMultiDHFAdapterConstruction:
    def test_requires_at_least_one_adapter(self):
        with pytest.raises(ValueError, match="at least one"):
            MultiDHFAdapter({})

    def test_primary_slug_is_first_entry(self, two_project_multi):
        multi, _, _ = two_project_multi
        assert multi.primary_slug == "alpha"

    def test_project_slugs_returns_all(self, two_project_multi):
        multi, _, _ = two_project_multi
        assert multi.project_slugs == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# list_items — namespacing and merging
# ---------------------------------------------------------------------------

class TestListItems:
    def test_items_from_all_projects_returned(self, two_project_multi):
        multi, _, _ = two_project_multi
        items = multi.list_items()
        assert len(items) == 4  # 2 from alpha + 2 from beta

    def test_ids_are_namespaced(self, two_project_multi):
        multi, _, _ = two_project_multi
        ids = {i["id"] for i in multi.list_items()}
        assert "alpha::SYS-001" in ids
        assert "alpha::SYS-002" in ids
        assert "beta::SYS-001" in ids
        assert "beta::SYS-003" in ids

    def test_no_id_collision_between_projects(self, two_project_multi):
        """Both projects have SYS-001 — they must not collide."""
        multi, _, _ = two_project_multi
        ids = [i["id"] for i in multi.list_items()]
        # Both appear, namespaced differently
        assert ids.count("alpha::SYS-001") == 1
        assert ids.count("beta::SYS-001") == 1

    def test_doc_type_filter_forwarded_to_all_adapters(self, two_project_multi):
        multi, alpha, beta = two_project_multi
        multi.list_items(doc_type="SYS")
        alpha.list_items.assert_called_with("SYS")
        beta.list_items.assert_called_with("SYS")


# ---------------------------------------------------------------------------
# get_item — routing by namespace prefix
# ---------------------------------------------------------------------------

class TestGetItem:
    def test_namespaced_id_routes_to_correct_adapter(self, two_project_multi):
        multi, alpha, beta = two_project_multi
        multi.get_item("beta::SYS-003")
        beta.get_item.assert_called_with("SYS-003")
        alpha.get_item.assert_not_called()

    def test_returned_item_retains_namespace(self, two_project_multi):
        multi, _, _ = two_project_multi
        item = multi.get_item("alpha::SYS-001")
        assert item is not None
        assert item["id"] == "alpha::SYS-001"

    def test_unnamespaced_id_routes_to_primary(self, two_project_multi):
        multi, alpha, _ = two_project_multi
        multi.get_item("SYS-001")
        alpha.get_item.assert_called_with("SYS-001")

    def test_returns_none_for_missing_item(self, two_project_multi):
        multi, alpha, _ = two_project_multi
        alpha.get_item.side_effect = lambda uid: None
        assert multi.get_item("alpha::MISSING") is None

    def test_unknown_slug_raises_key_error(self, two_project_multi):
        multi, _, _ = two_project_multi
        with pytest.raises(KeyError, match="unknown-project"):
            multi.get_item("unknown-project::SYS-001")


# ---------------------------------------------------------------------------
# validate_schema — merges errors across projects
# ---------------------------------------------------------------------------

class TestValidateSchema:
    def test_errors_from_all_projects_are_namespaced(self):
        alpha = MagicMock()
        alpha.validate_schema.return_value = {"file1.yaml": "bad field"}
        beta = MagicMock()
        beta.validate_schema.return_value = {"file2.yaml": "missing required"}
        multi = MultiDHFAdapter({"alpha": alpha, "beta": beta})

        errors = multi.validate_schema()
        assert "alpha::file1.yaml" in errors
        assert "beta::file2.yaml" in errors

    def test_empty_when_no_errors(self, two_project_multi):
        multi, _, _ = two_project_multi
        assert multi.validate_schema() == {}


# ---------------------------------------------------------------------------
# Test results — namespacing
# ---------------------------------------------------------------------------

class TestTestResults:
    def test_get_all_test_results_namespaced(self, two_project_multi):
        multi, _, _ = two_project_multi
        results = multi.get_all_test_results()
        assert "alpha::TC-SYS-001" in results
        assert "beta::TC-SYS-001" in results

    def test_get_test_result_routes_by_prefix(self, two_project_multi):
        multi, alpha, beta = two_project_multi
        alpha.get_test_result = MagicMock(return_value={"testing_status": "passed"})
        beta.get_test_result = MagicMock(return_value=None)

        multi.get_test_result("alpha::TC-001")
        alpha.get_test_result.assert_called_with("TC-001")
        beta.get_test_result.assert_not_called()


# ---------------------------------------------------------------------------
# Documents — namespacing
# ---------------------------------------------------------------------------

class TestDocuments:
    def test_list_documents_namespaced(self, two_project_multi):
        multi, _, _ = two_project_multi
        docs = multi.list_documents()
        assert all("::" in d for d in docs)
        assert any(d.startswith("alpha::") for d in docs)
        assert any(d.startswith("beta::") for d in docs)

    def test_get_document_routes_to_correct_adapter(self, two_project_multi):
        multi, alpha, beta = two_project_multi
        multi.get_document("beta::DOC-SYS-003")
        beta.get_document.assert_called_with("DOC-SYS-003")
        alpha.get_document.assert_not_called()


# ---------------------------------------------------------------------------
# get_project_config — uses primary adapter
# ---------------------------------------------------------------------------

class TestProjectConfig:
    def test_returns_primary_config(self, two_project_multi):
        multi, alpha, beta = two_project_multi
        multi.get_project_config()
        alpha.get_project_config.assert_called_once()
        beta.get_project_config.assert_not_called()


# ---------------------------------------------------------------------------
# Compliance runs — delegated to primary
# ---------------------------------------------------------------------------

class TestComplianceRuns:
    def test_record_delegates_to_primary(self, two_project_multi):
        multi, alpha, beta = two_project_multi
        multi.record_compliance_run("iec62304", {}, "abc123", "manual")
        alpha.record_compliance_run.assert_called_once()
        beta.record_compliance_run.assert_not_called()

    def test_get_runs_delegates_to_primary(self, two_project_multi):
        multi, alpha, beta = two_project_multi
        alpha.get_compliance_runs.return_value = []
        multi.get_compliance_runs("iec62304")
        alpha.get_compliance_runs.assert_called_once()
        beta.get_compliance_runs.assert_not_called()


# ---------------------------------------------------------------------------
# CLI --project flag wiring
# ---------------------------------------------------------------------------

class TestCLIProjectFlag:
    def test_invalid_format_rejected(self, runner, test_dhf_root):
        from compliantflow.cli import main as cf_main
        result = runner.invoke(cf_main, ["--project", "no-colon", "validate", "traceability"])
        assert result.exit_code != 0
        assert "slug:path" in result.output.lower() or "format" in result.output.lower()

    def test_single_project_flag_produces_namespaced_output(self, runner, test_dhf_root):
        from compliantflow.cli import main as cf_main
        result = runner.invoke(
            cf_main,
            ["--project", f"alpha:{test_dhf_root}", "validate", "traceability"],
        )
        # Exit 1 is expected when the test DHF has orphans — that is correct
        # behaviour. What matters is that items are namespaced in the output.
        assert result.exit_code != 2  # not a Click usage error
        assert "alpha::" in result.output

    def test_two_project_flags_produce_both_slugs_in_output(self, runner, test_dhf_root):
        from compliantflow.cli import main as cf_main
        result = runner.invoke(
            cf_main,
            [
                "--project", f"alpha:{test_dhf_root}",
                "--project", f"beta:{test_dhf_root}",
                "validate", "traceability",
            ],
        )
        assert result.exit_code != 2
        assert "alpha::" in result.output
        assert "beta::" in result.output
