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
                entry = f"{dt['code']} ({dt['display_name']})"
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

    # Relationship model — injected once so every generate-dhf session has
    # the full traceability graph in context without reading external docs.
    lines.append(
        "### Traceability Link Model\n"
        "(Canonical link fields and what each relationship means.)\n\n"
        "| Written on | Field | Points to | Meaning |\n"
        "|------------|-------|-----------|---------|\n"
        "| CRS | `derives_from` | UC | customer requirement ← use case |\n"
        "| SYS | `satisfies` | CRS | system requirement ← customer need |\n"
        "| SYSARCH | `design` | SYS | arch decision designs this SYS requirement |\n"
        "| SRS | `derives_from` | SYS | software requirement ← system requirement |\n"
        "| SWDD | `implements` | SRS | detailed design implements this SRS |\n"
        "| SWDD | `module` | MODULE | detailed design belongs to this module |\n"
        "| RCM | `mitigates` | RISK | control measure mitigates this risk |\n"
        "| RCM | `implements` | SYS | control measure is a system requirement |\n"
        "\n"
        "Design layer roles:\n"
        "- SYSARCH — one per SYS requirement; records the system-level design decision for that requirement\n"
        "- MODULE — one per software unit; defines the module's responsibility and interfaces (module-oriented, not requirement-oriented)\n"
        "- SWDD — one per SRS requirement; records design decisions within a specific module; must carry both `implements` (SRS) and `module` (MODULE)\n"
        "\n"
    )

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


def _build_risk_context_block(dhf_path: Path) -> str:
    """Summarise the current RISK/RCM landscape for injection into generate-dhf prompts."""
    try:
        from dhfkit.local_adapter import LocalDHFAdapter

        adapter = LocalDHFAdapter(dhf_path)
        config = adapter._config
        items = adapter.list_items()
    except Exception:
        return ""

    risk_dt = config.get_doc_type("RISK")
    rcm_dt = config.get_doc_type("RCM")
    if not risk_dt or not rcm_dt:
        return ""

    risk_prefix = risk_dt.prefix
    rcm_prefix = rcm_dt.prefix

    risk_items = {it["id"]: it for it in items if it["id"].startswith(risk_prefix)}
    rcm_items = {it["id"]: it for it in items if it["id"].startswith(rcm_prefix)}

    if not risk_items:
        return ""

    lines = [
        "## Risk & Control Context\n",
        "(Pre-computed from DHF. When proposing new system requirements, check whether "
        "they implement an existing RCM. When proposing changes that affect an existing "
        "RCM-linked SYS item, flag the related RISK for re-evaluation.)\n\n",
    ]

    for risk_id, risk in sorted(risk_items.items()):
        severity = risk.get("severity", "—")
        risk_level = risk.get("risk_level", "—")
        lines.append(f"**{risk_id}** [{severity} · {risk_level}] — {risk.get('title', '')}\n")
        rcms_for_risk = [
            (rid, rcm) for rid, rcm in rcm_items.items()
            if risk_id in (
                rcm.get("mitigates") if isinstance(rcm.get("mitigates"), list)
                else ([rcm.get("mitigates")] if rcm.get("mitigates") else [])
            )
        ]
        if rcms_for_risk:
            for rcm_id, rcm in sorted(rcms_for_risk):
                implements = rcm.get("implements") or []
                if isinstance(implements, str):
                    implements = [implements]
                impl_str = ", ".join(implements) if implements else "—"
                lines.append(f"  ↳ {rcm_id} — {rcm.get('title', '')} (implements: {impl_str})\n")
        else:
            lines.append("  ↳ _(no RCM items yet)_\n")
        lines.append("\n")

    return "".join(lines)


def _build_module_context_block(dhf_path: Path) -> str:
    """Pre-compute the MODULE → SWDD → SRS map for the develop prompt."""
    try:
        from dhfkit.local_adapter import LocalDHFAdapter
        from dhfkit.traceability import build_module_map

        adapter = LocalDHFAdapter(dhf_path)
        module_map = build_module_map(adapter.list_items(), adapter._config)
    except Exception:
        return ""

    if not module_map:
        return ""

    lines = ["## Module → Design → Requirement Map\n",
             "(Pre-computed from DHF. Use this to identify which module to touch "
             "for a given requirement, and which SWDDs to update after implementation.)\n\n"]
    for entry in module_map:
        mod_id = entry["module_id"]
        mod_title = entry["title"]
        lines.append(f"**{mod_id}** — {mod_title}\n")
        if not entry["swdds"]:
            lines.append("  _(no SWDD items linked)_\n")
        else:
            for swdd in entry["swdds"]:
                impl_str = ", ".join(swdd["implements"]) if swdd["implements"] else "—"
                lines.append(f"  - {swdd['swdd_id']}: {swdd['title']}\n")
                lines.append(f"    implements: {impl_str}\n")
        lines.append("\n")
    return "".join(lines)


def _assemble_develop_prompt(cr_id: str, dhf_path: Path | None = None) -> str:
    prompt = _load_prompt("cr_develop.md").replace("{{cr_id}}", cr_id)
    if dhf_path is not None:
        module_block = _build_module_context_block(dhf_path)
        if module_block:
            prompt += "\n\n" + module_block
    return prompt


def _assemble_review_code_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_code.md").replace("{{cr_id}}", cr_id)


def _assemble_review_design_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_design.md").replace("{{cr_id}}", cr_id)


def _assemble_generate_dhf_prompt(cr_id: str, dhf_path: Path | None = None) -> str:
    prompt = _load_prompt("cr_generate_dhf.md").replace("{{cr_id}}", cr_id)
    if dhf_path is not None:
        block = _build_dhf_context_block(dhf_path)
        if block:
            prompt += "\n\n" + block
        risk_block = _build_risk_context_block(dhf_path)
        if risk_block:
            prompt += "\n\n" + risk_block
    return _append_skills(prompt)


