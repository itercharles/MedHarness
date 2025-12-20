"""Test results integration module.

Provides unified interface for retrieving test verification status from
multiple sources: automated tests (CI/CD) and manual tests (YAML files).
"""

from .provider import VerificationStatusProvider

__all__ = ['VerificationStatusProvider']
