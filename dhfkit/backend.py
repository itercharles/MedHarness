"""Where a DHF's items are kept.

The item store (`LocalDHFAdapter`) owns everything that is the same wherever the
items live: the doc-type schema, link checks, the lifecycle, and the shape of
what callers get back. A backend owns only persistence, so a new place to keep
items — an issue tracker, a database — is these five methods. The project's
`config/` and `documents/` stay in the repository whichever backend is chosen.

Choose one in `DHF/config/global.yaml`:

    store:
      type: yaml          # the default: one YAML file per item under DHF/items/
      # any other type is an installed backend, plus its own settings

A backend is installed as an entry point in the `dhfkit.backends` group whose
name is the `type`; it is called with the settings, the project config and the
DHF root, and returns an object that satisfies `ItemBackend`.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Protocol

import yaml

from dhfkit.exceptions import DHFDataError
from dhfkit.models.item import Item
from dhfkit.repository.git import item_ids_ever_added
from dhfkit.repository.loader import ItemLoader
from dhfkit.repository.saver import ItemSaver


class ItemBackend(Protocol):
    #: True when items are files in the project's Git repository. Commands that
    #: read the repository's diff (`verify changes`, `build plan`, `build code`)
    #: need it; without it they say so instead of answering wrongly.
    tracks_files: bool

    def load_all(self) -> list[Item]:
        """Every item. Raises `ValidationError` for one that cannot be read."""

    def load_by_uid(self, uid: str) -> Item | None: ...

    def save(self, item: Item) -> None:
        """Create the item, or replace the one with the same `uid`."""

    def delete(self, uid: str) -> bool: ...

    def used_ids(self) -> set[str]:
        """Every ID ever allocated, deleted items included.

        An ID that once meant one requirement must never mean another: every
        link, CR and test that names it would silently retarget.
        """

    def integrity_errors(self) -> list[str]:
        """Problems in the store as a whole, such as one ID held by two records."""


class YamlBackend:
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

    def delete(self, uid: str) -> bool:
        return self._saver.delete(uid)

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


def _installed() -> dict[str, Any]:
    return {ep.name: ep for ep in entry_points(group="dhfkit.backends")}


def resolve_backend(config: Any, dhf_root: Path) -> ItemBackend:
    """The backend `store:` in global.yaml names; YAML files when it names none."""
    settings = dict(getattr(config, "store", None) or {})
    kind = str(settings.pop("type", "yaml"))
    if kind == "yaml":
        return YamlBackend(dhf_root / "items", config)
    installed = _installed()
    if kind not in installed:
        available = ", ".join(sorted({"yaml", *installed}))
        raise DHFDataError(
            f"store type {kind!r} in {dhf_root / 'config' / 'global.yaml'} is not installed. "
            f"Installed: {available}."
        )
    return installed[kind].load()(settings=settings, config=config, dhf_root=dhf_root)
