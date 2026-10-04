"""A project says what belongs at each level, and the plan prompt carries it.

`build plan` had tier names and nothing on where one tier ends and the next begins, so
the model decided the level of a new item, and whether to create one at all, by guessing.
A doc type's `description` is the project's own answer; the starter ships one for the
requirement tiers.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

import dhfkit

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf

DEFAULTS = Path(dhfkit.__file__).parent / "templates" / "config" / "doc_types"
SECTION = "### What Belongs at Each Level"


def _project(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Levels")
    return tmp_path / "DHF"


def _prompt(dhf: Path) -> str:
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "plan", "--cr", "CR-001", "--prompt"])
    assert result.exit_code == 0, result.stderr
    return result.stdout


def _set_description(dhf: Path, code: str, description: str | None) -> None:
    """Override the type the way a project does: its own file beside the defaults."""
    name = f"{code.lower()}.yaml"
    path = dhf / "config" / "doc_types" / name
    path.parent.mkdir(exist_ok=True)
    data = yaml.safe_load((DEFAULTS / name).read_text())
    if description is None:
        data.pop("description", None)
    else:
        data["description"] = description
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def test_the_starter_tells_the_model_where_each_requirement_tier_ends(tmp_path: Path) -> None:
    prompt = _prompt(_project(tmp_path))
    assert SECTION in prompt
    for code in ("CRS", "SYS", "SRS"):
        assert f"**{code} — " in prompt
    assert "Not here:" in prompt


def test_a_project_describes_its_own_type_in_its_own_words(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    _set_description(dhf, "SYS", "A hardware interlock the clinic can inspect.")
    prompt = _prompt(dhf)
    assert "A hardware interlock the clinic can inspect." in prompt
    assert "behaviour observable at the system boundary" not in prompt


def test_a_type_without_a_description_is_left_out(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    _set_description(dhf, "SRS", None)
    prompt = _prompt(dhf)
    assert "**SYS — " in prompt
    assert "**SRS — " not in prompt


def test_a_project_that_describes_nothing_gets_no_empty_section(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    for code in ("UC", "CRS", "SYS", "SRS", "SYSARCH"):
        _set_description(dhf, code, None)
    assert SECTION not in _prompt(dhf)
