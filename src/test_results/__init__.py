"""Test results integration module.

Provides unified interface for retrieving test verification status from
multiple sources: automated tests (CI/CD) and manual tests (YAML files).
"""

from .provider import TestResultsProvider

__all__ = ['TestResultsProvider']
