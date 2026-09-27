"""This repository's own `DHF/README.md` is what `init` writes today.

It was scaffolded early and never regenerated, so it went on teaching
`AI-harness/context.md`, `.github/prompts/`, `change plan` and
`validate traceability` long after all of them were gone. Nothing read it for
retired names: the docs guard scans `README.md`, `CLAUDE.md` and `docs/`.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_it_matches_the_template_init_copies() -> None:
    project = yaml.safe_load((ROOT / "DHF" / "config" / "global.yaml").read_text())["project_name"]
    template = (ROOT / "dhfkit" / "templates" / "README.md").read_text(encoding="utf-8")
    assert (ROOT / "DHF" / "README.md").read_text(encoding="utf-8") == \
        template.replace("{{project_name}}", project), (
        "DHF/README.md differs from dhfkit/templates/README.md; regenerate it "
        "from the template when either changes"
    )
