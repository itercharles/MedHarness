"""
Tests for DHF facade: traceability and implementation context.

Item CRUD, transition, and validate operations live in dhfkit —
these tests cover the medharness-specific adapter integration.
"""

from pathlib import Path

from medharness.core import MedHarnessCore


def test_build_traceability_chains_with_local_adapter():
    """build_traceability_chains must key by code not name.

    LocalDHFAdapter.list_item_types() returns human-readable name values
    (e.g. 'System Requirement') since the _item_type_dict fix. Keying
    prefix_map by name instead of code would make get_code() return display
    labels, breaking path comparisons against codes like ['SYS', 'SRS'].
    """
    from dhfkit.local_adapter import LocalDHFAdapter
    from dhfkit.tests.fixtures import create_test_dhf, populate_test_dhf_direct

    dhf_path = create_test_dhf()
    populate_test_dhf_direct(dhf_path)
    adapter = LocalDHFAdapter(dhf_path)
    core = MedHarnessCore(adapter)

    chains = core.build_traceability_chains(["SYS", "SRS"])

    assert len(chains) > 0, "expected at least one chain — prefix_map may be keyed by name instead of code"
    sys_items = [c for c in chains if c.get("SYS") is not None]
    assert len(sys_items) > 0, "no SYS items resolved — get_code() is not matching 'SYS' code"


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

