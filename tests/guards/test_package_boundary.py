"""`dhfkit` has a public surface; `medharness` must use it.

The documented boundary says `dhfkit` can be used standalone, which means it
has a contract. `medharness` read `adapter._config` in ten places — a private
attribute of a `dhfkit` class, reached across the package boundary. Any
refactor of `ItemStore` would have broken `medharness` silently, and
nothing checked.

The import direction was already guarded. What a consumer may *touch* was not.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Names that look private but are pytest hooks or dunder attributes.
_ALLOWED = {"_", "__class__", "__dict__", "__name__", "__doc__", "__module__"}


def _private_reaches() -> list[tuple[str, int, str]]:
    """`something._private` in medharness, where `something` came from dhfkit."""
    found = []
    for path in sorted((ROOT / "medharness").rglob("*.py")):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text())

        # Names bound from a dhfkit import or a dhfkit constructor call.
        dhfkit_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("dhfkit"):
                dhfkit_names.update(a.asname or a.name for a in node.names)
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                func = node.value.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name and name in dhfkit_names:
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            dhfkit_names.add(t.id)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            if not node.attr.startswith("_") or node.attr in _ALLOWED:
                continue
            base = getattr(node.value, "id", None)
            if base and base in dhfkit_names:
                found.append((str(path.relative_to(ROOT)), node.lineno,
                              f"{base}.{node.attr}"))
    return found


def _private_imports() -> list[tuple[str, int, str]]:
    """`from dhfkit... import _private` in medharness — the same reach, by import."""
    found = []
    for path in sorted((ROOT / "medharness").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("dhfkit"):
                found += [(str(path.relative_to(ROOT)), node.lineno, f"{node.module}.{a.name}")
                          for a in node.names
                          if a.name.startswith("_") and a.name not in _ALLOWED]
    return found


REACHES = _private_reaches() + _private_imports()


def test_the_scan_understands_the_code() -> None:
    """A scan that resolves nothing would make the assertion below vacuous."""
    sample = ast.parse((ROOT / "medharness" / "services" / "verify_tests.py").read_text())
    names = {
        a.asname or a.name
        for n in ast.walk(sample)
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("dhfkit")
        for a in n.names
    }
    assert names, "no dhfkit imports resolved in services/verify_tests.py — the scan is broken"


@pytest.mark.parametrize("where,line,expr", REACHES,
                         ids=[f"{w}:{ln}" for w, ln, _e in REACHES] or ["none"])
def test_no_private_dhfkit_attribute_is_read(where: str, line: int, expr: str) -> None:
    pytest.fail(
        f"{where}:{line} reads {expr}. dhfkit is meant to be usable standalone, "
        f"so it has a public surface — use it, or add to it."
    )


class TestThePublicSurfaceCoversWhatIsNeeded:
    def test_the_adapter_exposes_its_config(self) -> None:
        from dhfkit.item_store import ItemStore

        assert isinstance(
            getattr(ItemStore, "config", None), property
        ), "the config every gate needs is not on the public surface"

    def test_the_api_exposes_it_by_path(self, tmp_path: Path) -> None:
        from dhfkit.store import open_store
        from medharness.scaffold import replace_placeholders, scaffold_dhf

        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Boundary")
        config = open_store(tmp_path / "DHF").config
        assert config.project_name == "Boundary"
