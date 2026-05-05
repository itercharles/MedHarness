"""Tests for latest-only ResultStore behavior."""

from __future__ import annotations

import yaml

from dhfkit.result_store import ResultStore


def test_record_execution_overwrites_latest_record(populated_dhf):
    store = ResultStore(populated_dhf)

    store.record_execution(
        tc_id="TC-SYS-001",
        testing_status="FAIL",
        tester="ci",
        run_id="1",
        links=["SYS-001"],
        title="System test",
    )
    store.record_execution(
        tc_id="TC-SYS-001",
        testing_status="PASS",
        tester="ci",
        run_id="2",
    )

    latest = store.get_latest("TC-SYS-001")
    assert latest["testing_status"] == "PASS"
    assert latest["run_id"] == "2"
    assert latest["title"] == "System test"
    assert latest["links"] == ["SYS-001"]
    assert store.get_history("TC-SYS-001") == [latest]

    data = yaml.safe_load((populated_dhf / "test-results" / "results.yaml").read_text())
    assert isinstance(data["TC-SYS-001"], dict)


def test_record_executions_batches_file_write(populated_dhf):
    store = ResultStore(populated_dhf)

    store.record_executions([
        {
            "tc_id": "TC-SYS-001",
            "testing_status": "PASS",
            "tester": "ci",
            "run_id": "1",
            "links": ["SYS-001"],
        },
        {
            "tc_id": "TC-SYS-002",
            "testing_status": "FAIL",
            "tester": "ci",
            "run_id": "1",
            "links": ["SYS-002"],
        },
    ])

    records = store.get_all()
    assert set(records) == {"TC-SYS-001", "TC-SYS-002"}
    assert records["TC-SYS-001"]["testing_status"] == "PASS"
    assert records["TC-SYS-002"]["testing_status"] == "FAIL"


def test_load_old_history_format_keeps_latest(populated_dhf):
    path = populated_dhf / "test-results" / "results.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump({
            "TC-SYS-001": [
                {"id": "TC-SYS-001", "testing_status": "PASS", "run_id": "2"},
                {"id": "TC-SYS-001", "testing_status": "FAIL", "run_id": "1"},
            ],
            "TC-SYS-002": {"id": "TC-SYS-002", "testing_status": "PASS"},
        }),
        encoding="utf-8",
    )

    store = ResultStore(populated_dhf)
    assert store.get_latest("TC-SYS-001")["run_id"] == "2"
    assert store.get_latest("TC-SYS-002")["testing_status"] == "PASS"

    store.record_execution("TC-SYS-001", "PASS", run_id="3")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["TC-SYS-001"]["run_id"] == "3"
    assert isinstance(data["TC-SYS-001"], dict)
