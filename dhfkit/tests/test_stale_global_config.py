"""A doc type may outgrow the global.yaml a project scaffolded with.

`global.yaml` is project-owned — it holds the safety class, its rationale, and
the traceability rules — so `medharness upgrade` never rewrites it. That is the
right call for those. But the same file also defines `global_lifecycle.states`,
which shipped doc types reference: `cr.yaml` transitions to `design` and
`develop`, states added after v0.14.

`get_available_transitions` used to `continue` past a transition whose target it
could not resolve. The transition simply was not offered, so a configuration
fault looked like a rule — a scaffolded CR could not reach `completed`, and the
only symptom was that `completed` was absent from the list. v0.18.0 fixed the
template; a project that scaffolded earlier still carries the old file and
cannot receive the fix.

The transition is reported now, unavailable, saying which state is undefined.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import dhfkit.api as api
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def aged(tmp_path: Path) -> Path:
    """A DHF whose global.yaml predates the states its doc types use."""
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Aged")
    dhf = tmp_path / "DHF"
    config = dhf / "config" / "global.yaml"
    data = yaml.safe_load(config.read_text())
    data["global_lifecycle"]["states"] = [
        s for s in data["global_lifecycle"]["states"]
        if s["id"] not in ("design", "develop")
    ]
    config.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return dhf


class TestAnUndefinedTargetIsReportedNotDropped:
    def test_the_transition_still_appears(self, aged: Path) -> None:
        offered = {t["to_state"] for t in api.get_item_transitions(aged, "CR-001")}
        assert "design" in offered, (
            "the transition vanished — a reader sees a rule where there is a "
            "broken config"
        )

    def test_it_is_marked_unavailable_with_the_reason(self, aged: Path) -> None:
        design = next(t for t in api.get_item_transitions(aged, "CR-001")
                      if t["to_state"] == "design")
        assert design["can_transition"] is False
        reason = " ".join(design["blocking_criteria"])
        assert "design" in reason and "global_lifecycle.states" in reason

    def test_executing_it_says_what_is_wrong(self, aged: Path) -> None:
        with pytest.raises(ValueError) as exc:
            api.transition_item(aged, "CR-001", "design")
        message = str(exc.value)
        assert "not defined in global_lifecycle.states" in message, message
        assert "is not allowed from state" not in message, (
            "the old message blamed the state machine for a config gap"
        )

    def test_a_resolvable_transition_is_unaffected(self, aged: Path) -> None:
        rejected = next(t for t in api.get_item_transitions(aged, "CR-001")
                        if t["to_state"] == "rejected")
        assert rejected["can_transition"] is True


class TestTheCurrentScaffoldIsSelfConsistent:
    """Every state a shipped doc type targets must exist in global.yaml.

    This is the check that would have caught the original defect at the source,
    rather than after a project hit it.
    """

    def _templates(self) -> Path:
        return Path(__file__).resolve().parents[1] / "templates" / "config"

    def test_no_doc_type_targets_an_undefined_state(self) -> None:
        cfg = self._templates()
        defined = {
            s["id"] for s in
            yaml.safe_load((cfg / "global.yaml").read_text())["global_lifecycle"]["states"]
        }
        problems = []
        for path in sorted((cfg / "doc_types").glob("*.yaml")):
            lifecycle = yaml.safe_load(path.read_text()).get("lifecycle") or {}
            for transition in lifecycle.get("transitions", []):
                target = transition.get("to_state")
                if target and target not in defined:
                    problems.append(f"{path.name}: → {target}")
                for origin in transition.get("from_states") or []:
                    if origin is not None and origin not in defined:
                        problems.append(f"{path.name}: from {origin}")
        assert not problems, (
            "doc types reference states global.yaml does not define:\n  "
            + "\n  ".join(problems)
        )
