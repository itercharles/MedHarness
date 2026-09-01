"""The interface document is a contract, so it is checked like one.

`docs/interface.md` tells callers what they may rely on. A document that drifts
from the implementation is worse than none: it produces confident code built on
a promise nothing keeps.

These tests assert only the facts a caller would act on — the envelope keys, the
exit codes, the blocking vocabulary. Prose is left alone.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from medharness.services.ci import ENVELOPE_KEYS
from medharness.services.gates import BLOCKING, GATES, gates_manifest

DOC = Path(__file__).resolve().parents[2] / "docs" / "interface.md"


@pytest.fixture(scope="module")
def text() -> str:
    return DOC.read_text()


class TestEnvelopeIsDocumentedAccurately:
    def test_every_envelope_key_has_a_table_row(self, text: str) -> None:
        for key in ENVELOPE_KEYS:
            assert re.search(rf"^\|\s*`{key}`\s*\|", text, re.M), (
                f"envelope key '{key}' has no row in the interface table"
            )

    def test_no_key_is_documented_that_does_not_exist(self, text: str) -> None:
        """Scoped to the envelope table — other tables document other things."""
        table = text.split("| Key | Type | Meaning |", 1)[1].split("\n\n", 1)[0]
        documented = set(re.findall(r"^\|\s*`(\w+)`\s*\|", table, re.M))
        assert documented == set(ENVELOPE_KEYS)

    def test_the_sample_envelope_carries_exactly_the_real_keys(self, text: str) -> None:
        """The first JSON block is what a reader will copy."""
        blocks = re.findall(r"```json\n(\{.*?\n\})\n```", text, re.S)
        envelope = next((b for b in blocks if '"gate":' in b), None)
        assert envelope, "no sample envelope in the document"
        shown = set(re.findall(r'^\s*"(\w+)":', envelope, re.M))
        assert shown == set(ENVELOPE_KEYS)


class TestExitCodesMatch:
    def test_documented_codes_are_the_real_ones(self, text: str) -> None:
        documented = set(re.findall(r"^\|\s*`(\d)`\s*\|", text, re.M))
        assert documented == set(gates_manifest()["exit_codes"])


class TestBlockingVocabulary:
    @pytest.mark.parametrize("value", BLOCKING)
    def test_every_blocking_value_is_explained(self, value: str, text: str) -> None:
        assert f"`{value}`" in text, (
            f"blocking value '{value}' appears in the manifest but is not "
            f"explained in the interface document"
        )


class TestPromisesAreKeptElsewhere:
    """The document claims properties other tests enforce; check they exist."""

    def test_claims_a_failing_gate_populates_errors(self, text: str) -> None:
        assert "always populates `errors`" in text

    def test_claims_stderr_is_not_a_contract(self, text: str) -> None:
        assert "stderr is not a contract" in text.lower() or \
               "**stderr is not a contract**" in text

    def test_names_the_gates_that_wait_for_a_class(self, text: str) -> None:
        opt_in = [g["command"] for g in GATES if g["blocking"] == "opt_in"]
        for command in opt_in:
            assert f"`{command}`" in text, (
                f"{command} is opt_in but the document does not say so"
            )


class TestDocumentIsReachable:
    def test_linked_from_adopting_or_readme(self) -> None:
        root = DOC.parents[1]
        readme = (root / "README.md").read_text()
        adopting = (root / "docs" / "adopting.md").read_text()
        assert "interface.md" in readme or "interface.md" in adopting, (
            "a contract nobody can find is not a contract"
        )

    def test_internal_links_resolve(self, text: str) -> None:
        for target in re.findall(r"\]\((\w[\w./-]*\.md)(?:#[\w-]+)?\)", text):
            assert (DOC.parent / target).exists(), f"broken link: {target}"
