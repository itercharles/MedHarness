"""A CR whose work stopped can be recorded as cancelled.

`cancelled` was a terminal phase in the code and a state in the lifecycle, and
no transition reached it: a CR whose pull request closed unmerged could only be
left `design` or `develop` forever, or wrongly marked `rejected` — which is the
triage verdict, not an abandoned change.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dhfkit.item_store import ItemStore
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def adapter(tmp_path: Path) -> ItemStore:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Cancel")
    return ItemStore(tmp_path / "DHF")


@pytest.mark.parametrize("path", [[], ["design"], ["design", "develop"]],
                         ids=["from new", "from design", "from develop"])
def test_an_active_cr_can_be_cancelled(adapter: ItemStore, path: list[str]) -> None:
    for state in path:
        adapter.execute_transition("CR-001", state)
    adapter.execute_transition("CR-001", "cancelled")
    assert adapter.get_item("CR-001")["status"] == "cancelled"


def test_the_ai_stages_refuse_a_cancelled_cr(adapter: ItemStore, tmp_path: Path) -> None:
    adapter.execute_transition("CR-001", "cancelled")
    for stage in ("plan", "code"):
        result = CliRunner().invoke(
            main, ["--dhf", str(tmp_path / "DHF"), "build", stage, "--cr", "CR-001", "--prompt"])
        assert result.exit_code == 1
        assert "already 'cancelled'" in result.stderr
