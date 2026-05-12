"""Spec front-matter validation for CI gates.

Reads the YAML front-matter produced by cr-analyze and validates:
- Required fields are present
- direction_fit is a known value
- affected_items reference real DHF item IDs
- proposed_new_items uses a predictable machine-readable shape
- design_impact_summary is present for downstream consumers
- test_plan has the expected structure
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_VALID_DIRECTION_FIT = {"in-scope", "scope-expansion", "out-of-scope"}
_FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_VALID_NEW_ITEM_TYPES = {"CRS", "SYS", "SRS", "SYSARCH", "SWDD", "RISK", "RCM", "SOUP", "REL", "DEF", "UC"}


def parse_spec_frontmatter(spec_path: Path) -> dict | None:
    """Extract and parse YAML front-matter from a spec file. Returns None if absent."""
    if not spec_path.exists():
        return None
    text = spec_path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return None
    try:
        import yaml
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return None


def extract_structured_analysis(spec_path: Path) -> dict | None:
    """Return the machine-readable CR analysis block from a spec file."""
    fm = parse_spec_frontmatter(spec_path)
    if fm is None:
        return None
    return {
        "direction_fit": fm.get("direction_fit"),
        "affected_items": list(fm.get("affected_items", []) or []),
        "proposed_new_items": list(fm.get("proposed_new_items", []) or []),
        "design_impact_summary": fm.get("design_impact_summary"),
        "test_plan": fm.get("test_plan"),
    }


def validate_spec(
    spec_path: Path,
    cr_id: str,
    dhf_path: Path | None = None,
) -> list[dict]:
    """Validate spec front-matter. Returns list of error dicts with 'issue' and 'fix'."""
    errors: list[dict] = []

    if not spec_path.exists():
        return [{
            "field": "file",
            "issue": f"Spec file not found: {spec_path}",
            "fix": f"Re-run cr-analyze for {cr_id} to generate the spec.",
        }]

    fm = parse_spec_frontmatter(spec_path)
    if fm is None:
        return [{
            "field": "front-matter",
            "issue": "No YAML front-matter found in spec.",
            "fix": "The spec must begin with a --- YAML block. See cr-analyze.md template.",
        }]

    # cr_id
    if fm.get("cr_id") != cr_id:
        errors.append({
            "field": "cr_id",
            "issue": f"cr_id is '{fm.get('cr_id')}', expected '{cr_id}'.",
            "fix": f'Set cr_id: "{cr_id}" in front-matter.',
        })

    # direction_fit
    df = fm.get("direction_fit")
    if not df:
        errors.append({
            "field": "direction_fit",
            "issue": "direction_fit is missing.",
            "fix": f"Add direction_fit: one of {sorted(_VALID_DIRECTION_FIT)}",
        })
    elif df not in _VALID_DIRECTION_FIT:
        errors.append({
            "field": "direction_fit",
            "issue": f"direction_fit '{df}' is not a valid value.",
            "fix": f"Change direction_fit to one of: {', '.join(sorted(_VALID_DIRECTION_FIT))}",
        })

    # affected_items
    affected = fm.get("affected_items")
    if affected is None:
        errors.append({
            "field": "affected_items",
            "issue": "affected_items is missing.",
            "fix": "Add affected_items: [] (or list the DHF item IDs this CR touches).",
        })
    elif not isinstance(affected, list):
        errors.append({
            "field": "affected_items",
            "issue": "affected_items must be a YAML list.",
            "fix": "Format as a YAML sequence: affected_items:\\n  - SYS-001",
        })
    elif dhf_path and affected:
        try:
            import dhfkit.api as _api
            existing = {it["id"] for it in _api.list_items(dhf_path)}
            for uid in affected:
                if uid not in existing:
                    errors.append({
                        "field": "affected_items",
                        "issue": f"Item '{uid}' in affected_items does not exist in DHF.",
                        "fix": f"Remove '{uid}' from affected_items, or create it first.",
                    })
        except Exception:
            pass

    proposed = fm.get("proposed_new_items")
    if proposed is None:
        errors.append({
            "field": "proposed_new_items",
            "issue": "proposed_new_items is missing.",
            "fix": "Add proposed_new_items: [] or a list of {type, title} objects.",
        })
    elif not isinstance(proposed, list):
        errors.append({
            "field": "proposed_new_items",
            "issue": "proposed_new_items must be a YAML list.",
            "fix": "Format as proposed_new_items:\\n  - type: SRS\\n    title: Example title",
        })
    else:
        for idx, item in enumerate(proposed):
            if not isinstance(item, dict):
                errors.append({
                    "field": f"proposed_new_items[{idx}]",
                    "issue": "Each proposed_new_items entry must be a mapping.",
                    "fix": "Use objects with at least `type` and `title` keys.",
                })
                continue
            item_type = item.get("type")
            if not isinstance(item_type, str) or not item_type.strip():
                errors.append({
                    "field": f"proposed_new_items[{idx}].type",
                    "issue": "proposed_new_items entry is missing a type.",
                    "fix": "Set type to a DHF doc type such as SRS, SWDD, or RISK.",
                })
            elif item_type not in _VALID_NEW_ITEM_TYPES:
                errors.append({
                    "field": f"proposed_new_items[{idx}].type",
                    "issue": f"Unknown proposed_new_items type '{item_type}'.",
                    "fix": f"Use one of: {', '.join(sorted(_VALID_NEW_ITEM_TYPES))}",
                })
            title = item.get("title")
            if not isinstance(title, str) or not title.strip():
                errors.append({
                    "field": f"proposed_new_items[{idx}].title",
                    "issue": "proposed_new_items entry is missing a title.",
                    "fix": "Add a concise title describing the proposed new DHF item.",
                })

    design_impact_summary = fm.get("design_impact_summary")
    if not isinstance(design_impact_summary, str) or not design_impact_summary.strip():
        errors.append({
            "field": "design_impact_summary",
            "issue": "design_impact_summary is missing or blank.",
            "fix": "Add a one-line design_impact_summary describing the DHF and code impact.",
        })

    # test_plan
    tp = fm.get("test_plan")
    if tp is None:
        errors.append({
            "field": "test_plan",
            "issue": "test_plan section is missing.",
            "fix": "Add test_plan with keys: auto_covered, needs_new_tc, must_be_manual.",
        })
    elif not isinstance(tp, dict):
        errors.append({
            "field": "test_plan",
            "issue": "test_plan must be a mapping.",
            "fix": "Structure as: test_plan:\\n  auto_covered: []\\n  needs_new_tc: []\\n  must_be_manual: []",
        })
    else:
        for key in ("auto_covered", "needs_new_tc", "must_be_manual"):
            if key not in tp:
                errors.append({
                    "field": f"test_plan.{key}",
                    "issue": f"test_plan.{key} is missing.",
                    "fix": f"Add {key}: [] under test_plan.",
                })
            elif not isinstance(tp.get(key), list):
                errors.append({
                    "field": f"test_plan.{key}",
                    "issue": f"test_plan.{key} must be a YAML list.",
                    "fix": f"Format as {key}: [] under test_plan.",
                })

    return errors


def write_spec_json(spec_path: Path, frontmatter_dict: dict) -> Path:
    """Write a JSON companion alongside the Markdown spec. Returns the .json path."""
    json_path = spec_path.with_suffix(".json")
    json_path.write_text(
        json.dumps(frontmatter_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return json_path


def read_spec_json(spec_path: Path) -> dict | None:
    """Read the JSON companion for a spec. Returns None if absent or unreadable."""
    json_path = spec_path.with_suffix(".json")
    if not json_path.exists():
        return None
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return None
