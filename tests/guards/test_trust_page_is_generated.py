"""The trust page's table and the README's count are written from the seeded-omission test.

A hand-kept "9 of 12" outlives the experiment it reports; the table and the count are
generated, and this fails when the committed text is not what the generator writes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def generator():
    spec = importlib.util.spec_from_file_location("generate_interface", ROOT / "scripts" / "generate_interface.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ["docs/trust.md", "README.md"])
def test_the_generated_blocks_are_what_the_generator_writes(generator, name: str) -> None:
    path = ROOT / name
    current = path.read_text(encoding="utf-8")
    assert generator.update(current, generator.OTHER_BLOCKS[path]) == current, (
        f"{name} is out of date: run `python scripts/generate_interface.py`"
    )


def test_every_seeded_omission_has_a_row(generator) -> None:
    from medharness.validation import seeded

    rows = generator._seeded_omissions()
    assert len(rows) == len(seeded.STOPPED) + 4
    assert sum(1 for _, gate, _ in rows if gate is None) == sum(1 for _, gate, why in rows if why)


def test_the_trust_page_stays_short_and_claims_no_completeness() -> None:
    text = (ROOT / "docs" / "trust.md").read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 70
    for readme_or_doc in (text, (ROOT / "README.md").read_text(encoding="utf-8")):
        for phrase in ("guarantees completeness", "ensures correctness", "guaranteed complete"):
            assert phrase not in readme_or_doc.lower()
