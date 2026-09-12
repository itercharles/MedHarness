"""Where things live inside a DHF.

A consumer that joins these paths itself is coupled to this backend's layout.
Keeping them here means `medharness` can ask without knowing, and a different
store can answer differently.
"""

from __future__ import annotations

from pathlib import Path


def config_file(dhf_root: Path | str, name: str) -> Path | None:
    """Path to a project config file, or None when it is absent.

    Takes the root rather than an adapter: locating a file must not require a
    loadable project config, or a store with no `global.yaml` yet cannot be
    inspected at all.
    """
    candidate = Path(dhf_root) / "config" / name
    return candidate if candidate.is_file() else None
