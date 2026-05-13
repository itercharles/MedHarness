from __future__ import annotations

"""Prompt loading and assembly helpers for CR generation flows."""

import importlib.resources
import json
from pathlib import Path

from medharness.services.spec_validation import read_spec_json


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


def _build_dhf_context_block(dhf_path: Path) -> str:
    from dhfkit.local_adapter import LocalDHFAdapter

    from medharness.core import MedHarnessCore

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

    items = adapter.list_items()
    if items:
        lines.append("### All DHF Items\n")
        for item in items:
            item_id = item.get("id", "")
            title = item.get("title", "")
            lines.append(f"- {item_id} — {title}\n")

    cov = core.graph.calculate_coverage("SYS", "TC")
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


def _assemble_analyze_prompt(cr_id: str, dhf_path: Path | None = None) -> str:
    prompt = _load_prompt("cr_analyze.md").replace("{{cr_id}}", cr_id)
    if dhf_path is not None:
        block = _build_dhf_context_block(dhf_path)
        if block:
            prompt += "\n\n" + block
    return _append_skills(prompt)


def _assemble_design_prompt(cr_id: str) -> str:
    prompt = _load_prompt("cr_design.md").replace("{{cr_id}}", cr_id)
    return _append_skills(prompt)


def _assemble_develop_prompt(cr_id: str) -> str:
    return _load_prompt("cr_develop.md").replace("{{cr_id}}", cr_id)


def _assemble_review_spec_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_spec.md").replace("{{cr_id}}", cr_id)


def _assemble_review_design_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_design.md").replace("{{cr_id}}", cr_id)


def _assemble_review_code_prompt(cr_id: str) -> str:
    return _load_prompt("cr_review_code.md").replace("{{cr_id}}", cr_id)


def _assemble_design_prompt_with_spec_json(
    cr_id: str, spec_path: Path, dhf_path: Path | None = None
) -> str:
    prompt = _assemble_design_prompt(cr_id)
    spec_json = read_spec_json(spec_path)
    if not spec_json:
        return prompt
    prompt += (
        f"\n\n## Pre-computed Spec Summary (from {cr_id}-Spec.json)\n"
        "The following structured data was extracted from the approved spec. "
        "Use it directly — do not re-read or re-interpret the Markdown spec.\n"
        "For each proposed_new_items entry, preserve any explicit `parent` "
        "value when creating the DHF item so the design output matches the "
        "approved spec metadata.\n"
        "If a proposed_new_items entry includes `verification_method`, map that "
        "analysis metadata into the target item's actual schema instead of copying "
        "it verbatim: `SYS` uses `verification_method` as a single-element list, "
        "`SOUP` uses it as a scalar string, and item types without that field must "
        "not receive a synthetic `verification_method` property.\n"
        f"```json\n{json.dumps(spec_json, indent=2)}\n```\n"
    )
    if dhf_path is not None:
        closure = _build_impact_closure_block(dhf_path, spec_json)
        if closure:
            prompt += closure
    return prompt


def _build_impact_closure_block(dhf_path: Path, spec_json: dict) -> str:
    from dhfkit.local_adapter import LocalDHFAdapter

    from medharness.core import MedHarnessCore

    affected = spec_json.get("affected_items")
    if not isinstance(affected, list) or not affected:
        return ""

    try:
        adapter = LocalDHFAdapter(dhf_path)
        core = MedHarnessCore(adapter)
    except Exception:
        return ""

    lines = ["## Pre-computed Impact Closure\n"]
    lines.append(
        "For each affected item the upstream (requirements hierarchy) and "
        "downstream (linked tests, risks, etc.) nodes are listed so you can "
        "verify completeness without traversing the graph yourself.\n"
    )

    for uid in affected:
        uid = str(uid)
        chain = core.graph.get_item_chain(uid)
        if chain is None:
            lines.append(f"### {uid}\n\nNot found in DHF graph.\n")
            continue
        upstream = chain.get("upstream", [])
        downstream = chain.get("downstream", [])
        lines.append(f"### {uid}\n")
        us = ", ".join(sorted(upstream)) if upstream else "none"
        ds = ", ".join(sorted(downstream)) if downstream else "none"
        lines.append(f"Upstream: {us}\nDownstream: {ds}\n\n")

    return "".join(lines)
