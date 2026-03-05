"""Test results integration package."""

from dhf.result_store import ResultStore
from .junit_parser import ExecutionResult, parse_junit_xml

__all__ = [
    "ResultStore",
    "ExecutionResult",
    "parse_junit_xml",
]
