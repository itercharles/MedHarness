"""Tests for CR status: CR check-status Phase 0 gate behavior."""

from click.testing import CliRunner

from medharness.cli import main
from medharness.core import MedHarnessCore


def _invoke_check_status(monkeypatch, stub_adapter, cr_id: str):
    core = MedHarnessCore(stub_adapter)
    monkeypatch.setattr("medharness._helpers._make_core", lambda ctx: core)
    runner = CliRunner()
    return runner.invoke(main, ["cr", "check-status", cr_id])


def test_phase0_accepts_new(monkeypatch, stub_adapter):
    stub_adapter.create_item({"id": "CR-001", "title": "Test CR", "status": "new"})
    result = _invoke_check_status(monkeypatch, stub_adapter, "CR-001")
    assert result.exit_code == 0
    assert '"valid": true' in result.output


def test_phase0_rejects_completed(monkeypatch, stub_adapter):
    stub_adapter.create_item({"id": "CR-004", "title": "Test CR", "status": "completed"})
    result = _invoke_check_status(monkeypatch, stub_adapter, "CR-004")
    assert result.exit_code == 1
    assert '"valid": false' in result.output


def test_phase0_rejects_rejected(monkeypatch, stub_adapter):
    stub_adapter.create_item({"id": "CR-005", "title": "Test CR", "status": "rejected"})
    result = _invoke_check_status(monkeypatch, stub_adapter, "CR-005")
    assert result.exit_code == 1
    assert '"status": "rejected"' in result.output
