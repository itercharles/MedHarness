"""Where a DHF's items are kept.

The item store (`ItemStore`) owns everything that is the same wherever the
items live: the doc-type schema, link checks, the lifecycle, and the shape of
what callers get back. An adapter owns only persistence, so a new place to keep
items — an issue tracker, a database — is these five methods. The project's
`config/` and `documents/` stay in the repository whichever adapter is chosen.

Choose one in `DHF/config/global.yaml`:

    store:
      type: yaml          # the default: one YAML file per item under DHF/items/
      # any other type is an installed adapter, plus its own settings

An adapter is installed as an entry point in the `dhfkit.adapters` group whose
name is the `type`; it is called with the settings, the project config and the
DHF root, and returns an object that satisfies `DHFAdapter`.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Protocol

from dhfkit.exceptions import DHFDataError
from dhfkit.models.item import Item


class DHFAdapter(Protocol):
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


def _installed() -> dict[str, Any]:
    return {ep.name: ep for ep in entry_points(group="dhfkit.adapters")}


def resolve_adapter(config: Any, dhf_root: Path) -> DHFAdapter:
    """The adapter `store:` in global.yaml names; YAML files when it names none."""
    settings = dict(getattr(config, "store", None) or {})
    kind = str(settings.pop("type", "yaml"))
    if kind == "yaml":
        from dhfkit.local_adapter import LocalDHFAdapter

        return LocalDHFAdapter(dhf_root / "items", config)
    installed = _installed()
    if kind not in installed:
        available = ", ".join(sorted({"yaml", *installed}))
        raise DHFDataError(
            f"store type {kind!r} in {dhf_root / 'config' / 'global.yaml'} is not installed. "
            f"Installed: {available}."
        )
    return installed[kind].load()(settings=settings, config=config, dhf_root=dhf_root)
