"""The project keeps only what it changes; the package supplies the rest.

`init` used to copy about 900 lines of config into every project. The copy froze
the defaults at the version that scaffolded them, and `upgrade` existed only to
reconcile the copies. Now the defaults are read from the package and a project
overrides them file by file.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from dhfkit.models.config import ProjectConfig
from dhfkit.paths import DEFAULT_CONFIG_DIR


def _project(tmp_path: Path, global_yaml: str = 'project_name: "P"\n') -> Path:
    config = tmp_path / "config"
    config.mkdir()
    (config / "global.yaml").write_text(global_yaml)
    return config


def _default_codes() -> set[str]:
    return {yaml.safe_load(f.read_text())["code"]
            for f in (DEFAULT_CONFIG_DIR / "doc_types").glob("*.yaml")}


def test_a_one_line_project_has_every_default(tmp_path: Path) -> None:
    config = ProjectConfig.load(_project(tmp_path))
    assert config.project_name == "P"
    assert {dt.code for dt in config.doc_types} == _default_codes()
    assert config.required_traceability, "the default traceability rules were not inherited"


def test_a_project_doc_type_replaces_the_default_of_that_code(tmp_path: Path) -> None:
    config_dir = _project(tmp_path)
    (config_dir / "doc_types").mkdir()
    srs = yaml.safe_load((DEFAULT_CONFIG_DIR / "doc_types" / "srs.yaml").read_text())
    srs["name"] = "Our Software Requirement"
    (config_dir / "doc_types" / "srs.yaml").write_text(yaml.safe_dump(srs))

    config = ProjectConfig.load(config_dir)
    assert config.get_doc_type("SRS").name == "Our Software Requirement"
    assert [dt.code for dt in config.doc_types].count("SRS") == 1


def test_a_project_can_add_a_type(tmp_path: Path) -> None:
    config_dir = _project(tmp_path)
    (config_dir / "doc_types").mkdir()
    (config_dir / "doc_types" / "hwr.yaml").write_text(yaml.safe_dump({
        "code": "HWR", "name": "Hardware Requirement", "prefix": "HWR-", "properties": ["id"],
    }))
    assert ProjectConfig.load(config_dir).get_doc_type("HWR") is not None


def test_a_global_key_replaces_the_default_key(tmp_path: Path) -> None:
    config = ProjectConfig.load(_project(tmp_path, 'project_name: "P"\nrequired_traceability: []\n'))
    assert config.required_traceability == []


def test_omit_doc_types_drops_a_default(tmp_path: Path) -> None:
    config = ProjectConfig.load(_project(tmp_path, 'project_name: "P"\nomit_doc_types: [UC]\n'))
    assert "UC" not in {dt.code for dt in config.doc_types}


def test_global_yaml_still_marks_a_dhf(tmp_path: Path) -> None:
    """Without it the directory is not a DHF, and saying so is the useful error."""
    import pytest

    (tmp_path / "config").mkdir()
    with pytest.raises(FileNotFoundError, match="global.yaml"):
        ProjectConfig.load(tmp_path / "config")


class TestSpecificationsLandInsideTheDHF:
    """The defaults spelled outputs `DHF/documents/...` from the project root, so
    a DHF in a directory with any other name wrote its specifications outside
    itself."""

    def test_a_dhf_not_named_dhf_keeps_its_documents(self, tmp_path: Path) -> None:
        from dhfkit.local_adapter import LocalDHFAdapter
        from dhfkit.tests.fixtures import bare_dhf

        dhf = bare_dhf(tmp_path / "mydhf")
        LocalDHFAdapter(dhf).generate_doc("SRS")
        assert (dhf / "documents" / "specs").is_dir()
        assert not (tmp_path / "DHF").exists(), "wrote outside the DHF"

    def test_an_older_project_relative_path_still_resolves(self, tmp_path: Path) -> None:
        from dhfkit.document_generation import spec_output_path

        dhf = tmp_path / "DHF"
        assert spec_output_path(dhf, "DHF/documents/specs/x.md") == dhf / "documents" / "specs" / "x.md"
        assert spec_output_path(dhf, "documents/specs/x.md") == dhf / "documents" / "specs" / "x.md"
