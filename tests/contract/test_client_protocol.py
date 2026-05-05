"""Contract tests for DHFClient — verifies it satisfies the WebTPS DHFAdapter Protocol."""

from pathlib import Path

from medharness.client import DHFClient


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
    client = DHFClient.__new__(DHFClient)  # bypass __init__ to test signature
    import inspect
    sig = inspect.signature(DHFClient.__init__)
    params = list(sig.parameters.keys())
    assert "dhf_path" in params
