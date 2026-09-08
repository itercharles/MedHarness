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

import dhfkit.api as api
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

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
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Lifecycle")
        dhf = tmp_path / "DHF"
        for state in ("design", "develop", "completed"):
            api.transition_item(dhf, "CR-001", state)
        assert api.get_item(dhf, "CR-001")["status"] == "completed"

    def test_an_undefined_state_is_still_refused(self, tmp_path: Path) -> None:
        """Widening the state list must not make the machine permissive."""
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Lifecycle")
        with pytest.raises(ValueError):
            api.transition_item(tmp_path / "DHF", "CR-001", "nonexistent")

    def test_skipping_a_state_is_still_refused(self, tmp_path: Path) -> None:
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Lifecycle")
        with pytest.raises(ValueError):
            api.transition_item(tmp_path / "DHF", "CR-001", "completed")
