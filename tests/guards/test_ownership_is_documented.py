"""The docs must put traceability analysis on the medharness side.

This has drifted twice. `architecture.md` listed traceability under `dhfkit`
while, thirty lines later, "The line between them" said dhfkit only stores. The
README's opening demo led with schema and dangling links — both dhfkit's, and a
dangling link is the one check a real backend makes impossible.

Analysis over the whole item set is what the project is for. A summary that
omits it describes a different product.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture.md"

def _owns(package: str) -> str:
    """The "Owns" cell of a package's row in the ownership table."""
    text = ARCH.read_text(encoding="utf-8")
    row = re.search(rf"^\|\s*`{package}`\s*\|[^|]*\|([^|]+)\|", text, re.M)
    assert row, f"no ownership row for {package} — this guard reads nothing"
    return row.group(1)


def test_medharness_owns_the_analysis() -> None:
    owns = _owns("medharness")
    assert re.search(r"analysis", owns, re.I) and "traceability" in owns, (
        "the medharness row does not claim traceability analysis, which is the "
        "capability the project exists for"
    )


def test_dhfkit_does_not_claim_the_analysis() -> None:
    owns = _owns("dhfkit")
    assert not re.search(r"analysis|traceability", owns, re.I), (
        "the dhfkit row claims analysis; dhfkit stores and retrieves"
    )
