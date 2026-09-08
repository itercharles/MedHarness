"""A criterion the engine cannot read must block, not pass.

`_validate_criteria` was an if/elif chain with no else. A `check_type` the
engine did not recognise — a typo, or a key that predates a rename — fell off
the end and the criterion simply never blocked. A project would have configured
a gate, watched it approve everything, and had nothing to tell it apart from a
gate that was satisfied.

This is the shape of defect this codebase keeps producing: a misconfiguration
that looks exactly like success. `required_test_levels` written with the wrong
YAML indentation disabled level checking and reported a pass; the `command`
example in `soup-sources.yaml` collapsed to one unparseable line; here a
mistyped `check_type` opens the gate it was meant to close.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from dhfkit.lifecycle import _validate_criteria

LIFECYCLE = Path(__file__).resolve().parents[1] / "lifecycle.py"
DOC_TYPES = Path(__file__).resolve().parents[1] / "templates" / "config" / "doc_types"


def _required(check_type, field="x"):
    c = {"id": "c1", "required": True, "field": field}
    if check_type is not None:
        c["check_type"] = check_type
    return [c]


class TestAnUnreadableCriterionBlocks:
    @pytest.mark.parametrize("check_type", [
        "field_not_emty",        # a typo
        "field_nonempty",        # a plausible alternative spelling
        "relationship",          # the format name, not the check name
        "",
        None,                    # omitted entirely
    ])
    def test_it_does_not_silently_pass(self, check_type) -> None:
        ok, blocking = _validate_criteria({}, _required(check_type))
        assert not ok, (
            f"check_type {check_type!r} let the transition through — a gate "
            f"nobody configured correctly approves everything"
        )
        assert blocking

    def test_the_reason_names_the_criterion_and_the_type(self) -> None:
        """`Blocking criteria not met: c1` alone would send a reader to the
        field, which is fine. The cause is the check_type."""
        _ok, blocking = _validate_criteria({}, _required("field_not_emty"))
        assert "c1" in blocking[0]
        assert "field_not_emty" in blocking[0]

    @pytest.mark.parametrize("check_type", ["field_not_empty", "field_present",
                                            "relationship_field"])
    def test_a_known_type_still_behaves(self, check_type) -> None:
        satisfied = {"x": "value"}
        assert _validate_criteria(satisfied, _required(check_type))[0]
        assert not _validate_criteria({}, _required(check_type))[0]

    def test_an_optional_criterion_is_still_skipped(self) -> None:
        """`required: false` means advisory; an unknown type must not promote it."""
        crit = [{"id": "c1", "check_type": "nonsense", "field": "x", "required": False}]
        assert _validate_criteria({}, crit)[0]


class TestEveryShippedCriterionIsReadable:
    """The templates must not carry a type the engine dropped.

    With the fix above, a stale `check_type` in a shipped doc type would block
    every transition using it. That is the safe direction, but it would still be
    a broken scaffold, so it is worth catching here rather than in a project.
    """

    def _supported(self) -> set[str]:
        return set(re.findall(r'check_type == "(\w+)"', LIFECYCLE.read_text()))

    def test_no_template_uses_an_unknown_check_type(self) -> None:
        supported = self._supported()
        assert supported, "could not read the supported check types"
        for path in sorted(DOC_TYPES.glob("*.yaml")):
            for transition in (yaml.safe_load(path.read_text())
                               .get("lifecycle", {}).get("transitions", [])):
                for criterion in transition.get("criteria", []):
                    assert criterion.get("check_type") in supported, (
                        f"{path.name}: criterion {criterion.get('id')!r} uses "
                        f"{criterion.get('check_type')!r}, which the engine does "
                        f"not implement — it would block every transition"
                    )

    def test_every_criterion_names_a_field(self) -> None:
        for path in sorted(DOC_TYPES.glob("*.yaml")):
            for transition in (yaml.safe_load(path.read_text())
                               .get("lifecycle", {}).get("transitions", [])):
                for criterion in transition.get("criteria", []):
                    assert criterion.get("field"), (
                        f"{path.name}: criterion {criterion.get('id')!r} has no field"
                    )
