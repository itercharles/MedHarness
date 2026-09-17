"""An item medharness writes must account for its own existence.

`build dhf --write` changes the DHF outside any CR. Git records that "ci" did
it; nothing recorded why. A reviewer opening SOUP-003 found a component with no
account of where it came from.

The nine manifest parsers already carried `source` — it was dropped when the
item was built. Recording it is more honest than a CR reference would be:
backfilling an existing project's register is not a change request, but "this
row came from requirements.txt" is true either way.

`release baseline` needs none of this: a REL item carries `included_items`, the
CRs the release contains.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from medharness.services.soup_sync import sync_soup_items


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """The full scaffold: `dhfkit init` is minimal and configures no SOUP type."""
    import shutil

    templates = Path(__file__).resolve().parents[2] / "dhfkit" / "templates"
    dhf = tmp_path / "DHF"
    for src in ("config", "items"):
        shutil.copytree(templates / src, dhf / src, dirs_exist_ok=True)
    (tmp_path / "requirements.txt").write_text("flask==3.0.0\n")
    return tmp_path


def _soup_items(dhf: Path) -> list[dict]:
    from dhfkit.local_adapter import LocalDHFAdapter

    return [i for i in LocalDHFAdapter(dhf).list_items() if i.get("type") == "SOUP"]


class TestAnAutoCreatedItemRecordsItsOrigin:
    def test_the_manifest_is_recorded(self, project: Path) -> None:
        dhf = project / "DHF"
        sync_soup_items(dhf, [project / "requirements.txt"], write=True)
        created = [i for i in _soup_items(dhf) if i.get("name") == "flask"]
        assert created, "build dhf created nothing"
        assert created[0].get("source") == str(project / "requirements.txt"), (
            "the item does not say which manifest produced it; a reviewer sees a "
            "record with no account of why it exists"
        )

    def test_every_parser_carries_a_source(self) -> None:
        """The field only lands if each parser supplies it."""
        import ast
        import inspect

        from medharness.services import soup_sync

        missing = []
        for name, fn in vars(soup_sync).items():
            if not (name.startswith("parse_") and callable(fn)):
                continue
            literals = {
                n.value for n in ast.walk(ast.parse(inspect.getsource(fn)))
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            }
            if "source" not in literals:
                missing.append(name)
        assert not missing, f"parsers that drop the manifest path: {missing}"


def test_a_release_record_names_the_crs_it_contains() -> None:
    """REL needs no separate provenance — `included_items` is it."""
    import inspect

    from medharness.services import release_baseline

    source = inspect.getsource(release_baseline.build_release_baseline)
    assert '"included_items"' in source, (
        "a REL item no longer records which CRs the release contains, so a "
        "release record would have no change attribution at all"
    )
