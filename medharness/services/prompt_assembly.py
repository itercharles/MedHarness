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
]


def _append_skills(prompt: str) -> str:
    parts = [prompt, "\n\n---\n"]
    for fname, title in _SKILL_FILES:
        parts.append(f"\n### {title}\n\n{_load_skill(fname)}\n")
    return "".join(parts)


def _assemble_analyze_prompt(cr_id: str) -> str:
    prompt = _load_prompt("cr_analyze.md").replace("{{cr_id}}", cr_id)
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


def _assemble_design_prompt_with_spec_json(cr_id: str, spec_path: Path) -> str:
    prompt = _assemble_design_prompt(cr_id)
    spec_json = read_spec_json(spec_path)
    if not spec_json:
        return prompt
    return prompt + (
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
