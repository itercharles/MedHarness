"""
Tests for SYS-034: Component Boundary Isolation

Verifies that the compliantflow analysis engine (src/compliantflow/) does not
directly import DHF I/O layer modules from outside the adapter boundary.

Permitted imports anywhere in src/compliantflow/:
  utils.models.*       — shared data DTOs (Item, ProjectConfig, etc.)
  utils.exceptions     — ValidationError

Prohibited imports (except in adapters/local.py which IS the adapter):
  utils.repository.*   — ItemLoader, ItemSaver, GitRepository
  utils.result_store   — ResultStore
  utils.junit_parser   — parse_junit_xml, ExecutionResult
  utils.document_generation — DocumentGenerator

@links: SYS-034
"""

import ast
import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

_COMPLIANTFLOW_SRC = Path(__file__).parent.parent.parent / "src" / "compliantflow"

_PROHIBITED_MODULES = [
    "utils.repository",
    "utils.result_store",
    "utils.junit_parser",
    "utils.document_generation",
]

_ADAPTER_IMPL = _COMPLIANTFLOW_SRC / "adapters" / "local.py"


def _collect_imports(filepath: Path) -> list[str]:
    """Return all imported module names found in a Python source file."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _find_py_files(directory: Path, exclude: Path | None = None) -> list[Path]:
    files = []
    for f in directory.rglob("*.py"):
        if exclude and f.resolve() == exclude.resolve():
            continue
        files.append(f)
    return files


class TestComponentBoundary:
    """SYS-034: compliantflow must not directly import DHF I/O modules."""

    def test_TC_SYS_034_001_no_prohibited_imports_outside_adapter(self):
        """
        TC-SYS-034-001: No file in src/compliantflow/ (except adapters/local.py)
        imports prohibited DHF I/O modules.

        @test_id: TC-SYS-034-001
        @links: SYS-034
        """
        violations = []

        py_files = _find_py_files(_COMPLIANTFLOW_SRC, exclude=_ADAPTER_IMPL)

        for filepath in py_files:
            imports = _collect_imports(filepath)
            relative = filepath.relative_to(_COMPLIANTFLOW_SRC.parent.parent)
            for imp in imports:
                for prohibited in _PROHIBITED_MODULES:
                    if imp == prohibited or imp.startswith(prohibited + "."):
                        violations.append(
                            f"{relative}: imports '{imp}' (prohibited — use adapter)"
                        )

        assert not violations, (
            "Component boundary violations found:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_TC_SYS_034_002_adapter_impl_may_import_utils(self):
        """
        TC-SYS-034-002: adapters/local.py (the adapter implementation) is permitted
        to import any utils.* module.

        @test_id: TC-SYS-034-002
        @links: SYS-034
        """
        assert _ADAPTER_IMPL.exists(), f"Adapter impl not found at {_ADAPTER_IMPL}"

        imports = _collect_imports(_ADAPTER_IMPL)
        utils_imports = [i for i in imports if i.startswith("utils.")]
        assert len(utils_imports) > 0, (
            "adapters/local.py should import from utils.* "
            "(it is the adapter implementation)"
        )
