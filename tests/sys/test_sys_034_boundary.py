"""
Tests for SYS-034: Component Boundary Isolation

Verifies that the compliantflow analysis engine (src/compliantflow/) does not
directly import DHF I/O layer modules outside the adapter boundary.

Prohibited imports in src/compliantflow/ (use adapter instead):
  utils.repository.*   — ItemLoader, ItemSaver, GitRepository
  utils.result_store   — ResultStore
  utils.junit_parser   — parse_junit_xml, ExecutionResult
  utils.document_generation — DocumentGenerator

LocalDHFAdapter lives in DHF/utils/local_adapter.py (CR-019 boundary move).
It may import compliantflow.domain.* (shared vocabulary) but not
compliantflow analysis-layer modules (traceability, mixins, core, cli).

Boundary rules documented in DHF/utils/docs/design.md (DESIGN-013).
"""

import ast
import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

_COMPLIANTFLOW_SRC = Path(__file__).parent.parent.parent / "src" / "compliantflow"
_DHF_UTILS = Path(__file__).parent.parent.parent / "DHF" / "utils"
_DHF_LOCAL_ADAPTER = _DHF_UTILS / "local_adapter.py"

_PROHIBITED_MODULES = [
    "utils.repository",
    "utils.result_store",
    "utils.junit_parser",
    "utils.document_generation",
]


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


def _find_py_files(directory: Path) -> list[Path]:
    files = []
    for f in directory.rglob("*.py"):
        files.append(f)
    return files


class TestComponentBoundary:
    """SYS-034: compliantflow must not directly import DHF I/O modules."""

    def test_TC_SYS_034_001_no_prohibited_imports_outside_adapter(self):
        """
        TC-SYS-034-001: No file in src/compliantflow/ imports prohibited DHF I/O
        modules. LocalDHFAdapter has been moved to DHF/utils/local_adapter.py, so
        src/compliantflow/ no longer contains any adapter implementation.

        @test_id: TC-SYS-034-001
        @links: SYS-034
        """
        violations = []

        py_files = _find_py_files(_COMPLIANTFLOW_SRC)

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

    def test_TC_SYS_034_002_dhf_local_adapter_uses_utils(self):
        """
        TC-SYS-034-002: DHF/utils/local_adapter.py (the adapter implementation)
        imports only utils.* modules (DHF layer) and compliantflow.domain.* (shared
        vocabulary). It must NOT import compliantflow analysis-layer modules.
        LocalDHFAdapter was moved from src/compliantflow/adapters/local.py to
        DHF/utils/local_adapter.py as part of CR-019 boundary cleanup.

        compliantflow.domain.* is the shared domain vocabulary (pure data models)
        that the adapter uses to produce ProjectSchema for CompliantFlowCore.
        Analysis-layer modules (traceability, mixins, core) remain prohibited.

        @test_id: TC-SYS-034-002
        @links: SYS-034
        """
        assert _DHF_LOCAL_ADAPTER.exists(), (
            f"LocalDHFAdapter not found at {_DHF_LOCAL_ADAPTER} — "
            "was it moved back to src/compliantflow/adapters/?"
        )

        imports = _collect_imports(_DHF_LOCAL_ADAPTER)
        utils_imports = [i for i in imports if i.startswith("utils.")]

        # Analysis-layer modules that the adapter must never import
        _PROHIBITED_CF_MODULES = [
            "compliantflow.traceability",
            "compliantflow.mixins",
            "compliantflow.core",
            "compliantflow.cli",
        ]
        prohibited_cf_imports = [
            i for i in imports
            if any(i == m or i.startswith(m + ".") for m in _PROHIBITED_CF_MODULES)
        ]

        assert len(utils_imports) > 0, (
            "DHF/utils/local_adapter.py should import from utils.* "
            "(it is the DHF-layer adapter implementation)"
        )
        assert not prohibited_cf_imports, (
            "DHF/utils/local_adapter.py must NOT import compliantflow analysis-layer modules. "
            "Only compliantflow.domain.* (shared vocabulary) is permitted. "
            f"Found prohibited: {prohibited_cf_imports}"
        )

    def test_TC_SYS_034_003_no_local_adapter_in_src(self):
        """
        TC-SYS-034-003: src/compliantflow/adapters/local.py does NOT exist —
        the LocalDHFAdapter implementation lives only in DHF/utils/local_adapter.py.

        @test_id: TC-SYS-034-003
        @links: SYS-034
        """
        old_location = _COMPLIANTFLOW_SRC / "adapters" / "local.py"
        assert not old_location.exists(), (
            f"LocalDHFAdapter implementation found at old location {old_location}. "
            "It should only exist at DHF/utils/local_adapter.py (CR-019 boundary move)."
        )
