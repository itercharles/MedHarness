"""
Tests for SYS-025: Compliance-Aware PR Review Agent

Verifies that review_pr() correctly parses diffs, builds item chains,
and returns a structured checklist (with or without LLM backend).

@links: SYS-025
"""

import pytest
from compliantflow.core import CompliantFlowCore
from tests.stub_adapter import StubDHFAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_diff(item_ids):
    """Return a minimal unified diff that references the given item IDs."""
    lines = []
    for uid in item_ids:
        prefix = uid.split("-")[0].lower()
        lines.append(f"diff --git a/DHF/items/{prefix}/{uid}.yaml b/DHF/items/{prefix}/{uid}.yaml")
        lines.append(f"--- a/DHF/items/{prefix}/{uid}.yaml")
        lines.append(f"+++ b/DHF/items/{prefix}/{uid}.yaml")
        lines.append(f"+title: Updated title for {uid}")
    return "\n".join(lines)


def _adapter_with_items():
    """StubDHFAdapter pre-populated with a small traceability chain."""
    adapter = StubDHFAdapter()
    adapter.create_item({
        "id": "SYS-001",
        "type": "SYS",
        "title": "System shall process input",
        "satisfies": ["CRS-001"],
    })
    adapter.create_item({
        "id": "CRS-001",
        "type": "CRS",
        "title": "System must handle user data",
    })
    adapter.create_item({
        "id": "SRS-001",
        "type": "SRS",
        "title": "Input validation module",
        "derives_from": ["SYS-001"],
    })
    return adapter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_TC_SYS_025_001_empty_diff_returns_no_items():
    """
    TC-SYS-025-001: A diff with no DHF YAML files produces an empty changed_items list.

    @test_id: TC-SYS-025-001
    @links: SYS-025
    """
    adapter = StubDHFAdapter()
    core = CompliantFlowCore(adapter, llm_backend=None)
    result = core.review_pr("diff --git a/src/main.py b/src/main.py\n+print('hello')\n")
    assert result["changed_items"] == []
    assert result["chains_analyzed"] == []
    assert result["llm_available"] is False
    assert "_No DHF items detected_" in result["checklist"] or "No DHF items" in result["checklist"]


def test_TC_SYS_025_002_diff_items_parsed_correctly():
    """
    TC-SYS-025-002: Item IDs are correctly extracted from diff header lines.

    @test_id: TC-SYS-025-002
    @links: SYS-025
    """
    adapter = _adapter_with_items()
    core = CompliantFlowCore(adapter, llm_backend=None)
    diff = _make_diff(["SYS-001", "SRS-001"])
    result = core.review_pr(diff)
    assert set(result["changed_items"]) == {"SYS-001", "SRS-001"}


def test_TC_SYS_025_003_no_llm_returns_static_summary():
    """
    TC-SYS-025-003: Without an LLM backend, returns a static chain summary.

    @test_id: TC-SYS-025-003
    @links: SYS-025
    """
    adapter = _adapter_with_items()
    core = CompliantFlowCore(adapter, llm_backend=None)
    diff = _make_diff(["SYS-001"])
    result = core.review_pr(diff)
    assert result["llm_available"] is False
    assert "SYS-001" in result["checklist"]
    assert "LLM backend not configured" in result["checklist"]


def test_TC_SYS_025_004_llm_backend_called_and_checklist_returned():
    """
    TC-SYS-025-004: When an LLM backend is present, its output is used as the checklist.

    @test_id: TC-SYS-025-004
    @links: SYS-025
    """
    class _FakeLLM:
        def generate(self, prompt):
            return "- [ ] Update SRS-001 to reflect SYS-001 change\n- [ ] Verify TC links"

    adapter = _adapter_with_items()
    core = CompliantFlowCore(adapter, llm_backend=_FakeLLM())
    diff = _make_diff(["SYS-001"])
    result = core.review_pr(diff)
    assert result["llm_available"] is True
    assert "- [ ]" in result["checklist"]
    assert "SRS-001" in result["checklist"]


def test_TC_SYS_025_005_llm_backend_error_returns_fallback():
    """
    TC-SYS-025-005: When the LLM backend raises an exception, a fallback error
    message is returned instead of propagating the exception.

    @test_id: TC-SYS-025-005
    @links: SYS-025
    """
    class _BrokenLLM:
        def generate(self, prompt):
            raise RuntimeError("API timeout")

    adapter = _adapter_with_items()
    core = CompliantFlowCore(adapter, llm_backend=_BrokenLLM())
    diff = _make_diff(["SYS-001"])
    result = core.review_pr(diff)
    assert result["llm_available"] is True
    assert "LLM backend error" in result["checklist"] or "API timeout" in result["checklist"]


def test_TC_SYS_025_006_item_not_in_graph_still_listed():
    """
    TC-SYS-025-006: An item referenced in the diff but not in the graph is still
    included in changed_items (new item scenario).

    @test_id: TC-SYS-025-006
    @links: SYS-025
    """
    adapter = StubDHFAdapter()
    # SYS-099 is in the adapter but has no graph edges (no links to other items)
    adapter.create_item({"id": "SYS-099", "type": "SYS", "title": "New requirement"})
    core = CompliantFlowCore(adapter, llm_backend=None)
    diff = _make_diff(["SYS-099"])
    result = core.review_pr(diff)
    assert "SYS-099" in result["changed_items"]


def test_TC_SYS_025_007_duplicate_item_ids_in_diff_deduplicated():
    """
    TC-SYS-025-007: The same item ID appearing multiple times in a diff is
    deduplicated — it appears only once in changed_items.

    @test_id: TC-SYS-025-007
    @links: SYS-025
    """
    adapter = _adapter_with_items()
    core = CompliantFlowCore(adapter, llm_backend=None)
    # Repeat SYS-001 on three separate lines
    diff = "\n".join([
        "diff --git a/DHF/items/sys/SYS-001.yaml b/DHF/items/sys/SYS-001.yaml",
        "+++ b/DHF/items/sys/SYS-001.yaml",
        "--- a/DHF/items/sys/SYS-001.yaml",
        "+title: first change",
    ])
    result = core.review_pr(diff)
    assert result["changed_items"].count("SYS-001") == 1


def test_TC_SYS_025_008_result_keys_always_present():
    """
    TC-SYS-025-008: review_pr() always returns the four required keys regardless
    of whether items are found or LLM is available.

    @test_id: TC-SYS-025-008
    @links: SYS-025
    """
    adapter = StubDHFAdapter()
    core = CompliantFlowCore(adapter, llm_backend=None)
    result = core.review_pr("")
    assert set(result.keys()) >= {"checklist", "changed_items", "chains_analyzed", "llm_available"}
