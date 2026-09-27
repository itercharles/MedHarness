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
# DHF context for the prompts, rendered from services.context
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


def _load_adapter(dhf_path: Path, purpose: str):
    """Open the DHF for prompt enrichment, failing loudly when it cannot be read.

    A caller that passes a dhf_path is asking for that context. Degrading to an
    empty block would send the design stage to the model with no knowledge of the
    existing DHF — it would then propose a V-model cascade blind to what is
    already there, and nothing downstream would report why.

    Callers that want no DHF context pass dhf_path=None instead.
    """
    # Inline import avoids coupling prompt_assembly to dhfkit at import-time;
    # it is only needed when a real DHF path is provided at runtime.
    from dhfkit.local_adapter import LocalDHFAdapter

    try:
        return LocalDHFAdapter(dhf_path)
    except Exception as exc:
        raise RuntimeError(
            f"Cannot load DHF at {dhf_path} for {purpose}: {exc}"
        ) from exc


def _cr_context(dhf_path: Path, cr_id: str) -> dict:
    from medharness.services.context import cr_context

    return cr_context(_load_adapter(dhf_path, "DHF context"), cr_id)


def _render_plan_context(ctx: dict) -> str:
    """The `build plan` prompt's view of `cr_context`."""
    lines = ["## Pre-computed DHF Context\n"]
    items = ctx["items"]

    if ctx["scope"] == "whole_dhf" and items:
        counts: dict[str, int] = {}
        for item in items:
            prefix = item["id"].rsplit("-", 1)[0]
            counts[prefix] = counts.get(prefix, 0) + 1
        type_summary = "  ".join(f"{p}: {n}" for p, n in sorted(counts.items()))
        lines.append(f"### Item Type Summary\n\n{type_summary}\n")

    by_role: dict[str, list[str]] = {}
    for dt in ctx["types"]:
        if dt["role"]:
            by_role.setdefault(dt["role"], []).append(f"{dt['code']} ({dt['display_name']})")
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

    if items:
        heading = "All DHF Items" if ctx["scope"] == "whole_dhf" else "Items This CR Affects"
        lines.append(f"### {heading}\n")
        for item in items[:MAX_ITEMS]:
            lines.append(f"- {item['id']} — {item.get('title', '')}\n")
        if len(items) > MAX_ITEMS:
            lines.append(f"\n_(truncated — showing {MAX_ITEMS} of {len(items)} items)_\n")
        lines.append("\n")

    if ctx["risks"]:
        lines += [
            "## Risk & Control Context\n",
            "(When proposing new system requirements, check whether "
            "they implement an existing RCM. When proposing changes that affect an existing "
            "RCM-linked SYS item, flag the related RISK for re-evaluation.)\n\n",
        ]
        for risk in ctx["risks"]:
            lines.append(f"**{risk['id']}** [{risk['severity'] or '—'} · "
                         f"{risk['risk_level'] or '—'}] — {risk['title']}\n")
            for rcm in risk["controls"]:
                impl_str = ", ".join(rcm["implements"]) or "—"
                lines.append(f"  ↳ {rcm['id']} — {rcm['title']} (implements: {impl_str})\n")
            if not risk["controls"]:
                lines.append("  ↳ _(no RCM items yet)_\n")
            lines.append("\n")

    return "".join(lines)


def _render_code_context(ctx: dict) -> str:
    """The `build code` prompt's view of `cr_context`: the module map."""
    if not ctx["modules"]:
        return ""
    lines = ["## Module → Design → Requirement Map\n",
             "(Use this to identify which module to touch "
             "for a given requirement, and which SWDDs to update after implementation.)\n\n"]
    for entry in ctx["modules"]:
        lines.append(f"**{entry['module_id']}** — {entry['title']}\n")
        if not entry["swdds"]:
            lines.append("  _(no SWDD items linked)_\n")
        for swdd in entry["swdds"]:
            impl_str = ", ".join(swdd["implements"]) if swdd["implements"] else "—"
            lines.append(f"  - {swdd['swdd_id']}: {swdd['title']}\n")
            lines.append(f"    implements: {impl_str}\n")
        lines.append("\n")
    return "".join(lines)


def _enrich(prompt: str, builder, dhf_path: Path, warnings: list[dict] | None) -> str:
    """Append an optional context block, recording the reason when it is absent.

    Enrichment stays non-fatal — a DHF that cannot be read should not abort a
    stage that can still run without it — but the failure is now reported through
    the caller's warnings channel instead of vanishing. Silently returning the
    bare prompt sent the model into a stage believing it had seen the DHF.

    The warning shape mirrors cr_generation._warning; prompt_assembly cannot
    import it without a cycle, since cr_generation imports from here.
    """
    try:
        block = builder(dhf_path)
    except Exception as exc:  # noqa: BLE001 — reported, not swallowed
        if warnings is not None:
            warnings.append({
                "code": "dhf_context_unavailable",
                "message": str(exc),
            })
        return prompt
    return prompt + "\n\n" + block if block else prompt


def _enrich_with_plan_context(prompt: str, cr_id: str, dhf_path: Path,
                              warnings: list[dict] | None) -> str:
    return _enrich(prompt, lambda p: _render_plan_context(_cr_context(p, cr_id)),
                   dhf_path, warnings)


def _assemble_develop_prompt(cr_id: str, dhf_path: Path | None = None,
                             warnings: list[str] | None = None) -> str:
    prompt = _load_prompt("cr_develop.md").replace("{{cr_id}}", cr_id)
    if dhf_path is not None:
        prompt = _enrich(prompt, lambda p: _render_code_context(_cr_context(p, cr_id)),
                         dhf_path, warnings)
    return prompt


def _assemble_review_code_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_code.md").replace("{{cr_id}}", cr_id)


def _assemble_review_design_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_design.md").replace("{{cr_id}}", cr_id)


def _assemble_generate_dhf_prompt(cr_id: str, dhf_path: Path | None = None,
                                  warnings: list[str] | None = None) -> str:
    prompt = _load_prompt("cr_generate_dhf.md").replace("{{cr_id}}", cr_id)
    if dhf_path is not None:
        prompt = _enrich_with_plan_context(prompt, cr_id, dhf_path, warnings)
    return _append_skills(prompt)


