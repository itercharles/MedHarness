"""
Tests for SYS-039: CR check-status Phase 0 gate behavior.

Verifies that only in-progress CR workflow states pass the gate.

@links: SYS-039
"""

from click.testing import CliRunner

from compliantflow.cli import main
from compliantflow.core import CompliantFlowCore


def _invoke_check_status(monkeypatch, stub_adapter, cr_id: str):
    core = CompliantFlowCore(stub_adapter)
    monkeypatch.setattr("compliantflow.cli._make_core", lambda ctx: core)
    runner = CliRunner()
    return runner.invoke(main, ["cr", "check-status", cr_id])


def test_TC_SYS_039_001_phase0_accepts_new(monkeypatch, stub_adapter):
    """
    TC-SYS-039-001: Phase 0 accepts CRs in new status.

    @test_id: TC-SYS-039-001
    @links: SYS-039
    """
    stub_adapter.create_item({"id": "CR-001", "title": "Test CR", "status": "new"})
    result = _invoke_check_status(monkeypatch, stub_adapter, "CR-001")
    assert result.exit_code == 0
    assert '"valid": true' in result.output


def test_TC_SYS_039_002_phase0_accepts_analyzing(monkeypatch, stub_adapter):
    """
    TC-SYS-039-002: Phase 0 accepts CRs in analyzing status.

    @test_id: TC-SYS-039-002
    @links: SYS-039
    """
    stub_adapter.create_item({"id": "CR-002", "title": "Test CR", "status": "analyzing"})
    result = _invoke_check_status(monkeypatch, stub_adapter, "CR-002")
    assert result.exit_code == 0
    assert '"status": "analyzing"' in result.output


def test_TC_SYS_039_003_phase0_accepts_developing(monkeypatch, stub_adapter):
    """
    TC-SYS-039-003: Phase 0 accepts CRs in developing status.

    @test_id: TC-SYS-039-003
    @links: SYS-039
    """
    stub_adapter.create_item({"id": "CR-003", "title": "Test CR", "status": "developing"})
    result = _invoke_check_status(monkeypatch, stub_adapter, "CR-003")
    assert result.exit_code == 0
    assert '"status": "developing"' in result.output


def test_TC_SYS_039_004_phase0_rejects_completed(monkeypatch, stub_adapter):
    """
    TC-SYS-039-004: Phase 0 rejects CRs in completed status.

    @test_id: TC-SYS-039-004
    @links: SYS-039
    """
    stub_adapter.create_item({"id": "CR-004", "title": "Test CR", "status": "completed"})
    result = _invoke_check_status(monkeypatch, stub_adapter, "CR-004")
    assert result.exit_code == 1
    assert '"valid": false' in result.output


def test_TC_SYS_039_005_phase0_rejects_rejected(monkeypatch, stub_adapter):
    """
    TC-SYS-039-005: Phase 0 rejects CRs in rejected status.

    @test_id: TC-SYS-039-005
    @links: SYS-039
    """
    stub_adapter.create_item({"id": "CR-005", "title": "Test CR", "status": "rejected"})
    result = _invoke_check_status(monkeypatch, stub_adapter, "CR-005")
    assert result.exit_code == 1
    assert '"status": "rejected"' in result.output
