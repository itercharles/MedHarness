"""The docs must put traceability analysis on the medharness side.

This has drifted twice. `architecture.md` listed traceability under `dhfkit`
while, thirty lines later, "The line between them" said dhfkit only stores. The
README's opening demo led with schema and dangling links — both dhfkit's, and a
dangling link is the one check a real backend makes impossible.

Analysis over the whole item set is what the project is for, and it is the half
a team keeping its DHF in Jira still needs. A summary that omits it describes a
different product.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture.md"

ANALYSIS = re.compile(r"traceability analysis|analysis over the", re.I)


def _section(text: str, heading: str) -> str:
    start = text.index(heading) + len(heading)
    rest = text[start:]
    end = rest.find("\n### ")
    return rest[: end if end != -1 else len(rest)]


def test_the_sections_exist() -> None:
    text = ARCH.read_text(encoding="utf-8")
    for heading in ("### `medharness` owns", "### `dhfkit` owns"):
        assert heading in text, f"{heading} is gone — this guard reads nothing"


def test_medharness_owns_the_analysis() -> None:
    owns = _section(ARCH.read_text(encoding="utf-8"), "### `medharness` owns")
    assert ANALYSIS.search(owns), (
        "the `medharness` owns list does not mention traceability analysis, "
        "which is the capability the project exists for"
    )


def test_dhfkit_does_not_claim_the_analysis() -> None:
    owns = _section(ARCH.read_text(encoding="utf-8"), "### `dhfkit` owns")
    assert not ANALYSIS.search(owns), (
        "the `dhfkit` owns list claims analysis; dhfkit stores and retrieves"
    )
