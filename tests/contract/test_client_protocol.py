"""Contract tests for DHFAdapter protocol surface.

Verifies that DHFClient and LocalDHFAdapter satisfy the DHFAdapter Protocol,
and that CONTRACT_VERSION is asserted so downstream repos get an explicit
failure on upgrade rather than a silent regression.
"""

import inspect
from pathlib import Path

from medharness.client import DHFClient
from medharness.contracts import CONTRACT_VERSION
from medharness.adapters.protocol import DHFAdapter
from dhfkit.local_adapter import LocalDHFAdapter


# ── Contract version ──────────────────────────────────────────────────────────

def test_contract_version_is_defined():
    assert isinstance(CONTRACT_VERSION, str) and CONTRACT_VERSION


def test_contract_version_is_stable():
    # Downstream repos pin against this string. Bump it in contracts.py when
    # the adapter surface changes; change the expected value here at the same time.
    assert CONTRACT_VERSION == "1.0"


# ── DHFClient public surface ───────────────────────────────────────────────────

def test_dhf_import_works():
    from medharness import DHFClient as ImportedClient
    assert ImportedClient is DHFClient


def test_client_has_required_methods():
    methods = [
        "list_items", "get_item", "create_item", "update_item",
        "transition_item", "get_document", "get_cr_context",
    ]
    for name in methods:
        assert hasattr(DHFClient, name), f"DHFClient missing method: {name}"


def test_client_init_accepts_path():
    sig = inspect.signature(DHFClient.__init__)
    assert "dhf_path" in sig.parameters


# ── DHFAdapter Protocol completeness on LocalDHFAdapter ───────────────────────

_PROTOCOL_METHODS = [
    # Item CRUD
    "get_item", "list_items", "create_item", "update_item", "delete_item",
    # Lifecycle
    "execute_transition", "get_available_transitions",
    # Validation
    "validate_schema", "validate_traceability",
    # Item type metadata
    "get_item_type", "list_item_types", "get_lifecycle_states",
    # Test results
    "get_test_result", "get_all_test_results", "get_test_result_items",
    "import_results_from_file", "record_test_result", "pull_results_from_artifacts",
    # Documents
    "get_document", "list_documents",
    # CR context
    "get_implementation_context",
    # Compliance runs
    "record_compliance_run", "get_compliance_runs",
    # Doc generation
    "get_available_doc_types", "generate_doc", "export_pdf",
]


def test_local_adapter_implements_all_protocol_methods():
    missing = [m for m in _PROTOCOL_METHODS if not hasattr(LocalDHFAdapter, m)]
    assert not missing, f"LocalDHFAdapter missing protocol methods: {missing}"


def test_local_adapter_satisfies_runtime_protocol():
    # DHFAdapter is @runtime_checkable — isinstance check validates structural
    # compatibility without constructing a real adapter instance.
    assert issubclass(LocalDHFAdapter, DHFAdapter), (
        "LocalDHFAdapter no longer satisfies the DHFAdapter Protocol. "
        "Check that all required methods are present with matching signatures."
    )


def test_protocol_method_signatures_stable():
    """Spot-check that core method signatures have the expected parameters.

    Adding optional parameters is fine; removing or renaming required ones is a
    breaking change that must increment CONTRACT_VERSION.
    """
    checks = {
        "create_item": ["data", "author", "cr_id"],
        "update_item": ["uid", "data", "author", "cr_id"],
        "execute_transition": ["item_id", "to_state", "performed_by"],
        "get_item": ["uid"],
        "list_items": ["doc_type"],
    }
    for method_name, expected_params in checks.items():
        method = getattr(LocalDHFAdapter, method_name)
        sig = inspect.signature(method)
        actual = list(sig.parameters.keys())
        for param in expected_params:
            assert param in actual, (
                f"LocalDHFAdapter.{method_name} is missing parameter '{param}'. "
                f"This is a breaking change — bump CONTRACT_VERSION."
            )
