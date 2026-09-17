"""A CR cannot be closed before it carries what closure means.

The reference project had eight CRs marked `completed` and all eight failed
`verify completion`. The most instructive was CR-012: the AI workflow wrote a
good plan, the process broke off before the approval gate, and someone
transitioned the CR to `completed` by hand. Nothing stopped them — the shipped
`cr.yaml` defined five transitions and zero criteria, so `completed` was
reachable from `develop` with no checks at all.

The lifecycle engine had supported blocking criteria since it was written. They
had simply never been configured for the doc type whose whole purpose is
recording that a change was carried out.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import dhfkit.api as api
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

CLOSURE = {
    "implementation_notes": "Toolbar updated.",
    "affected_risk_items": ["RISK-001"],
    "triage_result": {"verdict": "approved"},
}


@pytest.fixture
def cr(tmp_path: Path) -> tuple[Path, str]:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Closure")
    dhf = tmp_path / "DHF"
    for state in ("design", "develop"):
        api.transition_item(dhf, "CR-001", state)
    return dhf, "CR-001"


class TestClosureIsRefusedUntilTheRecordExists:
    def test_a_bare_cr_cannot_be_completed(self, cr) -> None:
        dhf, cr_id = cr
        with pytest.raises(ValueError) as exc:
            api.transition_item(dhf, cr_id, "completed")
        assert "implementation_recorded" in str(exc.value)
        assert api.get_item(dhf, cr_id)["status"] == "develop", "state changed anyway"

    @pytest.mark.parametrize("omit", sorted(CLOSURE))
    def test_each_field_is_required_on_its_own(self, cr, omit: str) -> None:
        """Named individually, so a reader knows which one to go and write."""
        dhf, cr_id = cr
        api.update_item(dhf, cr_id, {k: v for k, v in CLOSURE.items() if k != omit})
        with pytest.raises(ValueError) as exc:
            api.transition_item(dhf, cr_id, "completed")
        expected = {
            "implementation_notes": "implementation_recorded",
            "affected_risk_items": "risk_impact_assessed",
            "triage_result": "triaged",
        }[omit]
        assert expected in str(exc.value)

    def test_a_complete_record_closes(self, cr) -> None:
        dhf, cr_id = cr
        api.update_item(dhf, cr_id, CLOSURE)
        api.transition_item(dhf, cr_id, "completed")
        assert api.get_item(dhf, cr_id)["status"] == "completed"


class TestAssessedAndEmptyIsAnAnswer:
    """`affected_risk_items: []` means the risks were assessed and none apply.

    `verify completion` accepts it — it checks `isinstance(..., list)` and its
    own message says "use [] if none". A criterion reading falsy-as-absent would
    have been stricter than the gate it mirrors, and would have forced projects
    to invent an affected risk to close a CR that affects none.
    """

    def test_an_empty_list_satisfies_the_criterion(self, cr) -> None:
        dhf, cr_id = cr
        api.update_item(dhf, cr_id, {**CLOSURE, "affected_risk_items": []})
        api.transition_item(dhf, cr_id, "completed")
        assert api.get_item(dhf, cr_id)["status"] == "completed"

    def test_an_absent_field_still_blocks(self, cr) -> None:
        """Absent is not the same as empty: one is unassessed, one is assessed."""
        dhf, cr_id = cr
        api.update_item(dhf, cr_id, {
            k: v for k, v in CLOSURE.items() if k != "affected_risk_items"
        })
        with pytest.raises(ValueError, match="risk_impact_assessed"):
            api.transition_item(dhf, cr_id, "completed")


class TestTheCriteriaMirrorTheGate:
    """Two checks of the same thing must not disagree.

    A criterion stricter than `verify completion` would refuse a CR the gate
    would pass — the tool contradicting itself, with no way for a project to
    satisfy both.
    """

    def test_every_criterion_names_a_field_the_gate_checks(self) -> None:
        import importlib.resources as resources

        import yaml

        cr_yaml = yaml.safe_load(
            resources.files("dhfkit")
            .joinpath("templates/config/doc_types/cr.yaml").read_text()
        )
        transition = next(
            t for t in cr_yaml["lifecycle"]["transitions"]
            if t.get("to_state") == "completed"
        )
        fields = {c["field"] for c in transition.get("criteria", [])}
        assert fields, "the closing transition has no criteria"

        gate = (
            Path(__file__).resolve().parents[2]
            / "medharness" / "services" / "ci.py"
        ).read_text()
        for field in fields:
            assert field in gate, (
                f"closure requires {field!r}, which verify completion never "
                f"checks — the two would be enforcing different contracts"
            )
