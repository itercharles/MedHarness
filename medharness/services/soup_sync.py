"""SOUP manifest synchronisation — compare package manifests against DHF SOUP items.

Parses lockfiles and dependency manifests from multiple ecosystems, diffs them
against the current SOUP items in the DHF, and writes creates/updates
back through the store.

Supported manifest formats
--------------------------
| File                | Ecosystem  | Notes                              |
|---------------------|------------|------------------------------------|
| requirements.txt    | PyPI       | pinned (==) only                   |
| uv.lock             | PyPI       | uv lockfile (TOML)                 |
| poetry.lock         | PyPI       | Poetry lockfile (TOML)             |
| pyproject.toml      | PyPI       | best-effort; lockfile preferred    |
| package.json        | npm        | installed version from a lockfile  |
| package-lock.json   | npm        | v2/v3 lockfile; pinned             |
| pnpm-lock.yaml      | npm        | lockfile v6+; direct dependencies  |

Any other ecosystem (Go, Cargo, Maven, ...) goes through ``--from-command`` or a
``command`` source: one JSON object per line, ``{name, version, ecosystem}``.

Extension mechanisms
--------------------
``soup-sources.yaml`` (at ``DHF/config/soup-sources.yaml``) is the persistent
per-project source list. Supported entry types::

    sources:
      - type: manifest
        path: requirements.txt          # relative to project root

      - type: command
        run: "syft . -o syft-json"      # stdout NDJSON: {name,version,ecosystem}

      - type: manual
        items:
          - name: Ubuntu Server
            version: "22.04.3 LTS"
            manufacturer: Canonical Ltd.
            ecosystem: null             # no OSV scan for non-package SOUP
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

import yaml

from dhfkit.paths import config_file
from dhfkit.store import open_store


# ---------------------------------------------------------------------------
# Known manifest filenames → parser dispatch
# ---------------------------------------------------------------------------

_KNOWN_MANIFESTS: list[str] = [
    "uv.lock",
    "poetry.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "requirements.txt",
    "pyproject.toml",
    "package.json",
]


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Case-fold and strip hyphens/underscores for fuzzy matching."""
    return re.sub(r"[-_.]", "", name).lower()


def _normalize_version(v: str) -> str:
    """Strip semver range operators so versions can be compared literally."""
    return re.sub(r"^[\^~>=<! ]+", "", v).strip()


def _load_toml(path: Path) -> dict:
    import tomllib

    return tomllib.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Manifest parsers — each returns list[{name, version, source, ecosystem}]
# ---------------------------------------------------------------------------

_PEP508_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)"
    r"(?:\[[^\]]+\])?"        # optional extras
    r"==(?P<version>[^\s;#]+)",
)


def parse_requirements_txt(path: Path) -> list[dict]:
    """Pinned packages (==) from requirements.txt."""
    packages: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = _PEP508_RE.match(line)
        if m:
            packages.append({
                "name": m.group("name"),
                "version": m.group("version"),
                "source": str(path),
                "ecosystem": "PyPI",
            })
    return packages


def parse_python_lock(path: Path) -> list[dict]:
    """The packages of a uv.lock or poetry.lock, bar the project's own.

    uv lists the project (and each workspace member) among its packages with an editable or
    virtual source. That is the software being built, not SOUP.
    """
    packages: list[dict] = []
    for pkg in _load_toml(path).get("package", []):
        name = pkg.get("name")
        version = pkg.get("version")
        source = pkg.get("source")
        if isinstance(source, dict) and ("editable" in source or "virtual" in source):
            continue
        if name and version:
            packages.append({"name": name, "version": str(version), "source": str(path), "ecosystem": "PyPI"})
    return packages


def parse_pyproject_toml(path: Path) -> list[dict]:
    """Best-effort: extract pinned (==) deps from pyproject.toml.

    Lockfiles (uv.lock, poetry.lock) are more reliable; use them when present.
    """
    data = _load_toml(path)
    packages: list[dict] = []
    source = str(path)

    # PEP 621 [project.dependencies]
    for dep in data.get("project", {}).get("dependencies") or []:
        m = _PEP508_RE.match(str(dep).strip())
        if m:
            packages.append({"name": m.group("name"), "version": m.group("version"),
                             "source": source, "ecosystem": "PyPI"})

    # Poetry [tool.poetry.dependencies]
    for name, spec in (data.get("tool", {}).get("poetry", {}).get("dependencies") or {}).items():
        if name.lower() == "python":
            continue
        if isinstance(spec, str):
            ver = _normalize_version(spec)
            if ver:
                packages.append({"name": name, "version": ver, "source": source, "ecosystem": "PyPI"})
        elif isinstance(spec, dict):
            ver = _normalize_version(str(spec.get("version") or ""))
            if ver:
                packages.append({"name": name, "version": ver, "source": source, "ecosystem": "PyPI"})

    return packages


def parse_package_json(path: Path) -> list[dict]:
    """The dependencies package.json declares, at the version a lockfile resolved them to.

    A lockfile in the manifest's directory, or in one above it up to the repository root (a
    workspace), says what is installed; a range such as ``^2.1.0`` does not, and its floor is
    not what ships. A dependency the lockfile does not list keeps its range as written, which
    `verify soup` reports as not checked and the SBOM gives no purl.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    installed = _installed_versions(path)
    packages: list[dict] = []
    for section, is_dev in (
        ("dependencies", False),
        ("devDependencies", True),
        ("peerDependencies", False),
    ):
        for name, version_spec in (data.get(section) or {}).items():
            packages.append({
                "name": name,
                "version": installed.get(name) or version_spec,
                "source": str(path),
                "ecosystem": "npm",
                "dev": is_dev,
            })
    return packages


def parse_package_lock_json(path: Path) -> list[dict]:
    """Pinned packages from npm package-lock.json (v2/v3)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    packages: list[dict] = []
    source = str(path)
    # v2/v3: flat "packages" map; keys like "node_modules/express"
    for key, info in (data.get("packages") or {}).items():
        if not key or key == "":
            continue  # root package
        # The name is what follows the last `node_modules/`, scope included: `@types/node`.
        name = info.get("name") or key.rsplit("node_modules/", 1)[-1]
        version = info.get("version")
        if name and version:
            packages.append({"name": name, "version": version, "source": source, "ecosystem": "npm"})
    # v1 fallback: "dependencies" map
    if not packages:
        for name, info in (data.get("dependencies") or {}).items():
            version = info.get("version")
            if version:
                packages.append({"name": name, "version": version, "source": source, "ecosystem": "npm"})
    return packages


_PNPM_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies")
_PNPM_VERSION_RE = re.compile(r"^\d[^()\s]*")


def parse_pnpm_lock(path: Path) -> list[dict]:
    """The direct dependencies of every project in pnpm-lock.yaml, at the versions pnpm installed.

    Lockfile v6 and later. A dependency that is a workspace link or a git or tarball URL has no
    registry version and is left out; the peer-dependency suffix on a version is dropped.
    """
    found: dict[tuple[str, str], dict] = {}
    for versions in _pnpm_importers(path).values():
        for name, version in versions.items():
            found.setdefault((name, version), {"name": name, "version": version,
                                               "source": str(path), "ecosystem": "npm"})
    return list(found.values())


def _pnpm_importers(path: Path) -> dict[str, dict[str, str]]:
    """``{project path: {dependency: installed version}}`` from a pnpm-lock.yaml (v6 and later)."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    major = str(data.get("lockfileVersion", "")).split(".")[0]
    if not major.isdigit() or int(major) < 6:
        raise ValueError(
            f"Unsupported pnpm lockfileVersion {data.get('lockfileVersion')!r} in {path.name}: need 6 or later"
        )
    # A single-project v6 lockfile keeps its dependencies at the top level.
    importers = data.get("importers") or {".": data}
    resolved: dict[str, dict[str, str]] = {}
    for key, importer in importers.items():
        versions: dict[str, str] = {}
        for section in _PNPM_SECTIONS:
            for name, info in (importer.get(section) or {}).items():
                m = _PNPM_VERSION_RE.match(str(info.get("version", "") if isinstance(info, dict) else info))
                if m:
                    versions[name] = m.group()
        resolved[key] = versions
    return resolved


def _installed_versions(manifest: Path) -> dict[str, str]:
    """What a lockfile beside or above ``manifest`` says is installed, by package name.

    The search stops at the repository root, so a lockfile that belongs to another project
    further up is never read. Empty when there is none, or it cannot be read.
    """
    manifest = manifest.resolve()
    directory = manifest.parent
    while True:
        try:
            for lock in ("pnpm-lock.yaml", "package-lock.json"):
                if (directory / lock).is_file():
                    rel = _relative_to(manifest.parent, directory)
                    return (_pnpm_importers(directory / lock).get(rel, {}) if lock == "pnpm-lock.yaml"
                            else _npm_lock_versions(directory / lock, rel))
        except (ValueError, OSError, json.JSONDecodeError, yaml.YAMLError):
            return {}
        if (directory / ".git").exists() or directory.parent == directory:
            return {}
        directory = directory.parent


def _relative_to(project: Path, root: Path) -> str:
    """``project`` as a path from ``root`` the way a lockfile writes it: ``.`` or ``apps/client``."""
    return project.relative_to(root).as_posix() if project != root else "."


def _npm_lock_versions(path: Path, project: str) -> dict[str, str]:
    """The top-level installed versions of the project at ``project`` in a package-lock.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    prefix = "" if project == "." else f"{project}/"
    versions: dict[str, str] = {}
    for key, info in (data.get("packages") or {}).items():
        for tail in (f"{prefix}node_modules/", "node_modules/"):
            if key.startswith(tail) and "/node_modules/" not in key[len(tail):]:
                versions.setdefault(key[len(tail):], str(info.get("version", "")))
                break
    if not data.get("packages"):
        versions = {name: str(info.get("version", "")) for name, info in (data.get("dependencies") or {}).items()}
    return {name: version for name, version in versions.items() if version}


def _dispatch_parser(path: Path) -> list[dict]:
    """Route a manifest file to its parser by filename."""
    name = path.name
    if name == "requirements.txt":
        return parse_requirements_txt(path)
    if name in ("uv.lock", "poetry.lock"):
        return parse_python_lock(path)
    if name == "pyproject.toml":
        return parse_pyproject_toml(path)
    if name == "package.json":
        return parse_package_json(path)
    if name == "package-lock.json":
        return parse_package_lock_json(path)
    if name == "pnpm-lock.yaml":
        return parse_pnpm_lock(path)
    raise ValueError(f"Unsupported manifest format: {name}")


# ---------------------------------------------------------------------------
# Auto-discovery
# ---------------------------------------------------------------------------

def discover_manifests(project_dir: Path) -> list[Path]:
    """Find known manifest files in *project_dir* (non-recursive, top-level only)."""
    found: list[Path] = []
    for filename in _KNOWN_MANIFESTS:
        candidate = project_dir / filename
        if candidate.exists():
            found.append(candidate)
    return found


# ---------------------------------------------------------------------------
# soup-sources.yaml — persistent per-project source config
# ---------------------------------------------------------------------------

def load_soup_sources(dhf_path: Path, project_dir: Path) -> tuple[list[dict], list[str]]:
    """Read DHF/config/soup-sources.yaml and collect all packages.

    Returns (packages, errors).  Each package is a dict with at least
    {name, version, ecosystem}.  Manual entries may omit ecosystem.
    """

    sources_file = config_file(dhf_path, "soup-sources.yaml")
    if sources_file is None:
        return [], []

    try:
        data = yaml.safe_load(sources_file.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return [], [f"Failed to parse soup-sources.yaml: {exc}"]

    packages: list[dict] = []
    errors: list[str] = []

    for entry in data.get("sources") or []:
        if not isinstance(entry, dict):
            errors.append(f"soup-sources.yaml: a source must be a mapping with a 'type', not {entry!r}")
            continue
        entry_type = entry.get("type")

        if entry_type == "manifest":
            raw_path = entry.get("path", "")
            manifest_path = project_dir / raw_path
            if not manifest_path.exists():
                errors.append(f"soup-sources.yaml: manifest not found: {raw_path}")
                continue
            try:
                pkgs = _dispatch_parser(manifest_path)
                packages.extend(pkgs)
            except Exception as exc:
                errors.append(f"Failed to parse {raw_path}: {exc}")

        elif entry_type == "command":
            cmd = entry.get("run", "")
            default_eco = entry.get("ecosystem", "")
            if not cmd:
                errors.append("soup-sources.yaml: command entry missing 'run'")
                continue
            try:
                pkgs = _run_external_command(cmd, default_ecosystem=default_eco,
                                             cwd=project_dir)
                packages.extend(pkgs)
            except Exception as exc:
                errors.append(f"Command failed '{cmd}': {exc}")

        elif entry_type == "manual":
            for item in entry.get("items") or []:
                name = str(item.get("name") or "").strip()
                version = str(item.get("version") or "").strip()
                if not name or not version:
                    errors.append(f"soup-sources.yaml: manual entry missing name or version: {item}")
                    continue
                packages.append({
                    "name": name,
                    "version": version,
                    "ecosystem": item.get("ecosystem") or "",
                    "manufacturer": item.get("manufacturer") or "",
                    "source": "soup-sources.yaml (manual)",
                })
        else:
            errors.append(f"soup-sources.yaml: unknown source type '{entry_type}'")

    return packages, errors


# ---------------------------------------------------------------------------
# External command support
# ---------------------------------------------------------------------------

def _run_external_command(cmd: str, *, default_ecosystem: str = "",
                           cwd: Path | None = None) -> list[dict]:
    """Run a shell command and parse its NDJSON stdout.

    Each line of stdout must be a JSON object with at least ``name`` and
    ``version``. Optional ``ecosystem`` overrides ``default_ecosystem``.

    Example command that works out of the box::

        pip list --format=json | python3 -c "
        import sys, json
        for p in json.load(sys.stdin):
            print(json.dumps({**p, 'ecosystem': 'PyPI'}))"
    """
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=str(cwd) if cwd else None,
    )
    if result.returncode != 0:
        raise RuntimeError(f"exited {result.returncode}: {result.stderr.strip()[:200]}")

    packages: list[dict] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = str(obj.get("name") or "").strip()
        version = str(obj.get("version") or "").strip()
        if not name or not version:
            continue
        packages.append({
            "name": name,
            "version": version,
            "ecosystem": obj.get("ecosystem") or default_ecosystem,
            "source": f"command: {cmd[:60]}",
        })
    return packages


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
    to_update: list[dict] = []
    matched: list[dict] = []
    # Items expose "id". The artifact keys below stay "uid" because existing
    # consumers read them — the same split release-baseline makes. Reading
    # item["uid"] was simply wrong, and crashed the sync on every real DHF.
    matched_item_ids: set[str] = set()

    for pkg in packages:
        item = _find_soup_item(soup_items, pkg["name"])
        if item is None:
            to_create.append(pkg)
        else:
            matched_item_ids.add(item["id"])
            soup_ver = _normalize_version(item.get("version") or "")
            manifest_ver = _normalize_version(pkg["version"])
            if soup_ver != manifest_ver:
                to_update.append({"pkg": pkg, "item": item, "old_version": soup_ver})
            else:
                matched.append({"pkg": pkg, "item": item})

    orphans = [it for it in soup_items if it["id"] not in matched_item_ids]
    return {
        "to_create": to_create,
        "to_update": to_update,
        "orphans": orphans,
        "matched": matched,
    }


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def collect_manifest_packages(
    dhf: Path,
    manifest_paths: list[Path] | None = None,
    *,
    extra_commands: list[str] | None = None,
    use_sources_file: bool = True,
) -> tuple[list[dict], list[str], list[str]]:
    """Every package the project's manifests resolve, deduplicated by name.

    Returns ``(packages, manifests_parsed, errors)``. Shared by the read-only
    drift half of the SOUP gate and by the write action, so the two can never
    disagree about what the manifests say.
    """
    errors: list[str] = []
    packages: list[dict] = []
    manifests_parsed: list[str] = []
    project_dir = dhf.parent

    # 1. Explicit manifest paths
    for path in manifest_paths or []:
        try:
            pkgs = _dispatch_parser(path)
            packages.extend(pkgs)
            manifests_parsed.append(str(path))
        except ValueError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"Failed to parse {path}: {exc}")

    # 2. External commands
    for cmd in (extra_commands or []):
        try:
            pkgs = _run_external_command(cmd, cwd=project_dir)
            packages.extend(pkgs)
            manifests_parsed.append(f"command:{cmd[:40]}")
        except Exception as exc:
            errors.append(f"Command failed '{cmd}': {exc}")

    # 3. soup-sources.yaml (when no explicit sources given)
    if not manifest_paths and not extra_commands:
        if use_sources_file and config_file(dhf, "soup-sources.yaml"):
            src_pkgs, src_errors = load_soup_sources(dhf, project_dir)
            packages.extend(src_pkgs)
            errors.extend(src_errors)
            if src_pkgs:
                manifests_parsed.append("soup-sources.yaml")
        else:
            # 4. Auto-discovery
            for manifest_path in discover_manifests(project_dir):
                try:
                    pkgs = _dispatch_parser(manifest_path)
                    packages.extend(pkgs)
                    manifests_parsed.append(str(manifest_path))
                except Exception as exc:
                    errors.append(f"Failed to parse {manifest_path.name}: {exc}")

    # Deduplicate by normalised name — first occurrence wins.
    seen: set[str] = set()
    deduped: list[dict] = []
    for pkg in packages:
        key = _normalize_name(pkg["name"])
        if key not in seen:
            seen.add(key)
            deduped.append(pkg)
    packages = deduped

    return packages, manifests_parsed, errors


def sync_soup_items(
    dhf: Path,
    manifest_paths: list[Path],
    *,
    extra_commands: list[str] | None = None,
    use_sources_file: bool = True,
) -> dict:
    """Parse manifests, diff against DHF SOUP items, and write the changes.

    Source priority (highest wins on name collision):
    1. Explicit ``manifest_paths``
    2. ``extra_commands`` (--from-command)
    3. ``DHF/config/soup-sources.yaml`` (when ``use_sources_file=True``)
    4. Auto-discovery of manifest files in the project root (when all above
       are empty and no sources file is present)

    Returns a structured result dict with outcome and counts.
    """
    packages, manifests_parsed, errors = collect_manifest_packages(
        dhf, list(manifest_paths),
        extra_commands=extra_commands, use_sources_file=use_sources_file,
    )

    soup_items: list[dict] = []
    store = None
    try:
        store = open_store(dhf)
        soup_items = [it for it in store.list_items() if it.get("type") == "SOUP"]
    except Exception as exc:
        errors.append(f"Failed to list SOUP items: {exc}")

    diff = diff_against_dhf(packages, soup_items)
    if store is None:
        # The register could not be read, so "no SOUP item for this package" proves nothing.
        diff["to_create"] = diff["to_update"] = []

    items_created: list[str] = []
    items_updated: list[str] = []

    for pkg in diff["to_create"]:
        try:
            data = {
                "type": "SOUP",
                "name": pkg["name"],
                "version": pkg["version"],
                "ecosystem": pkg.get("ecosystem") or "",
                "manufacturer": pkg.get("manufacturer") or "",
                # Left empty on purpose. §8.1.2 asks why a component is
                # used; "Dependency from PyPI" answers nothing and would
                # make the register look complete while saying nothing.
                # `verify soup` reports the gap until a person fills it.
                "purpose": "",
                "license": "",
                "source": pkg.get("source") or "",
            }
            new_item = store.create_item(data)
            items_created.append(new_item["id"])
        except Exception as exc:
            errors.append(f"Failed to create SOUP item for {pkg['name']}: {exc}")

    for entry in diff["to_update"]:
        pkg = entry["pkg"]
        item = entry["item"]
        try:
            store.update_item(item["id"], {"version": pkg["version"]})
            items_updated.append(item["id"])
        except Exception as exc:
            errors.append(f"Failed to update {item['id']}: {exc}")

    outcome = "completed_with_errors" if errors else "completed"
    return {
        "outcome": outcome,
        "manifests_parsed": manifests_parsed,
        "packages_found": len(packages),
        "to_create": [p["name"] for p in diff["to_create"]],
        "to_update": [
            {"uid": e["item"]["id"], "name": e["pkg"]["name"],
             "old_version": e["old_version"], "new_version": e["pkg"]["version"]}
            for e in diff["to_update"]
        ],
        "orphans": [{"uid": it["id"], "name": it.get("name", "")} for it in diff["orphans"]],
        "matched_count": len(diff["matched"]),
        "items_created": items_created,
        "items_updated": items_updated,
        "errors": errors,
    }
