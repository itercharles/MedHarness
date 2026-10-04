"""Every state a doc type transitions to must exist in the global lifecycle.

`cr.yaml` transitioned to `design` and `develop`; `global.yaml` listed only
`designing` and `developing`. `get_available_transitions` drops a transition
whose target it cannot resolve, silently — so a scaffolded CR could reach
nothing but `rejected`. `completed` was unreachable, and with it `verify
completion` and every release baseline that requires a completed CR.

Nothing failed. The transition was simply not offered.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dhfkit.store import open_store
from medharness.scaffold import replace_placeholders, scaffold_dhf

TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "config"


def _global_states() -> set[str]:
    doc = yaml.safe_load((TEMPLATES / "global.yaml").read_text(encoding="utf-8"))
    return {s["id"] for s in (doc.get("global_lifecycle") or {}).get("states", [])}


def _transition_targets() -> list[tuple[str, str]]:
    out = []
    for path in sorted((TEMPLATES / "doc_types").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for transition in (doc.get("lifecycle") or {}).get("transitions", []):
            target = transition.get("to_state")
            if target:
                out.append((doc["code"], target))
    return sorted(set(out))


TARGETS = _transition_targets()


def test_the_scan_found_transitions() -> None:
    assert len(TARGETS) >= 5, TARGETS


@pytest.mark.parametrize("code,target", TARGETS, ids=[f"{c}->{t}" for c, t in TARGETS])
def test_a_transition_target_exists_globally(code: str, target: str) -> None:
    assert target in _global_states(), (
        f"{code}.yaml transitions to '{target}', which global.yaml does not "
        f"define. get_available_transitions drops it silently, so the state is "
        f"simply unreachable."
    )


class TestTheScaffoldedCRCanReachCompleted:
    """The state every gate and release baseline depends on."""

    def test_the_full_path(self, tmp_path: Path) -> None:
        """Closing needs the record that closure is supposed to mean."""
        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Lifecycle")
        dhf = tmp_path / "DHF"
        for state in ("design", "develop"):
            open_store(dhf).execute_transition("CR-001", state)

        with pytest.raises(ValueError, match="implementation_recorded"):
            open_store(dhf).execute_transition("CR-001", "completed")

        open_store(dhf).update_item("CR-001", {
            "implementation_notes": "Toolbar updated.",
            "affected_risk_items": ["RISK-001"],
            "affected_items": ["SRS-001"],
            "triage_result": {"verdict": "approved"},
        })
        open_store(dhf).execute_transition("CR-001", "completed")
        assert open_store(dhf).get_item("CR-001")["status"] == "completed"

    def test_updating_a_field_does_not_undo_the_lifecycle(self, tmp_path: Path) -> None:
        """`update_item` reset any non-stable state to the initial one.

        Filling in a CR's required fields sent it back to `new`, so the criteria
        above could never be satisfied — the act of qualifying disqualified it.
        """
        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Lifecycle")
        dhf = tmp_path / "DHF"
        open_store(dhf).execute_transition("CR-001", "design")
        open_store(dhf).update_item("CR-001", {"implementation_notes": "x"})
        assert open_store(dhf).get_item("CR-001")["status"] == "design"

    def test_an_undefined_state_is_still_refused(self, tmp_path: Path) -> None:
        """Widening the state list must not make the machine permissive."""
        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Lifecycle")
        with pytest.raises(ValueError):
            open_store(tmp_path / "DHF").execute_transition("CR-001", "nonexistent")

    def test_skipping_a_state_is_still_refused(self, tmp_path: Path) -> None:
        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Lifecycle")
        with pytest.raises(ValueError):
            open_store(tmp_path / "DHF").execute_transition("CR-001", "completed")
