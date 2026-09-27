"""Which types are requirements is the config's answer, not the gates'.

`verify tests` took `--requirement-type`, defaulting to a list hardcoded in two
gates and a design check — `SRS, SYS, CRS` — while the config already said which
types are requirements, through each type's role. A project adding its own
requirement type had to remember the flag; three lists had to stay in step.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from dhfkit.models.config import ProjectConfig

TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "config"


def test_the_shipped_requirement_types() -> None:
    assert sorted(ProjectConfig.load(TEMPLATES).requirement_types()) == ["CRS", "SRS", "SYS"]


def test_design_detail_is_not_a_requirement() -> None:
    """SWDD tracks a verification status too; that does not make it one."""
    assert "SWDD" not in ProjectConfig.load(TEMPLATES).requirement_types()


def test_a_project_type_with_a_requirement_role_is_one(tmp_path: Path) -> None:
    config = tmp_path / "config"
    shutil.copytree(TEMPLATES, config)
    (config / "doc_types" / "hwr.yaml").write_text(yaml.safe_dump({
        "code": "HWR", "name": "Hardware Requirement", "prefix": "HWR-",
        "directory": "20_hwr", "role": "hardware_requirement", "properties": ["id"],
    }))
    assert "HWR" in ProjectConfig.load(config).requirement_types()
