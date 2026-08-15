"""SOUP manifest synchronisation — compare package manifests against DHF SOUP items.

Parses lockfiles and dependency manifests from multiple ecosystems, diffs them
against the current SOUP items in the DHF, and optionally writes creates/updates
back through dhfkit.api.

Supported manifest formats
--------------------------
| File                | Ecosystem  | Notes                              |
|---------------------|------------|------------------------------------|
| requirements.txt    | PyPI       | pinned (==) only                   |
| uv.lock             | PyPI       | uv lockfile (TOML)                 |
| poetry.lock         | PyPI       | Poetry lockfile (TOML)             |
| pyproject.toml      | PyPI       | best-effort; lockfile preferred    |
| package.json        | npm        | semver ranges stripped             |
| package-lock.json   | npm        | v2/v3 lockfile; pinned             |
| go.mod              | Go         | required block                     |
| Cargo.lock          | crates.io  | TOML lockfile                      |
| pom.xml             | Maven      | <dependencies> block               |

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
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Known manifest filenames → parser dispatch
# ---------------------------------------------------------------------------

_KNOWN_MANIFESTS: list[str] = [
    "uv.lock",
    "poetry.lock",
    "Cargo.lock",
    "package-lock.json",
    "requirements.txt",
    "go.mod",
    "pyproject.toml",
    "package.json",
    "pom.xml",
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
    """Load TOML using stdlib tomllib (Python 3.11+)."""
    try:
        import tomllib
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except ModuleNotFoundError:
        # Python <3.11 fallback
        try:
            import tomli  # type: ignore[import]
            return tomli.loads(path.read_text(encoding="utf-8"))
        except ModuleNotFoundError:
            raise RuntimeError(
                f"Cannot parse {path.name}: requires Python 3.11+ or 'tomli' package"
            )


# ---------------------------------------------------------------------------
# Manifest parsers — each returns list[{name, version, source, ecosystem}]
# ---------------------------------------------------------------------------

_PEP508_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)"
    r"(?:\[[^\]]+\])?"        # optional extras
    r"==(?P<version>[^\s;#]+)",
)

_PEP508_ANY_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)"
    r"(?:\[[^\]]+\])?"
    r"(?P<spec>[^;#\n]*)",
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


def parse_uv_lock(path: Path) -> list[dict]:
    """All packages from a uv.lock file."""
    data = _load_toml(path)
    packages: list[dict] = []
    for pkg in data.get("package", []):
        name = pkg.get("name")
        version = pkg.get("version")
        if name and version:
            packages.append({"name": name, "version": str(version), "source": str(path), "ecosystem": "PyPI"})
    return packages


def parse_poetry_lock(path: Path) -> list[dict]:
    """All packages from a poetry.lock file."""
    data = _load_toml(path)
    packages: list[dict] = []
    for pkg in data.get("package", []):
        name = pkg.get("name")
        version = pkg.get("version")
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
    """Version-range deps from package.json (semver operators stripped)."""
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


def parse_package_lock_json(path: Path) -> list[dict]:
    """Pinned packages from npm package-lock.json (v2/v3)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    packages: list[dict] = []
    source = str(path)
    # v2/v3: flat "packages" map; keys like "node_modules/express"
    for key, info in (data.get("packages") or {}).items():
        if not key or key == "":
            continue  # root package
        name = info.get("name") or key.removeprefix("node_modules/").split("/")[-1]
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


_GO_REQUIRE_RE = re.compile(
    r"^\s+(?P<module>[^\s]+)\s+v(?P<version>[^\s]+)(?:\s+//\s*indirect)?",
)


def parse_go_mod(path: Path) -> list[dict]:
    """Direct and indirect requires from go.mod."""
    packages: list[dict] = []
    source = str(path)
    in_require = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        # single-line require
        single = re.match(r"^require\s+(?P<module>[^\s]+)\s+v(?P<version>[^\s]+)", stripped)
        if single:
            packages.append({"name": single.group("module"), "version": single.group("version"),
                             "source": source, "ecosystem": "Go"})
            continue
        if in_require:
            m = _GO_REQUIRE_RE.match(line)
            if m:
                packages.append({"name": m.group("module"), "version": m.group("version"),
                                 "source": source, "ecosystem": "Go"})
    return packages


def parse_cargo_lock(path: Path) -> list[dict]:
    """All packages from Cargo.lock."""
    data = _load_toml(path)
    packages: list[dict] = []
    for pkg in data.get("package", []):
        name = pkg.get("name")
        version = pkg.get("version")
        if name and version:
            packages.append({"name": name, "version": str(version),
                             "source": str(path), "ecosystem": "crates.io"})
    return packages


_MVN_NS = {"mvn": "http://maven.apache.org/POM/4.0.0"}


def parse_pom_xml(path: Path) -> list[dict]:
    """Dependencies from Maven pom.xml."""
    packages: list[dict] = []
    source = str(path)
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return []
    root = tree.getroot()
    # Try with and without Maven namespace
    for ns in (_MVN_NS, {}):
        mvn = _MVN_NS["mvn"]
        dep_tag = f"{{{mvn}}}dependency" if ns else "dependency"
        g_tag = f"{{{mvn}}}groupId" if ns else "groupId"
        a_tag = f"{{{mvn}}}artifactId" if ns else "artifactId"
        v_tag = f"{{{mvn}}}version" if ns else "version"
        for dep in root.iter(dep_tag):
            group = dep.find(g_tag)
            artifact = dep.find(a_tag)
            version_el = dep.find(v_tag)
            if artifact is not None and version_el is not None:
                ver = (version_el.text or "").strip()
                gid = (group.text or "").strip() if group is not None else ""
                name = f"{gid}:{artifact.text.strip()}" if gid else (artifact.text or "").strip()
                if name and ver and not ver.startswith("${"):
                    packages.append({"name": name, "version": ver,
                                     "source": source, "ecosystem": "Maven"})
        if packages:
            break
    return packages


def _dispatch_parser(path: Path) -> list[dict]:
    """Route a manifest file to its parser by filename."""
    name = path.name
    if name == "requirements.txt":
        return parse_requirements_txt(path)
    if name == "uv.lock":
        return parse_uv_lock(path)
    if name == "poetry.lock":
        return parse_poetry_lock(path)
    if name == "pyproject.toml":
        return parse_pyproject_toml(path)
    if name == "package.json":
        return parse_package_json(path)
    if name == "package-lock.json":
        return parse_package_lock_json(path)
    if name == "go.mod":
        return parse_go_mod(path)
    if name == "Cargo.lock":
        return parse_cargo_lock(path)
    if name == "pom.xml":
        return parse_pom_xml(path)
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
    import yaml  # type: ignore[import]

    sources_file = dhf_path / "config" / "soup-sources.yaml"
    if not sources_file.exists():
        return [], []

    try:
        data = yaml.safe_load(sources_file.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return [], [f"Failed to parse soup-sources.yaml: {exc}"]

    packages: list[dict] = []
    errors: list[str] = []

    for entry in data.get("sources") or []:
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
    extra_commands: list[str] | None = None,
    use_sources_file: bool = True,
) -> dict:
    """Parse manifests, diff against DHF SOUP items, optionally write changes.

    Source priority (highest wins on name collision):
    1. Explicit ``manifest_paths``
    2. ``extra_commands`` (--from-command)
    3. ``DHF/config/soup-sources.yaml`` (when ``use_sources_file=True``)
    4. Auto-discovery of manifest files in the project root (when all above
       are empty and no sources file is present)

    Returns a structured result dict with outcome and counts.
    """
    import dhfkit.api as api

    errors: list[str] = []
    packages: list[dict] = []
    manifests_parsed: list[str] = []
    project_dir = dhf.parent

    # 1. Explicit manifest paths
    for path in manifest_paths:
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
        if use_sources_file and (dhf / "config" / "soup-sources.yaml").exists():
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

    soup_items: list[dict] = []
    try:
        soup_items = [it for it in api.list_items(dhf) if it.get("type") == "SOUP"]
    except Exception as exc:
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
                    "ecosystem": pkg.get("ecosystem") or "",
                    "manufacturer": pkg.get("manufacturer") or "",
                    "purpose": f"Dependency from {pkg.get('ecosystem') or 'manifest'}",
                    "license": "",
                }
                new_item = api.create_item(dhf, data, author=author, cr_id=cr_id)
                items_created.append(new_item["uid"])
            except Exception as exc:
                errors.append(f"Failed to create SOUP item for {pkg['name']}: {exc}")

        for entry in diff["to_update"]:
            pkg = entry["pkg"]
            item = entry["item"]
            try:
                api.update_item(dhf, item["uid"], {"version": pkg["version"]},
                                author=author, cr_id=cr_id)
                items_updated.append(item["uid"])
            except Exception as exc:
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
