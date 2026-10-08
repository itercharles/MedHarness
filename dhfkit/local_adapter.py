"""LocalDHFAdapter — a DHF whose items are YAML files in the project's repository.

One adapter per system, one file each: this is the local one, and a Jira
adapter would sit beside it as `jira_adapter.py`. Both implement `DHFAdapter`
(`dhfkit.adapter`) and nothing else; the schema, links, IDs and lifecycle are
`ItemStore`'s, so they do not change with the adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dhfkit.models.item import Item
from dhfkit.repository.git import item_ids_ever_added
from dhfkit.repository.loader import ItemLoader
from dhfkit.repository.saver import ItemSaver


class LocalDHFAdapter:
    """One YAML file per item, under `DHF/items/`."""

    tracks_files = True

    def __init__(self, items_dir: Path, project_config: Any):
        self.items_dir = items_dir
        self._loader = ItemLoader(items_dir, project_config=project_config)
        self._saver = ItemSaver(items_dir, project_config=project_config)

    def load_all(self) -> list[Item]:
        return self._loader.load_all()

    def load_by_uid(self, uid: str) -> Item | None:
        return self._loader.load_by_uid(uid)

    def save(self, item: Item) -> None:
        # An item that was read carries the file it came from; writing there
        # keeps a DHF laid out before the default directories changed intact.
        origin = getattr(item, "file_path", None)
        self._saver.save(item, Path(origin) if origin else None)

    def used_ids(self) -> set[str]:
        return {i.uid for i in self.load_all()} | item_ids_ever_added(self.items_dir)

    def integrity_errors(self) -> list[str]:
        """Two files claiming one ID make every reference to it ambiguous.

        `get_item` returns whichever the loader saw first and the other exists
        unreferenced. The schema passes both files as individually valid, so
        nothing else reports it.
        """
        seen: dict[str, list[str]] = {}
        if not self.items_dir.is_dir():
            return []
        for path in sorted(self.items_dir.rglob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue  # a file that will not parse is the loader's to report
            if not isinstance(data, dict):
                continue
            uid = str(data.get("id") or "").strip()
            if uid:
                seen.setdefault(uid, []).append(str(path.relative_to(self.items_dir.parent)))
        return [
            f"Duplicate item ID {uid!r} in: {', '.join(paths)}"
            for uid, paths in sorted(seen.items()) if len(paths) > 1
        ]
