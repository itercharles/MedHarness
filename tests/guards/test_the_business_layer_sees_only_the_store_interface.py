"""`medharness` reaches the item store through `dhfkit.store`, nothing behind it.

The checks and build steps must not know whether items are YAML files or live in
another system; that is what makes an adapter (`dhfkit.adapter`) enough to add one.
Importing the concrete store, the YAML loader or an adapter from `medharness`
would quietly couple a check to one of them.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from dhfkit.item_store import ItemStore
from dhfkit.store import DHFStore

ROOT = Path(__file__).resolve().parents[2]
BEHIND_THE_INTERFACE = ("dhfkit.item_store", "dhfkit.local_adapter", "dhfkit.repository", "dhfkit.adapter")


def _imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
    return found


FILES = sorted((ROOT / "medharness").rglob("*.py"))


def test_the_scan_found_the_package() -> None:
    assert len(FILES) > 30


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_module_imports_what_sits_behind_the_store(path: Path) -> None:
    offenders = sorted(m for m in _imports(path) if m.startswith(BEHIND_THE_INTERFACE))
    assert not offenders, (
        f"{path.relative_to(ROOT)} imports {offenders}; use `dhfkit.store.open_store` "
        f"and the `DHFStore` interface"
    )


def test_the_store_the_package_ships_implements_the_interface() -> None:
    declared = [n for n in vars(DHFStore) if not n.startswith("_")]
    assert len(declared) > 10, "the interface lost its methods"
    missing = [n for n in declared if not hasattr(ItemStore, n)]
    assert not missing, f"ItemStore lacks {missing}, which the business layer may call"
