"""Pytest configuration for CompliantFlow tests.

Registers custom markers for requirement traceability.
"""
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "verifies(req_id): mark test as verifying a specific requirement (e.g., SYS-030)"
    )


def pytest_collection_modifyitems(items):
    """Add requirement traceability information to test reports."""
    for item in items:
        # Extract verifies marker
        verifies_marker = item.get_closest_marker("verifies")
        if verifies_marker:
            req_id = verifies_marker.args[0]
            # Add to test metadata for reporting
            item.user_properties.append(("verifies", req_id))
