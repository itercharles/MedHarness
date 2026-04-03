"""
Tests for CR-006: IDs are auto-generated and immutable.

@links: SYS-001
"""

import pytest
from utils.local_adapter import LocalDHFAdapter
from utils.exceptions import ValidationError


@pytest.fixture
def adapter(test_dhf_root):
    return LocalDHFAdapter(test_dhf_root, auto_commit=False)


def test_TC_SYS_035_001_id_auto_generated(adapter):
    """
    TC-SYS-035-001: create_item auto-generates an ID when none is supplied.

    @test_id: TC-SYS-035-001
    @links: SYS-001
    """
    item = adapter.create_item({"type": "SRS", "title": "Auto ID test"})
    assert item["id"].startswith("SRS-")


def test_TC_SYS_035_002_supplied_id_is_ignored(adapter):
    """
    TC-SYS-035-002: create_item ignores any caller-supplied id and always
    auto-generates one.

    @test_id: TC-SYS-035-002
    @links: SYS-001
    """
    item = adapter.create_item({"type": "SRS", "title": "Supplied ID ignored", "id": "SRS-999"})
    assert item["id"] != "SRS-999"
    assert item["id"].startswith("SRS-")


def test_TC_SYS_035_003_id_immutable_on_update(adapter):
    """
    TC-SYS-035-003: update_item raises ValidationError when the caller
    attempts to change the item's id.

    @test_id: TC-SYS-035-003
    @links: SYS-001
    """
    item = adapter.create_item({"type": "SRS", "title": "Immutability test"})
    uid = item["id"]

    with pytest.raises(ValidationError):
        adapter.update_item(uid, {"id": "SRS-999", "title": "Renamed"})
