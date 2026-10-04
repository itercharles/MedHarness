"""The V-model defaults a project gets: which layer links to which, and which covers which.

They are written once, in the shipped `global.yaml`, and a project overrides them there.
"""

from __future__ import annotations

from dhfkit.models.config import ProjectConfig


def _load() -> ProjectConfig:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config"
        config.mkdir()
        (config / "global.yaml").write_text("project_name: Defaults\n")
        return ProjectConfig.load(config)


def test_the_default_rules_cover_the_vmodel_chain():
    rule_keys = {(r.source_type, r.field, r.target_type) for r in _load().required_traceability}
    assert ("SRS", "derives_from", "SYS") in rule_keys
    assert ("SWDD", "implements", "SRS") in rule_keys
    assert ("SWDD", "module", "MODULE") in rule_keys
    assert ("RCM", "mitigates", "RISK") in rule_keys
    assert ("RCM", "implements", "SYS") in rule_keys


def test_the_default_chains_include_module_to_design():
    paths = {tuple(m.path) for m in _load().traceability_matrices}
    assert ("MODULE", "SWDD") in paths
    assert ("UC", "CRS", "SYS", "SRS", "SWDD") in paths


def test_a_project_that_names_its_own_rules_replaces_the_defaults():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config"
        config.mkdir()
        (config / "global.yaml").write_text("project_name: Own\nrequired_traceability: []\ntraceability_matrices: []\n")
        loaded = ProjectConfig.load(config)
    assert loaded.required_traceability == [] and loaded.traceability_matrices == []
