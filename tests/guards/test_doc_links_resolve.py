"""Every relative link in the docs names a file, and an anchor, that exists.

ai-security.md pointed at `adopting.md#incremental-adoption` for a year after
the section was renamed, and CONTRIBUTING.md at an ADR template spelled with an
underscore the file never had.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = sorted(
    [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "CLAUDE.md"]
    + list((ROOT / "docs").rglob("*.md"))
)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _slug(heading: str) -> str:
    """GitHub's anchor for a heading."""
    text = re.sub(r"[`*_]", "", heading.strip().lower())
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def _anchors(path: Path) -> set[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    return {_slug(m) for m in re.findall(r"^#+\s+(.+)$", text, flags=re.M)}


def _links(path: Path) -> list[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    return [t for t in LINK.findall(text) if not re.match(r"[a-z]+:", t)]


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_relative_link_resolves(doc: Path) -> None:
    broken = []
    for target in _links(doc):
        file_part, _, anchor = target.partition("#")
        dest = (doc.parent / file_part).resolve() if file_part else doc
        if not dest.exists():
            broken.append(f"{target} (no such file)")
        elif anchor and dest.suffix == ".md" and anchor not in _anchors(dest):
            broken.append(f"{target} (no such heading)")
    assert not broken, f"{doc.relative_to(ROOT)}: " + ", ".join(broken)


def test_the_scan_found_links() -> None:
    assert sum(len(_links(d)) for d in DOCS) >= 20
    assert "setting-up-ci" in _anchors(ROOT / "docs" / "ci.md")
