"""Approval records are named by ULIDs, which must be well-formed and sort by time."""

from __future__ import annotations

import pytest

from medharness.services import approval
from medharness.services.approval import new_ulid


def test_a_ulid_is_26_characters_of_crockford_base32() -> None:
    uid = new_ulid()

    assert len(uid) == 26
    assert set(uid) <= set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    assert uid[0] in "01234567", "48 bits of time and 80 of randomness fill 128 bits"


def test_ulids_sort_by_the_time_they_were_made(monkeypatch: pytest.MonkeyPatch) -> None:
    made = []
    for ms in (1_000, 1_001, 5_000_000, 1_700_000_000_000):
        monkeypatch.setattr(approval.time, "time_ns", lambda ms=ms: ms * 1_000_000)
        made.append(new_ulid())

    assert made == sorted(made) and len(set(made)) == 4


def test_ulids_made_in_the_same_millisecond_differ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(approval.time, "time_ns", lambda: 1_700_000_000_000 * 1_000_000)

    assert len({new_ulid() for _ in range(100)}) == 100
