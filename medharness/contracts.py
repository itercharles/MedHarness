"""Stable public contracts consumed by downstream repos.

Re-exports JUnit XML property constants from dhfkit so downstream
test reporters can import from a single logical package.

Example (pytest conftest)::

    from medharness.contracts import JUNIT_LINKS

    record_property(JUNIT_LINKS, "SYS-005,SYS-008")
"""

from dhfkit.junit_parser import (  # noqa: F401
    JUNIT_ID,
    JUNIT_LINKS,
    JUNIT_TITLE,
    JUNIT_REVIEWER,
    JUNIT_REVIEW_DATE,
    JUNIT_REVIEW_STATUS,
)

__all__ = [
    "JUNIT_ID",
    "JUNIT_LINKS",
    "JUNIT_TITLE",
    "JUNIT_REVIEWER",
    "JUNIT_REVIEW_DATE",
    "JUNIT_REVIEW_STATUS",
]
