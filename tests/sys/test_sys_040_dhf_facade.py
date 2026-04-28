"""
Tests for SYS-040: DHF automation facade commands.

Verifies that CompliantFlow exposes generic DHF item operations and
implementation-context packaging through the adapter boundary.

@links: SYS-040
"""

import json
from pathlib import Path

from click.testing import CliRunner

from compliantflow.cli import main
from compliantflow.core import CompliantFlowCore


def _invoke(monkeypatch, stub_adapter, args):
    monkeypatch.setattr("compliantflow.cli._make_adapter", lambda ctx: stub_adapter)
    runner = CliRunner()
    return runner.invoke(main, args)


def test_TC_SYS_040_001_dhf_item_list_uses_adapter(monkeypatch, stub_adapter):
    """
    TC-SYS-040-001: dhf item list returns adapter items as JSON lines.

    @test_id: TC-SYS-040-001
    @links: SYS-040
    """
    stub_adapter.create_item({"id": "CR-900", "title": "Facade CR", "status": "planned"})

    result = _invoke(monkeypatch, stub_adapter, ["dhf", "item", "list", "--type", "CR"])

    assert result.exit_code == 0
    assert '"id": "CR-900"' in result.output


def test_TC_SYS_040_002_dhf_item_create_update_delete(monkeypatch, stub_adapter):
    """
    TC-SYS-040-002: dhf item create, update, and delete mutate through adapter.

    @test_id: TC-SYS-040-002
    @links: SYS-040
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


def test_TC_SYS_040_003_dhf_item_transition(monkeypatch, stub_adapter):
    """
    TC-SYS-040-003: dhf item transition delegates lifecycle changes to adapter.

    @test_id: TC-SYS-040-003
    @links: SYS-040
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


def test_TC_SYS_040_004_core_get_implementation_context(stub_adapter):
    """
    TC-SYS-040-004: core returns CR item, implementation spec, and DHF references.

    @test_id: TC-SYS-040-004
    @links: SYS-040
    """
    stub_adapter.create_item({"id": "CR-902", "title": "Context", "status": "implementing"})
    stub_adapter._documents["CR-902-Spec"] = "# Implementation Spec\n"

    context = CompliantFlowCore(stub_adapter).get_implementation_context("CR-902")

    assert context["cr"]["id"] == "CR-902"
    assert context["implementation_spec"] == "# Implementation Spec\n"
    assert context["dhf_references"] == ["CR-902", "CR-902-Spec"]


def test_TC_SYS_040_005_dhf_context_implementation_writes_package(monkeypatch, stub_adapter, tmp_path):
    """
    TC-SYS-040-005: dhf context implementation writes stable context files.

    @test_id: TC-SYS-040-005
    @links: SYS-040
    """
    stub_adapter.create_item({"id": "CR-903", "title": "Package", "status": "implementing"})
    stub_adapter._documents["CR-903-Spec"] = "# Package Spec\n"
    out_dir = tmp_path / "context"

    result = _invoke(
        monkeypatch,
        stub_adapter,
        ["dhf", "context", "implementation", "--cr", "CR-903", "--out-dir", str(out_dir)],
    )

    assert result.exit_code == 0
    assert json.loads((out_dir / "CR-903.json").read_text())["id"] == "CR-903"
    assert (out_dir / "CR-903-Spec.md").read_text() == "# Package Spec\n"
    package = json.loads((out_dir / "implementation-context.json").read_text())
    assert Path(package["cr"]).name == "CR-903.json"
