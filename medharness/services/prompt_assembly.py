from __future__ import annotations

"""Prompt loading and assembly helpers for CR generation flows."""

import importlib.resources
from pathlib import Path


MAX_ITEMS = 200
MAX_DIFF_CHARS = 40_000


def _load_prompt(name: str) -> str:
    ref = importlib.resources.files("medharness.prompts").joinpath(name)
    return ref.read_text(encoding="utf-8")


def _load_skill(name: str) -> str:
    ref = importlib.resources.files("medharness.prompts.skills").joinpath(name)
    return ref.read_text(encoding="utf-8")


_SKILL_FILES = [
    ("product_impact.md", "Product Impact"),
    ("req_manage.md", "Requirements Management"),
    ("architecture_impact.md", "Architecture Impact"),
    ("risk_impact.md", "Risk Impact"),
    ("soup_impact.md", "SOUP Impact"),
    ("test_impact.md", "Test Impact"),
    ("regulatory_impact.md", "Regulatory Impact"),
    ("security_impact.md", "Security Impact"),
    ("usability_impact.md", "Usability / HFE Impact"),
]


def _append_skills(prompt: str) -> str:
    parts = [prompt, "\n\n---\n"]
    for fname, title in _SKILL_FILES:
        parts.append(f"\n### {title}\n\n{_load_skill(fname)}\n")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Pre-computed DHF context for the analyze prompt
# ---------------------------------------------------------------------------


_ROLE_LABELS: dict[str, str] = {
    "use_case": "Use cases",
    "customer_requirement": "Customer / user needs (tier 1)",
    "system_requirement": "System requirements (tier 2)",
    "software_requirement": "Software / subsystem requirements (tier 3)",
    "design_detail": "Design detail (tier 4)",
    "architecture": "Architecture",
    "risk": "Risk analysis",
    "risk_control": "Risk controls",
    "soup": "SOUP",
    "change_request": "Change requests",
    "defect": "Defects",
    "release": "Releases",
}


def _build_dhf_context_block(dhf_path: Path) -> str:
    # Inline imports avoid coupling prompt_assembly to dhfkit/medharness core
    # at import-time. These modules are only needed when a real DHF path is
    # provided at runtime.
    from dhfkit.local_adapter import LocalDHFAdapter

    from medharness.core import MedHarnessCore

    # Silent degradation: prompt assembly is a best-effort enrichment. If the
    # DHF cannot be loaded the caller still gets the base prompt + skills.
    try:
        adapter = LocalDHFAdapter(dhf_path)
        core = MedHarnessCore(adapter)
    except Exception:
        return ""

    lines = ["## Pre-computed DHF Context\n"]

    counts = core.graph.node_counts()
    if counts:
        type_summary = "  ".join(
            f"{prefix.rstrip('-')}: {count}"
            for prefix, count in sorted(counts.items())
        )
        lines.append(f"### Item Type Summary\n\n{type_summary}\n")

    by_role: dict[str, list[str]] = {}
    role_codes: dict[str, list[str]] = {}
    try:
        for dt in adapter.list_item_types():
            if dt.get("role"):
                role = dt["role"]
                entry = f"{dt['code']} ({dt['name']})"
                by_role.setdefault(role, []).append(entry)
                role_codes.setdefault(role, []).append(dt["code"])
    except Exception:
        pass  # Type Registry is best-effort; degrade if adapter is unavailable
    if by_role:
        lines.append(
            "### Type Registry\n"
            "(Maps abstract DHF roles to this project's type codes."
            " Skills reference these roles — resolve to codes here.)\n\n"
        )
        for role, label in _ROLE_LABELS.items():
            if role in by_role:
                lines.append(f"{label}: {', '.join(by_role[role])}\n")
        lines.append("\n")

    items = adapter.list_items()
    cap = MAX_ITEMS
    if items:
        lines.append("### All DHF Items\n")
        for item in items[:cap]:
            item_id = item.get("id", "")
            title = item.get("title", "")
            lines.append(f"- {item_id} — {title}\n")
        if len(items) > cap:
            lines.append(
                f"\n_(truncated — showing {cap} of {len(items)} items)_\n"
            )

    lines.append("\n")

    # TC is the test-case ID prefix used throughout dhfkit (junit_parser.py
    # generates TC-DOCTYPE-NNN IDs). This prefix is a project convention, not
    # a configurable DHF setting. Projects that rename their test prefix can
    # override it by defining a TC doc type in their DHF config.
    tc_prefix = "TC"
    tc_type = adapter.get_item_type(f"{tc_prefix}-")
    if tc_type is not None and tc_type.get("prefix"):
        tc_prefix = tc_type["prefix"].rstrip("-")

    sys_prefix = role_codes.get("system_requirement", ["SYS"])[0]
    cov = core.graph.calculate_coverage(sys_prefix, tc_prefix)
    uncovered = cov.get("uncovered", [])
    if uncovered:
        lines.append(
            "### $DHF_CONTEXT.test_coverage.manual_verification_candidates\n"
        )
        lines.append(
            ", ".join(uncovered)
            + "  (no linked TC items — likely manual verification)\n"
        )

    return "".join(lines)


def _assemble_develop_prompt(cr_id: str) -> str:
    return _load_prompt("cr_develop.md").replace("{{cr_id}}", cr_id)


def _assemble_review_code_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_code.md").replace("{{cr_id}}", cr_id)


def _assemble_generate_dhf_prompt(cr_id: str, dhf_path: Path | None = None) -> str:
    prompt = _load_prompt("cr_generate_dhf.md").replace("{{cr_id}}", cr_id)
    if dhf_path is not None:
        block = _build_dhf_context_block(dhf_path)
        if block:
            prompt += "\n\n" + block
    return _append_skills(prompt)


