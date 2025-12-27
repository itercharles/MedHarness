#!/usr/bin/env python3
"""
Generate requirement-to-test traceability report.

Scans test files for @pytest.mark.verifies() markers and generates
a report showing which tests verify which requirements.

Usage:
    python scripts/generate_test_traceability.py
"""
import ast
import sys
from pathlib import Path
from collections import defaultdict


def extract_verifies_markers(test_file):
    """Extract requirement IDs from @pytest.mark.verifies() decorators."""
    with open(test_file) as f:
        tree = ast.parse(f.read(), filename=str(test_file))
    
    test_to_req = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            # Look for @pytest.mark.verifies decorator
            for decorator in node.decorator_list:
                if (isinstance(decorator, ast.Call) and
                    isinstance(decorator.func, ast.Attribute) and
                    decorator.func.attr == 'verifies'):
                    # Extract requirement ID from decorator argument
                    if decorator.args:
                        req_id = decorator.args[0].value
                        test_name = node.name
                        test_to_req[test_name] = req_id
    
    return test_to_req


def generate_traceability_report():
    """Generate traceability report from all test files."""
    tests_dir = Path(__file__).parent.parent / "tests"
    
    # Collect all test-to-requirement mappings
    req_to_tests = defaultdict(list)
    
    for test_file in tests_dir.rglob("test_*.py"):
        markers = extract_verifies_markers(test_file)
        for test_name, req_id in markers.items():
            test_path = test_file.relative_to(tests_dir.parent)
            req_to_tests[req_id].append(f"{test_path}::{test_name}")
    
    # Generate report
    print("=" * 80)
    print("REQUIREMENT-TO-TEST TRACEABILITY REPORT")
    print("=" * 80)
    print()
    
    if not req_to_tests:
        print("No tests with @pytest.mark.verifies() markers found.")
        return
    
    for req_id in sorted(req_to_tests.keys()):
        print(f"📋 {req_id}")
        for test in req_to_tests[req_id]:
            print(f"   ✓ {test}")
        print()
    
    print("=" * 80)
    print(f"Total Requirements Verified: {len(req_to_tests)}")
    print(f"Total Tests: {sum(len(tests) for tests in req_to_tests.values())}")
    print("=" * 80)


if __name__ == "__main__":
    generate_traceability_report()
