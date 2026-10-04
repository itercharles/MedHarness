"""`build plan --prompt` and `build code --prompt` hand a running agent the stage.

An engineer's own agent does the DHF work locally; it must get the same steps
and the same DHF context the CI agent gets, and no second agent must start.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path, monkeypatch) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Local")

    def no_model(*a, **k):
        raise AssertionError("--prompt started a model")
    monkeypatch.setattr("medharness.services.llm._run_claude", no_model)
    return tmp_path / "DHF"


@pytest.mark.parametrize("stage,assemble", [
    ("plan", "_assemble_generate_dhf_prompt"),
    ("code", "_assemble_develop_prompt"),
])
def test_it_prints_what_the_ci_agent_is_given(dhf: Path, stage: str, assemble: str) -> None:
    from medharness.services import prompt_assembly

    r = CliRunner().invoke(main, ["--dhf", str(dhf), "build", stage, "--cr", "CR-001", "--prompt"])

    assert r.exit_code == 0, r.output
    assert r.stdout == getattr(prompt_assembly, assemble)("CR-001", dhf_path=dhf) + "\n"
    assert "CR-001" in r.stdout


def test_a_closed_cr_is_refused_here_too(dhf: Path) -> None:
    import dhfkit.api as api

    api.update_item(dhf, "CR-001", {"status": "rejected"})
    r = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "plan", "--cr", "CR-001", "--prompt"])
    assert r.exit_code != 0
