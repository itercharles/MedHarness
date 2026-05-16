"""SOUP manifest synchronisation — compare package manifests against DHF SOUP items.

Parses ``requirements.txt`` (PEP 508) and ``package.json`` (npm) manifests,
diffs them against the current SOUP items in the DHF, and optionally writes
creates/updates back through dhfkit.api.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Manifest parsers
# ---------------------------------------------------------------------------

_PEP508_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)"
    r"(?:\[[^\]]+\])?"        # optional extras
    r"==(?P<version>[^\s;#]+)",
)


def parse_requirements_txt(path: Path) -> list[dict]:
    """Return [{name, version, source}] for pinned packages in a requirements.txt."""
    packages: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = _PEP508_RE.match(line)
        if m:
            packages.append({
                "name": m.group("name"),
                "version": m.group("version"),
                "source": str(path),
                "ecosystem": "pypi",
            })
    return packages


def parse_package_json(path: Path) -> list[dict]:
    """Return [{name, version, source, dev}] for all deps in a package.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    packages: list[dict] = []
    for section, is_dev in (
        ("dependencies", False),
        ("devDependencies", True),
        ("peerDependencies", False),
    ):
        for name, version_spec in (data.get(section) or {}).items():
            packages.append({
                "name": name,
                "version": _normalize_version(version_spec),
                "source": str(path),
                "ecosystem": "npm",
                "dev": is_dev,
            })
    return packages


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Case-fold and strip hyphens/underscores for fuzzy matching."""
    return re.sub(r"[-_.]", "", name).lower()


def _normalize_version(v: str) -> str:
    """Strip semver range operators so versions can be compared literally."""
    return re.sub(r"^[\^~>=<! ]+", "", v).strip()


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------

def _find_soup_item(soup_items: list[dict], package_name: str) -> Optional[dict]:
    """Return the SOUP item whose name matches package_name (fuzzy)."""
    target = _normalize_name(package_name)
    for item in soup_items:
        if _normalize_name(item.get("name") or "") == target:
            return item
    return None


def _package_key(pkg: dict) -> str:
    return f"{pkg['ecosystem']}:{pkg['name']}"


def diff_against_dhf(
    packages: list[dict],
    soup_items: list[dict],
) -> dict:
    """Compare parsed manifest packages against existing SOUP items.

    Returns::

        {
          "to_create": [pkg, ...],   # in manifests, no SOUP item found
          "to_update": [             # SOUP item exists but version differs
              {"pkg": pkg, "item": item, "old_version": str},
              ...
          ],
          "orphans": [item, ...],    # SOUP item exists but not in any manifest
          "matched": [               # in manifests and SOUP item matches
              {"pkg": pkg, "item": item},
              ...
          ],
        }
    """
    to_create: list[dict] = []
    to_update: list[list] = []
    matched: list[dict] = []
    matched_item_ids: set[str] = set()

    for pkg in packages:
        item = _find_soup_item(soup_items, pkg["name"])
        if item is None:
            to_create.append(pkg)
        else:
            matched_item_ids.add(item["uid"])
            soup_ver = _normalize_version(item.get("version") or "")
            manifest_ver = _normalize_version(pkg["version"])
            if soup_ver != manifest_ver:
                to_update.append({"pkg": pkg, "item": item, "old_version": soup_ver})
            else:
                matched.append({"pkg": pkg, "item": item})

    orphans = [it for it in soup_items if it["uid"] not in matched_item_ids]
    return {
        "to_create": to_create,
        "to_update": to_update,
        "orphans": orphans,
        "matched": matched,
    }


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def sync_soup_items(
    dhf: Path,
    manifest_paths: list[Path],
    *,
    write: bool = False,
    author: str = "ci",
    cr_id: Optional[str] = None,
) -> dict:
    """Parse manifests, diff against DHF SOUP items, optionally write changes.

    Returns a structured result dict with outcome and counts.
    """
    import dhfkit.api as api

    errors: list[str] = []
    packages: list[dict] = []
    manifests_parsed: list[str] = []

    for path in manifest_paths:
        try:
            if path.name == "requirements.txt":
                pkgs = parse_requirements_txt(path)
            elif path.name == "package.json":
                pkgs = parse_package_json(path)
            else:
                errors.append(f"Unsupported manifest format: {path}")
                continue
            packages.extend(pkgs)
            manifests_parsed.append(str(path))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Failed to parse {path}: {exc}")

    soup_items: list[dict] = []
    try:
        soup_items = [it for it in api.list_items(dhf) if it.get("type") == "SOUP"]
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Failed to list SOUP items: {exc}")

    diff = diff_against_dhf(packages, soup_items)

    items_created: list[str] = []
    items_updated: list[str] = []

    if write:
        for pkg in diff["to_create"]:
            try:
                data = {
                    "type": "SOUP",
                    "name": pkg["name"],
                    "version": pkg["version"],
                    "purpose": f"Dependency from {pkg['ecosystem']} manifest",
                    "manufacturer": "",
                    "license": "",
                }
                new_item = api.create_item(dhf, data, author=author, cr_id=cr_id)
                items_created.append(new_item["uid"])
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Failed to create SOUP item for {pkg['name']}: {exc}")

        for entry in diff["to_update"]:
            pkg = entry["pkg"]
            item = entry["item"]
            try:
                api.update_item(dhf, item["uid"], {"version": pkg["version"]},
                                author=author, cr_id=cr_id)
                items_updated.append(item["uid"])
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Failed to update {item['uid']}: {exc}")

    outcome = "completed_with_errors" if errors else "completed"
    return {
        "outcome": outcome,
        "manifests_parsed": manifests_parsed,
        "packages_found": len(packages),
        "to_create": [p["name"] for p in diff["to_create"]],
        "to_update": [
            {"uid": e["item"]["uid"], "name": e["pkg"]["name"],
             "old_version": e["old_version"], "new_version": e["pkg"]["version"]}
            for e in diff["to_update"]
        ],
        "orphans": [{"uid": it["uid"], "name": it.get("name", "")} for it in diff["orphans"]],
        "matched_count": len(diff["matched"]),
        "items_created": items_created,
        "items_updated": items_updated,
        "write": write,
        "errors": errors,
    }
