"""Stable public contracts consumed by downstream repos.

Re-exports JUnit XML property constants from dhfkit so downstream
test reporters can import from a single logical package.

Example (pytest conftest)::

    from medharness.contracts import JUNIT_LINKS

    record_property(JUNIT_LINKS, "SYS-005,SYS-008")

CONTRACT_VERSION tracks breaking changes to the public surface (adapter
protocol shape, JUnit property names, CLI JSON output keys). Downstream
repos may assert this value in their contract test suites to get an
explicit failure when upgrading rather than a silent behavioural regression.

Increment CONTRACT_VERSION whenever:
  - A DHFAdapter protocol method is added, removed, or has its signature changed
  - A JUnit property name constant is renamed or removed
  - A CLI command output key is renamed or removed
"""

# Bump this when the public contract surface breaks.
CONTRACT_VERSION = "1.0"

from dhfkit.junit_parser import (  # noqa: F401
    JUNIT_ID,
    JUNIT_LINKS,
    JUNIT_TITLE,
    JUNIT_REVIEWER,
    JUNIT_REVIEW_DATE,
    JUNIT_REVIEW_STATUS,
)

__all__ = [
    "CONTRACT_VERSION",
    "JUNIT_ID",
    "JUNIT_LINKS",
    "JUNIT_TITLE",
    "JUNIT_REVIEWER",
    "JUNIT_REVIEW_DATE",
    "JUNIT_REVIEW_STATUS",
]
