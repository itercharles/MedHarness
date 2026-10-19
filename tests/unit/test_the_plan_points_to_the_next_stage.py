"""The plan prompt names the stage that follows it, at the top.

A coding agent that had just designed a CR, told by the user to go on, wrote the code from its own plan and never read
the next stage's instructions. The prompt is the one place both the CI agent and a local one read, so the pointer lives
there and not in a skill, which can neither force it nor stay in step with the prompt.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


def test_the_prompt_names_build_code_for_this_cr_and_the_dhf_in_use(tmp_path: Path) -> None:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Next")
    (tmp_path / "DHF").rename(tmp_path / "Records")

    result = CliRunner().invoke(main, ["--dhf", str(tmp_path / "Records"), "build", "plan", "--cr", "CR-001", "--prompt"])

    assert result.exit_code == 0, result.stderr
    assert "medharness --dhf Records build code --cr CR-001 --prompt" in result.stdout
    assert result.stdout.index("build code --cr CR-001 --prompt") < result.stdout.index("## Inputs"), (
        "the pointer is read before the DHF context, which can run to tens of thousands of characters")
