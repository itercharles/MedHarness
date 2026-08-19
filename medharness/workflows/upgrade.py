"""medharness upgrade — diff and apply scaffold template updates.

Compares the installed template files against what's deployed in a project
directory and reports (or applies) changes to infrastructure files. DHF data
files (items, global.yaml, context.md) are never touched.
"""

from __future__ import annotations

import re
import shutil
from importlib.metadata import version as pkg_version
from pathlib import Path

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "dhfkit" / "templates"

# (template_rel, project_rel) — files that medharness owns and can auto-upgrade.
# DHF items, global.yaml, context.md, and CLAUDE.md are user-owned; never listed here.
# The CI workflow is user-owned too: it is not in the release payload, so this
# build has no template to compare against. docs/adopting.md carries the current
# recipe and the changelog calls out when it changes.
_UPGRADE_MAP: list[tuple[str, str]] = [
    ("github/prompts/cr-analyze.md",                          ".github/prompts/cr-analyze.md"),
    ("github/prompts/cr-develop.md",                          ".github/prompts/cr-develop.md"),
    ("specs/architecture_design_specification.md.j2",         "DHF/documents/specs/architecture_design_specification.md.j2"),
    ("specs/change_request_specification.md.j2",              "DHF/documents/specs/change_request_specification.md.j2"),
    ("specs/customer_requirement_specification.md.j2",        "DHF/documents/specs/customer_requirement_specification.md.j2"),
    ("specs/rcm_specification.md.j2",                         "DHF/documents/specs/rcm_specification.md.j2"),
    ("specs/requirements_specification.md.j2",                "DHF/documents/specs/requirements_specification.md.j2"),
    ("specs/risk_specification.md.j2",                        "DHF/documents/specs/risk_specification.md.j2"),
    ("specs/software_design_document.md.j2",                  "DHF/documents/specs/software_design_document.md.j2"),
    ("specs/test_specification.md.j2",                        "DHF/documents/specs/test_specification.md.j2"),
    ("specs/traceability_matrix.md.j2",                       "DHF/documents/specs/traceability_matrix.md.j2"),
    ("specs/styles/default.css",                              "DHF/documents/specs/styles/default.css"),
    ("config/doc_types/cr.yaml",                              "DHF/config/doc_types/cr.yaml"),
    ("config/doc_types/crs.yaml",                             "DHF/config/doc_types/crs.yaml"),
    ("config/doc_types/def.yaml",                             "DHF/config/doc_types/def.yaml"),
    ("config/doc_types/module.yaml",                          "DHF/config/doc_types/module.yaml"),
    ("config/doc_types/rcm.yaml",                             "DHF/config/doc_types/rcm.yaml"),
    ("config/doc_types/rel.yaml",                             "DHF/config/doc_types/rel.yaml"),
    ("config/doc_types/risk.yaml",                            "DHF/config/doc_types/risk.yaml"),
    ("config/doc_types/soup.yaml",                            "DHF/config/doc_types/soup.yaml"),
    ("config/doc_types/srs.yaml",                             "DHF/config/doc_types/srs.yaml"),
    ("config/doc_types/swdd.yaml",                            "DHF/config/doc_types/swdd.yaml"),
    ("config/doc_types/sys.yaml",                             "DHF/config/doc_types/sys.yaml"),
    ("config/doc_types/sysarch.yaml",                         "DHF/config/doc_types/sysarch.yaml"),
    ("config/doc_types/uc.yaml",                              "DHF/config/doc_types/uc.yaml"),
]


def _read_project_name(project_dir: Path) -> str:
    global_yaml = project_dir / "DHF" / "config" / "global.yaml"
    try:
        text = global_yaml.read_text()
        m = re.search(r'project_name:\s*["\']?([^"\'\n]+)["\']?', text)
        if m:
            return m.group(1).strip()
    except OSError:
        pass
    return project_dir.name.replace("-", " ").replace("_", " ").title()


def _substitute(text: str, project_name: str, medharness_version: str) -> str:
    text = text.replace("{{project_name}}", project_name)
    text = text.replace("{{medharness_version}}", medharness_version)
    text = text.replace("{{medharness_repo}}", "itercharles/MedHarness")
    text = text.replace("{{primary_test_tool}}", "pytest")
    return text


def check_upgrade(project_dir: Path) -> dict:
    """Compare template files against the project and report differences.

    Returns:
        {
          "installed_version": str,
          "files_checked": int,
          "up_to_date": [{"file": str}],
          "outdated": [{"file": str, "added_lines": int, "removed_lines": int}],
          "missing": [{"file": str}],
          "unavailable": [{"file": str, "template": str}],
          "summary": str,
        }

    ``unavailable`` lists templates this build cannot supply. That is a packaging
    fault rather than a project state, so it is reported rather than skipped —
    silently passing over a file the map claims to manage would let `upgrade`
    report "all up to date" about a file it never looked at.
    """
    try:
        installed_version = pkg_version("medharness")
    except Exception:
        installed_version = "unknown"

    project_name = _read_project_name(project_dir)

    up_to_date: list[dict] = []
    outdated: list[dict] = []
    missing: list[dict] = []
    unavailable: list[dict] = []

    for tmpl_rel, proj_rel in _UPGRADE_MAP:
        tmpl_path = _TEMPLATES_DIR / tmpl_rel
        proj_path = project_dir / proj_rel

        if not tmpl_path.exists():
            unavailable.append({"file": proj_rel, "template": tmpl_rel})
            continue

        try:
            tmpl_text = tmpl_path.read_text()
        except OSError:
            continue

        rendered = _substitute(tmpl_text, project_name, installed_version)

        if not proj_path.exists():
            missing.append({"file": proj_rel})
            continue

        try:
            proj_text = proj_path.read_text()
        except OSError:
            missing.append({"file": proj_rel})
            continue

        if rendered == proj_text:
            up_to_date.append({"file": proj_rel})
        else:
            tmpl_lines = set(rendered.splitlines())
            proj_lines = set(proj_text.splitlines())
            added = len(tmpl_lines - proj_lines)
            removed = len(proj_lines - tmpl_lines)
            outdated.append({"file": proj_rel, "added_lines": added, "removed_lines": removed})

    n_out = len(outdated)
    n_miss = len(missing)
    if n_out == 0 and n_miss == 0:
        summary = f"All {len(up_to_date)} scaffold file(s) are up to date (v{installed_version})."
    else:
        parts = []
        if n_out:
            parts.append(f"{n_out} file(s) outdated")
        if n_miss:
            parts.append(f"{n_miss} file(s) missing")
        summary = f"{', '.join(parts).capitalize()}. Run 'medharness upgrade --apply' to update."
    if unavailable:
        summary += (
            f" {len(unavailable)} template(s) missing from the medharness"
            f" installation — this build cannot manage them."
        )

    return {
        "installed_version": installed_version,
        "files_checked": len(up_to_date) + len(outdated) + len(missing),
        "up_to_date": up_to_date,
        "outdated": outdated,
        "missing": missing,
        "unavailable": unavailable,
        "summary": summary,
    }


def apply_upgrade(project_dir: Path) -> dict:
    """Apply template updates to outdated and missing scaffold files.

    Returns the same shape as check_upgrade with an additional ``applied`` list.
    """
    report = check_upgrade(project_dir)
    try:
        installed_version = pkg_version("medharness")
    except Exception:
        installed_version = "unknown"

    project_name = _read_project_name(project_dir)
    applied: list[str] = []

    targets = {e["file"] for e in report["outdated"]} | {e["file"] for e in report["missing"]}
    for tmpl_rel, proj_rel in _UPGRADE_MAP:
        if proj_rel not in targets:
            continue
        tmpl_path = _TEMPLATES_DIR / tmpl_rel
        proj_path = project_dir / proj_rel
        try:
            rendered = _substitute(tmpl_path.read_text(), project_name, installed_version)
        except OSError:
            continue
        proj_path.parent.mkdir(parents=True, exist_ok=True)
        proj_path.write_text(rendered)
        applied.append(proj_rel)

    n_applied = len(applied)
    report["applied"] = applied
    report["summary"] = (
        f"Applied {n_applied} update(s). "
        f"{len(report['up_to_date'])} file(s) were already current."
    )
    return report
