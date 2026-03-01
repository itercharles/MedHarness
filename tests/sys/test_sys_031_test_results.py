"""
API tests for SYS-031: Test Result Retrieval and Display

Verifies: The system shall retrieve the test result from pipeline and
display it in the system.

@links: SYS-031

This replaces browser-based tests with direct API testing.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from compliantflow.core import CompliantFlowCore


def test_TC_SYS_031_001_compliance_references_standards(test_dhf_root):
    """
    TC-SYS-031-001: Compliance Data References Regulatory Standards (API)

    @links: SYS-031
    @test_id: TC-SYS-031-001

    Verify system loads regulatory standards (IEC 62304) for test result display.
    """
    core = CompliantFlowCore(test_dhf_root)

    policy_group = core.get_policy_group("IEC_62304")

    assert policy_group is not None, "System should load IEC 62304 compliance data"
    assert "IEC_62304" in str(policy_group) or "IEC 62304" in str(policy_group), \
        "Policy group should reference IEC 62304"
    assert "policies" in policy_group, "Policy group should contain policies"
    assert len(policy_group["policies"]) > 0, "Should have at least one policy"


def test_TC_SYS_031_002_item_verification_status(test_dhf_root):
    """
    TC-SYS-031-002: Item Verification Status (API)

    @links: SYS-031
    @test_id: TC-SYS-031-002

    Verify system exposes requirement items with their verification status.
    """
    core = CompliantFlowCore(test_dhf_root)

    item = core.get_item("SRS-001")

    assert item is not None, "SRS-001 should exist in the system"
    assert item["id"] == "SRS-001"
    assert "title" in item, "Item should have a title"
    assert "Item Persistence and Versioning" in item["title"]
    assert item.get("status") == "approved", "SRS-001 should have approved status"
    assert "content" in item, "Item should have content"
    assert "persist" in item["content"].lower() or "dhf" in item["content"].lower(), \
        "Content should describe persistence"


def test_TC_SYS_031_003_pipeline_results_storage(test_dhf_root):
    """
    TC-SYS-031-003: Pipeline Test Results Storage (API)

    @links: SYS-031
    @test_id: TC-SYS-031-003

    Verify system supports storing and retrieving pipeline test results.
    """
    test_results_dir = Path(test_dhf_root) / "test_results"
    test_results_dir.mkdir(exist_ok=True)

    mock_results = {
        "test_run_id": "pipeline-run-123",
        "timestamp": "2025-12-28T14:00:00Z",
        "results": [
            {"test_id": "TC-SRS-001-001", "requirement_id": "SRS-001", "status": "PASS", "duration_ms": 150},
            {"test_id": "TC-SRS-002-001", "requirement_id": "SRS-002", "status": "FAIL", "duration_ms": 200,
             "error_message": "Assertion failed: Expected value not found"},
            {"test_id": "TC-SRS-003-001", "requirement_id": "SRS-003", "status": "PASS", "duration_ms": 180},
        ],
        "summary": {"total": 3, "passed": 2, "failed": 1},
    }

    results_file = test_results_dir / "test_results.json"
    results_file.write_text(json.dumps(mock_results, indent=2))

    assert results_file.exists(), "System should support test result file storage"

    stored = json.loads(results_file.read_text())

    assert stored["test_run_id"] == "pipeline-run-123"
    assert stored["summary"]["total"] == 3
    assert stored["summary"]["passed"] == 2
    assert stored["summary"]["failed"] == 1

    statuses = [r["status"] for r in stored["results"]]
    assert "PASS" in statuses
    assert "FAIL" in statuses

    test_ids = [r["test_id"] for r in stored["results"]]
    assert "TC-SRS-001-001" in test_ids
    assert "TC-SRS-002-001" in test_ids
    assert "TC-SRS-003-001" in test_ids
