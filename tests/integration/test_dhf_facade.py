"""
Tests for DHF facade: DHF automation facade commands.

Verifies that MedHarness exposes generic DHF item operations and
implementation-context packaging through the adapter boundary.

"""

import json
from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main
from medharness.core import MedHarnessCore


def _invoke(monkeypatch, stub_adapter, args):
    monkeypatch.setattr("dhfkit.api._adapter", lambda dhf_root: stub_adapter)
    monkeypatch.setattr("medharness._helpers._make_adapter", lambda ctx: stub_adapter)
    runner = CliRunner()
    return runner.invoke(main, args)


def test_dhf_item_list_uses_adapter(monkeypatch, stub_adapter):
    """
    dhf item list returns adapter items as JSON lines.

    """
    stub_adapter.create_item({"id": "CR-900", "title": "Facade CR", "status": "planned"})

    result = _invoke(monkeypatch, stub_adapter, ["dhf", "item", "list", "--type", "CR"])

    assert result.exit_code == 0
    assert '"id": "CR-900"' in result.output


def test_dhf_item_create_update_delete(monkeypatch, stub_adapter):
    """
    dhf item create, update, and delete mutate through adapter.

    """
    create = _invoke(
        monkeypatch,
        stub_adapter,
        ["dhf", "item", "create", "--type", "CR", "--data", '{"title":"Facade"}'],
    )
    assert create.exit_code == 0
    item_id = json.loads(create.output)["id"]

    update = _invoke(
        monkeypatch,
        stub_adapter,
        ["dhf", "item", "update", item_id, "--data", '{"title":"Updated"}'],
    )
    assert update.exit_code == 0
    assert json.loads(update.output)["title"] == "Updated"

    delete = _invoke(monkeypatch, stub_adapter, ["dhf", "item", "delete", item_id])
    assert delete.exit_code == 0
    assert stub_adapter.get_item(item_id) is None


def test_dhf_item_transition(monkeypatch, stub_adapter):
    """
    dhf item transition delegates lifecycle changes to adapter.

    """
    stub_adapter.create_item({"id": "CR-901", "title": "Transition", "status": "planned"})

    result = _invoke(
        monkeypatch,
        stub_adapter,
        ["dhf", "item", "transition", "CR-901", "implementing", "--by", "tester"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "implementing"
    assert payload["implementing_by"] == "tester"


def test_core_get_implementation_context(stub_adapter):
    """
    core returns CR item, implementation spec, and DHF references.

    """
    stub_adapter.create_item({"id": "CR-902", "title": "Context", "status": "implementing"})
    stub_adapter._documents["CR-902-Spec"] = "# Implementation Spec\n"

    context = MedHarnessCore(stub_adapter).get_implementation_context("CR-902")

    assert context["cr"]["id"] == "CR-902"
    assert context["implementation_spec"] == "# Implementation Spec\n"
    assert context["dhf_references"] == ["CR-902", "CR-902-Spec"]

