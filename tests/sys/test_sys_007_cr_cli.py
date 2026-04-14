"""
Tests for SYS-007: cr_git_evidence policy check.

Covers:
  - `cr_git_evidence` policy check reading from an artifact file

CLI integration tests (cr check-status, cr generate-report, test import/status/list)
live in the compliantflow-dhf repository where LocalDHFAdapter is available.

@links: SYS-006
"""

import json
import os
import tempfile

import pytest

from compliantflow.core import CompliantFlowCore
from compliantflow.policy import PolicyEngine


def test_TC_SYS_007_005_cr_git_evidence_pass(stub_adapter):
    """
    TC-SYS-007-005: cr_git_evidence returns True when the report JSON
    contains at least one commit.

    @test_id: TC-SYS-007-005
    @links: SYS-006, SYS-010
    """
    core = CompliantFlowCore(stub_adapter)
    engine = PolicyEngine(core)

    report_data = {
        "cr_id": "CR-002",
        "commits": [{"sha": "abc123", "message": "feat: implement CR-002"}],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(report_data, f)
        tmp_path = f.name

    try:
        passed, details, evidence = engine._check_cr_git_evidence(report_path=tmp_path)
    finally:
        os.unlink(tmp_path)

    assert passed is True
    assert evidence["commit_count"] == 1
    assert "CR-002" in details


def test_TC_SYS_007_006_cr_git_evidence_no_commits_fails(stub_adapter):
    """
    TC-SYS-007-006: cr_git_evidence returns False when the report JSON
    has an empty commits list.

    @test_id: TC-SYS-007-006
    @links: SYS-006, SYS-010
    """
    core = CompliantFlowCore(stub_adapter)
    engine = PolicyEngine(core)

    report_data = {"cr_id": "CR-001", "commits": []}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(report_data, f)
        tmp_path = f.name

    try:
        passed, details, evidence = engine._check_cr_git_evidence(report_path=tmp_path)
    finally:
        os.unlink(tmp_path)

    assert passed is False
    assert evidence["commit_count"] == 0


def test_TC_SYS_007_007_cr_git_evidence_env_var(stub_adapter, monkeypatch):
    """
    TC-SYS-007-007: cr_git_evidence reads from COMPLIANTFLOW_CR_REPORT_PATH
    when no report_path param is provided.

    @test_id: TC-SYS-007-007
    @links: SYS-006, SYS-010
    """
    core = CompliantFlowCore(stub_adapter)
    engine = PolicyEngine(core)

    report_data = {
        "cr_id": "CR-002",
        "commits": [{"sha": "def456", "message": "fix: CR-002 follow-up"}],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(report_data, f)
        tmp_path = f.name

    try:
        monkeypatch.setenv("COMPLIANTFLOW_CR_REPORT_PATH", tmp_path)
        passed, details, evidence = engine._check_cr_git_evidence()
    finally:
        os.unlink(tmp_path)
        monkeypatch.delenv("COMPLIANTFLOW_CR_REPORT_PATH", raising=False)

    assert passed is True
    assert evidence["commit_count"] == 1


def test_TC_SYS_007_008_cr_git_evidence_no_path_fails(stub_adapter, monkeypatch):
    """
    TC-SYS-007-008: cr_git_evidence returns False when neither report_path
    param nor env var is set.

    @test_id: TC-SYS-007-008
    @links: SYS-006, SYS-010
    """
    core = CompliantFlowCore(stub_adapter)
    engine = PolicyEngine(core)

    monkeypatch.delenv("COMPLIANTFLOW_CR_REPORT_PATH", raising=False)
    passed, details, _ = engine._check_cr_git_evidence()
    assert passed is False
    assert "not set" in details
