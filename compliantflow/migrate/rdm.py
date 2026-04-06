"""Innolitics RDM → CompliantFlow DHF migration."""

from __future__ import annotations

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Type mapping
# ---------------------------------------------------------------------------

# Map RDM item level / directory hint → CompliantFlow doc type code.
# Priority: explicit `level` field first, then directory name heuristic.
_LEVEL_TO_TYPE: Dict[str, str] = {
    "user_need": "CRS",
    "stakeholder": "CRS",
    "system": "SYS",
    "system_requirement": "SYS",
    "software": "SRS",
    "software_requirement": "SRS",
    "risk": "RISK",
    "soup": "SOUP",
    "architectural": "SYSARCH",
}

_DIR_TO_TYPE: Dict[str, str] = {
    "user_needs": "CRS",
    "stakeholder_needs": "CRS",
    "system_requirements": "SYS",
    "system": "SYS",
    "software_requirements": "SRS",
    "software": "SRS",
    "risks": "RISK",
    "risk": "RISK",
    "soup": "SOUP",
    "architecture": "SYSARCH",
}

# CompliantFlow traceability link field per doc type
_LINK_FIELD: Dict[str, str] = {
    "CRS": "derives_from",
    "SYS": "satisfies",
    "SRS": "derives_from",
    "SWDD": "derives_from",
    "SYSARCH": "derives_from",
    "RISK": "derives_from",
    "SOUP": "derives_from",
}

# DHF directory per doc type (matches global.yaml / doc_types config)
_TYPE_TO_DIR: Dict[str, str] = {
    "CRS": "01_req_crs",
    "SYS": "02_req_sys",
    "SRS": "03_req_srs",
    "SWDD": "05_swdd",
    "SYSARCH": "06_sys_arch",
    "RISK": "12_risks",
    "SOUP": "11_soup",
}


# ---------------------------------------------------------------------------
# reST → Markdown conversion (lightweight, no docutils dependency)
# ---------------------------------------------------------------------------

def _rst_to_markdown(text: str) -> str:
    """Convert a reST snippet to Markdown. Handles common patterns only."""
    if not text:
        return text

    lines = text.splitlines()
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Section headers: underline on next line with = - ~ ^
        if i + 1 < len(lines):
            underline = lines[i + 1].strip()
            if underline and len(set(underline)) == 1 and underline[0] in "=-~^#":
                depth = "=-~^#".index(underline[0])
                hashes = "#" * (depth + 1)
                out.append(f"{hashes} {line.strip()}")
                i += 2
                continue

        # .. directive:: — strip
        if re.match(r"\s*\.\. \w+::", line):
            i += 1
            # skip indented directive body
            while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
                i += 1
            continue

        # ``code`` → `code`
        line = re.sub(r"``(.+?)``", r"`\1`", line)
        # `link <url>`_ → [link](url)
        line = re.sub(r"`([^`<]+)\s+<([^>]+)>`_", r"[\1](\2)", line)

        out.append(line)
        i += 1

    return "\n".join(out).strip()


# ---------------------------------------------------------------------------
# ID remapping
# ---------------------------------------------------------------------------

class _IDMapper:
    """Assigns new CompliantFlow IDs and tracks the old→new mapping."""

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self._map: Dict[str, str] = {}   # old_id → new_id

    def assign(self, old_id: str, type_code: str) -> str:
        if old_id in self._map:
            return self._map[old_id]
        n = self._counters.get(type_code, 0) + 1
        self._counters[type_code] = n
        new_id = f"{type_code}-{n:03d}"
        self._map[old_id] = new_id
        return new_id

    def resolve(self, old_id: str) -> Optional[str]:
        return self._map.get(old_id)

    @property
    def mapping(self) -> Dict[str, str]:
        return dict(self._map)


# ---------------------------------------------------------------------------
# Main migrator
# ---------------------------------------------------------------------------

class RDMMigrator:
    """Convert an Innolitics RDM repository into a CompliantFlow DHF.

    Usage::

        migrator = RDMMigrator(source_dir=Path("path/to/rdm-repo"))
        report = migrator.migrate(dhf_items_dir=Path("DHF/items"), dry_run=False)
    """

    def __init__(self, source_dir: Path) -> None:
        self.source_dir = source_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def migrate(
        self,
        dhf_items_dir: Path,
        dry_run: bool = False,
    ) -> Dict:
        """Run the migration.

        Returns a report dict with keys:
            created, skipped, needs_review, mapping
        """
        raw_items = self._discover(self.source_dir)

        id_mapper = _IDMapper()
        # First pass: assign all IDs so links can be resolved
        typed: List[Tuple[Dict, str]] = []
        skipped: List[Dict] = []

        for raw in raw_items:
            type_code = self._resolve_type(raw)
            if type_code is None:
                skipped.append({
                    "rdm_id": raw.get("id", "<unknown>"),
                    "reason": "Cannot determine CompliantFlow doc type",
                })
                continue
            id_mapper.assign(raw["id"], type_code)
            typed.append((raw, type_code))

        # Second pass: convert and write
        created: List[Dict] = []
        needs_review: List[Dict] = []

        for raw, type_code in typed:
            cf_item, warnings = self._convert(raw, type_code, id_mapper)
            if not dry_run:
                self._write(cf_item, type_code, dhf_items_dir)
            created.append({"rdm_id": raw["id"], "cf_id": cf_item["id"], "type": type_code})
            for w in warnings:
                needs_review.append({"cf_id": cf_item["id"], "warning": w})

        return {
            "created": created,
            "skipped": skipped,
            "needs_review": needs_review,
            "mapping": id_mapper.mapping,
            "dry_run": dry_run,
        }

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover(self, root: Path) -> List[Dict]:
        """Find all RDM-format YAML files under root."""
        items: List[Dict] = []
        for yaml_file in sorted(root.rglob("*.yaml")):
            try:
                data = yaml.safe_load(yaml_file.read_text())
            except Exception:
                continue
            if not isinstance(data, dict) or "id" not in data:
                continue
            # Attach the source path for directory-based type hinting
            data["_source_path"] = yaml_file
            items.append(data)
        return items

    # ------------------------------------------------------------------
    # Type resolution
    # ------------------------------------------------------------------

    def _resolve_type(self, raw: Dict) -> Optional[str]:
        # 1. Explicit `level` field
        level = str(raw.get("level", "")).lower().replace(" ", "_")
        if level and level in _LEVEL_TO_TYPE:
            return _LEVEL_TO_TYPE[level]

        # 2. Directory hint from source path
        source: Optional[Path] = raw.get("_source_path")
        if source:
            for part in source.parts:
                part_lower = part.lower().replace("-", "_")
                if part_lower in _DIR_TO_TYPE:
                    return _DIR_TO_TYPE[part_lower]

        # 3. ID prefix heuristic (e.g. "SYS-001", "SRS-002")
        rdm_id: str = raw.get("id", "")
        prefix = rdm_id.split("-")[0].upper() if "-" in rdm_id else ""
        if prefix in _TYPE_TO_DIR:
            return prefix

        return None

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def _convert(
        self,
        raw: Dict,
        type_code: str,
        id_mapper: _IDMapper,
    ) -> Tuple[Dict, List[str]]:
        """Convert one RDM item to a CompliantFlow item dict."""
        warnings: List[str] = []
        new_id = id_mapper.assign(raw["id"], type_code)

        cf: Dict = {"id": new_id}

        # Title
        title = raw.get("title") or raw.get("name") or ""
        if not title:
            warnings.append("No title found; set manually")
        cf["title"] = title

        # Content / description
        description = raw.get("description") or raw.get("content") or ""
        cf["content"] = _rst_to_markdown(description)

        # Traceability links
        parent_ids: List[str] = raw.get("parent_ids") or raw.get("parents") or []
        resolved_links: List[str] = []
        for pid in parent_ids:
            new_pid = id_mapper.resolve(pid)
            if new_pid:
                resolved_links.append(new_pid)
            else:
                warnings.append(f"Parent '{pid}' not found in migration set; link dropped")

        if resolved_links:
            link_field = _LINK_FIELD.get(type_code, "derives_from")
            cf[link_field] = resolved_links

        # Carry over fields that map cleanly
        for rdm_field, cf_field in [
            ("category", "category"),
            ("verification_methods", "verification_methods"),
            ("notes", "notes"),
        ]:
            if rdm_field in raw:
                cf[cf_field] = raw[rdm_field]

        return cf, warnings

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def _write(self, cf_item: Dict, type_code: str, dhf_items_dir: Path) -> None:
        subdir = _TYPE_TO_DIR.get(type_code, type_code.lower())
        target_dir = dhf_items_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{cf_item['id']}.yaml"
        with open(target_file, "w") as f:
            yaml.dump(cf_item, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
