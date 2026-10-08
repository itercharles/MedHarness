"""YAML file saver for items."""

from pathlib import Path
import json
import os
import yaml
from typing import Optional, Dict, Any
from dhfkit.models.item import Item


class ItemSaver:
    """Save items to YAML files."""

    def __init__(
        self,
        specs_dir: Path,
        project_config: Optional[Any] = None
    ):
        """
        Initialize saver.

        Args:
            specs_dir: Path to specifications directory
            project_config: Optional ProjectConfig for directory mapping
        """
        self.specs_dir = specs_dir
        self.project_config = project_config
        self._prefix_map = None

    def save(self, item: Item, file_path: Optional[Path] = None) -> Path:
        """Write an item to ``file_path``, or to its doc type's directory when new.

        An existing item is rewritten where it was read from: a DHF laid out
        before the default directories changed keeps its layout, rather than
        gaining a second file with the same ID.
        """
        if file_path is None:
            save_dir = self._get_directory_for_prefix(item.prefix)
            save_dir.mkdir(parents=True, exist_ok=True)
            file_path = save_dir / f"{item.uid}.yaml"

        data = item.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude_unset=True,
            mode='json'
        )

        data.pop('uid', None)
        data.pop('text', None)
        data.pop('file_path', None)

        # Written to a sibling and moved into place: `open(path, 'w')` truncates
        # first, so a failure part-way through yaml.dump left a half-written
        # item that no longer loads. os.replace is atomic on the same
        # filesystem, so the item is either the old one or the new one.
        tmp_path = file_path.with_name(f".{file_path.name}.tmp")
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                if file_path.exists():
                    _patch(file_path, data, f)
                else:
                    _dump(data, f)
            os.replace(tmp_path, file_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        return file_path

    def _build_prefix_map(self) -> Dict[str, str]:
        """Build prefix-to-directory mapping from project config."""
        if self._prefix_map is not None:
            return self._prefix_map

        prefix_map = {}

        if self.project_config and hasattr(self.project_config, 'doc_types'):
            for doc_type in self.project_config.doc_types:
                prefix = doc_type.prefix
                directory = doc_type.directory if doc_type.directory else prefix.rstrip('-')
                prefix_map[prefix] = directory

        self._prefix_map = prefix_map
        return prefix_map

    def _get_directory_for_prefix(self, prefix: str) -> Path:
        """Get appropriate directory for a prefix."""
        prefix_map = self._build_prefix_map()

        if prefix in prefix_map:
            subdir = prefix_map[prefix]
        else:
            matched_prefix = None
            for config_prefix in sorted(prefix_map.keys(), key=len, reverse=True):
                if prefix.startswith(config_prefix):
                    matched_prefix = config_prefix
                    break

            if matched_prefix:
                subdir = prefix_map[matched_prefix]
            else:
                subdir = 'other'

        return self.specs_dir / subdir


def _dump(data: Dict[str, Any], f) -> None:
    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _patch(file_path: Path, data: Dict[str, Any], out) -> None:
    """Rewrite only the top-level keys whose value changed; every other line stays as written.

    A controlled record is reviewed as a diff: a one-field update must show as
    one field, not as the whole file re-quoted and re-wrapped.
    """
    blocks: list[list[str]] = []
    text = file_path.read_text(encoding='utf-8')
    for line in (text if text.endswith('\n') else text + '\n').splitlines(keepends=True):
        starts_key = line[:1] not in ('', ' ', '\t', '\n', '#', '-')
        if starts_key or not blocks:
            blocks.append([line])
        else:
            blocks[-1].append(line)

    written: set[str] = set()
    for block in blocks:
        parsed = yaml.safe_load(''.join(block))
        if not isinstance(parsed, dict) or len(parsed) != 1:
            out.write(''.join(block))
            continue
        key, old = next(iter(parsed.items()))
        if key not in data:
            continue
        written.add(key)
        if _plain(old) == _plain(data[key]):
            out.write(''.join(block))
        else:
            _dump({key: data[key]}, out)
    rest = {k: v for k, v in data.items() if k not in written}
    if rest:
        _dump(rest, out)


def _plain(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))
