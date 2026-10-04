from __future__ import annotations

"""Prompt loading and assembly helpers for CR generation flows."""

import importlib.resources
from pathlib import Path


MAX_ITEMS = 300
MAX_DIFF_CHARS = 40_000


def _load_prompt(name: str) -> str:
    ref = importlib.resources.files("medharness.prompts").joinpath(name)
    return ref.read_text(encoding="utf-8")


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
    from dhfkit.store import open_store

    try:
        return open_store(dhf_path)
    except Exception as exc:
        raise RuntimeError(
            f"Cannot load DHF at {dhf_path} for {purpose}: {exc}"
        ) from exc


def _cr_context(dhf_path: Path, cr_id: str) -> dict:
    from medharness.services.context import cr_context

    return cr_context(_load_adapter(dhf_path, "DHF context"), cr_id)


def _link_model(ctx: dict) -> str:
    """The project's own link fields and chains, so a custom type or relationship is
    described to the model the way the checks will read it."""
    rows = [
        f"| {t['code']} | `{link['field']}` | {' or '.join(link['targets']) or 'any'} | {link['meaning']} |\n"
        for t in ctx["types"] for link in t.get("links", [])
    ]
    text = (
        "### Traceability Link Model\n"
        "(This project's link fields: what each is written on, what it points to, what it means.)\n\n"
        "| Written on | Field | Points to | Meaning |\n"
        "|------------|-------|-----------|---------|\n" + "".join(rows) + "\n"
    )
    chains = ctx.get("chains") or []
    if chains:
        text += (
            "### Traceability Chains\n"
            "(Write items top-down along these chains. An item you create needs at least one item of the next "
            "type linking back to it; the first type of a chain is where requirements enter and is exempt.)\n\n"
            + "".join(f"- {' → '.join(chain)}\n" for chain in chains) + "\n"
        )
    codes = {t["code"] for t in ctx["types"]}
    if {"SYSARCH", "MODULE", "SWDD"} <= codes:
        text += (
            "Design layer roles:\n"
            "- SYSARCH — a system-level design decision for the SYS it designs; only when the change alters boundaries, data flow or deployment\n"
            "- MODULE — one per software unit; defines the module's responsibility and interfaces (module-oriented, not requirement-oriented)\n"
            "- SWDD — a design decision within a module, only past the threshold in the prompt; must carry both `implements` (SRS) and `module` (MODULE)\n"
            "\n"
        )
    return text


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
            " Resolve a role to this project's codes here.)\n\n"
        )
        for role, label in _ROLE_LABELS.items():
            if role in by_role:
                lines.append(f"{label}: {', '.join(by_role[role])}\n")
        lines.append("\n")

    levels = [t for t in ctx["types"] if t.get("description")]
    if levels:
        lines.append(
            "### What Belongs at Each Level\n"
            "(This project's own definition of each type. Decide the level of a new item from these, "
            "and create nothing at a level whose existing item already covers the change.)\n\n"
        )
        lines += [f"**{t['code']} — {t['display_name']}**\n{t['description'].strip()}\n\n" for t in levels]

    lines.append(_link_model(ctx))


    if items:
        if ctx["scope"] == "whole_dhf" and len(items) > MAX_ITEMS:
            chains = ctx.get("chains") or []
            starts = {chain[0] for chain in chains}
            # SYS starts SYS→SYSARCH but sits inside CRS→SYS: an entry type is one no chain leads into.
            entry_types = (starts - {code for chain in chains for code in chain[1:]}) or starts
            lines.append("### Entry-tier Items\n")
            lines.append(
                "(The DHF is too large to list. Only the entry types of the chains are shown; "
                "use `item list --brief`, `--match` and `--linked-to` for the rest.)\n\n"
            )
            for item in items:
                if item["type"] in entry_types:
                    lines.append(f"- {item['id']} — {item.get('title', '')}\n")
        else:
            heading = "All DHF Items" if ctx["scope"] == "whole_dhf" else "Items This CR Affects"
            lines.append(f"### {heading}\n")
            for item in items:
                lines.append(f"- {item['id']} — {item.get('title', '')}\n")
        lines.append("\n")

    if ctx["risks"]:
        lines += [
            "## Risk & Control Context\n",
            "(When proposing new system requirements, check whether "
            "they implement an existing RCM. When proposing changes that affect an existing "
            "RCM-linked SYS item, flag the related RISK for re-evaluation.)\n\n",
        ]
        for risk in ctx["risks"]:
            lines.append(f"**{risk['id']}** — {risk['title']}\n")
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


def checks_section(checks: tuple[str, ...]) -> str:
    """Tells the model which commands the harness will run, and that they must pass."""
    if not checks:
        return ""
    listed = "".join(f"- `{command}`\n" for command in checks)
    return (
        "\n\n## Checks That Must Pass\n\n"
        "When you finish, the harness runs these commands itself. The run fails if any exits non-zero, "
        "and nothing is pushed. Use them as the build, typecheck and test commands for step 4, run them "
        "yourself first, and fix the code until each exits 0. Do not edit, skip or work around a check; "
        "if one cannot run here, say why in `implementation_notes`.\n\n" + listed
    )


def _assemble_develop_prompt(cr_id: str, dhf_path: Path | None = None,
                             warnings: list[str] | None = None,
                             checks: tuple[str, ...] = ()) -> str:
    prompt = _load_prompt("cr_develop.md").replace("{{cr_id}}", cr_id)
    if dhf_path is not None:
        prompt = _enrich(prompt, lambda p: _render_code_context(_cr_context(p, cr_id)),
                         dhf_path, warnings)
    return prompt + checks_section(checks)


def _assemble_review_code_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_code.md").replace("{{cr_id}}", cr_id)


MAX_SIBLINGS = 15


def _render_neighbourhoods(store, changed_items: dict[str, list[str]], cr_id: str) -> str:
    """For each item the CR created or updated: where it sits, what is beside it, what it may duplicate.

    The review sees only the diff, so an item the change should have reached, or one it
    duplicates, would otherwise never be in front of the reviewer.
    """
    from medharness.services.impact import NEAR_DUPLICATE_RATIO, chain_links, closest_same_type, parents

    items = store.list_items()
    by_id = {it["id"]: it for it in items}
    up = parents(items, store.config)
    down: dict[str, list[str]] = {}
    for item, target in chain_links(items, store.config):
        down.setdefault(target, []).append(item)
    created = set(changed_items.get("created", []))
    changed = [uid for uid in dict.fromkeys([*changed_items.get("created", []), *changed_items.get("updated", [])])
               if uid != cr_id and uid in by_id]

    def label(uid: str) -> str:
        return f"{uid} — {by_id[uid].get('title', '')}" if uid in by_id else uid

    def capped(uids: list[str]) -> str:
        more = f"; and {len(uids) - MAX_SIBLINGS} more" if len(uids) > MAX_SIBLINGS else ""
        return "; ".join(label(u) for u in uids[:MAX_SIBLINGS]) + more

    # One line per level, not one per path: with several parents per item, paths multiply.
    def ancestor_levels(uid: str) -> list[list[str]]:
        levels, frontier, seen = [], [uid], {uid}
        while frontier := sorted({p for n in frontier for p in up.get(n, []) if p in by_id and p not in seen}):
            seen.update(frontier)
            levels.append(frontier)
        return levels

    blocks = []
    for uid in changed:
        lines = [f"### {label(uid)} ({'created' if uid in created else 'updated'})\n"]
        levels = ancestor_levels(uid)
        if levels:
            lines.append(f"- Parent chain: {' → '.join(capped(level) for level in levels)}\n")
        else:
            lines.append("- Parent chain: none (this is where requirements enter)\n")
        siblings = sorted({sib for parent in (levels[0] if levels else []) for sib in down.get(parent, [])} - {uid})
        if siblings:
            lines.append(f"- Siblings under the same parent ({len(siblings)}): {capped(siblings)}\n")
        if uid in created:
            closest = closest_same_type(by_id[uid], items, created)
            if closest and closest[1] >= NEAR_DUPLICATE_RATIO:
                lines.append(f"- Closest existing item of the same type: {label(closest[0])} "
                             f"(similarity {closest[1]:.2f})\n")
        blocks.append("".join(lines))
    if not blocks:
        return ""
    return ("## Neighbourhood of the Changed Items\n\n"
            "(What sits around each item this CR created or updated, so you can judge what it "
            "left out and what it overlaps.)\n\n" + "\n".join(blocks))


def _assemble_review_design_prompt(cr_id: str, dhf_path: Path | None = None,
                                   changed_items: dict[str, list[str]] | None = None,
                                   warnings: list[dict] | None = None) -> str:
    prompt = _load_prompt("cr_review_design.md").replace("{{cr_id}}", cr_id)
    if dhf_path is not None and changed_items:
        prompt = _enrich(
            prompt, lambda p: _render_neighbourhoods(_load_adapter(p, "the design review"), changed_items, cr_id),
            dhf_path, warnings)
    return prompt


def _assemble_generate_dhf_prompt(cr_id: str, dhf_path: Path | None = None,
                                  warnings: list[str] | None = None) -> str:
    prompt = _load_prompt("cr_generate_dhf.md").replace("{{cr_id}}", cr_id)
    if dhf_path is not None:
        prompt = _enrich_with_plan_context(prompt, cr_id, dhf_path, warnings)
    return prompt


