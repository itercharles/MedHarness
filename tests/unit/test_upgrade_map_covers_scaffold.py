"""Every file `init` writes must be classified, so none can be forgotten.

`_UPGRADE_MAP` is hand-written. `config/doc_types/apr.yaml` was left out of it
while all twelve sibling doc types were listed, and nothing noticed: a project
that upgraded rather than scaffolded never received the APR doc type, so
`dhfkit item create --type APR` failed with "Unknown doc type" — and
`verify completion`, which requires an APR item, could not be satisfied at all.

`config/safety_activities.yaml` was missing the same way, with a quieter
failure: `verify classification` and `verify plans` ran, found no activities to
require, and exited 0. A green build that checked nothing.

The maps still have to be maintained by hand — the categories are judgements a
test cannot make. What this file removes is the possibility of forgetting
silently.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from medharness.workflows.init import _replace_placeholders, _scaffold_dhf
from medharness.workflows.upgrade import (
    _SEED_MAP,
    _TEMPLATES_DIR,
    _UPGRADE_MAP,
    _USER_OWNED,
)


@pytest.fixture(scope="module")
def scaffolded(tmp_path_factory) -> set[str]:
    """What `medharness init` actually writes, minus the sample DHF items."""
    root = tmp_path_factory.mktemp("scaffold")
    _scaffold_dhf(root)
    _replace_placeholders(root, "Coverage Check")
    return {
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and not str(p.relative_to(root)).startswith("DHF/items/")
    }


def _managed() -> set[str]:
    return {proj for _tmpl, proj in _UPGRADE_MAP}


def _seeded() -> set[str]:
    return {proj for _tmpl, proj in _SEED_MAP}


def test_every_scaffolded_file_is_classified(scaffolded: set[str]) -> None:
    unclassified = scaffolded - _managed() - _seeded() - set(_USER_OWNED)
    assert not unclassified, (
        "these files are written by init but no upgrade category claims them, so "
        "a project that upgrades never receives them:\n  "
        + "\n  ".join(sorted(unclassified))
    )


def test_no_category_claims_a_file_init_does_not_write(scaffolded: set[str]) -> None:
    """A stale entry is the same defect pointing the other way."""
    claimed = _managed() | _seeded() | set(_USER_OWNED)
    orphaned = claimed - scaffolded
    assert not orphaned, (
        "claimed by an upgrade category but never scaffolded:\n  "
        + "\n  ".join(sorted(orphaned))
    )


def test_the_categories_do_not_overlap() -> None:
    """A file in two categories has two behaviours and one of them is wrong."""
    managed, seeded, owned = _managed(), _seeded(), set(_USER_OWNED)
    assert not managed & seeded, managed & seeded
    assert not managed & owned, managed & owned
    assert not seeded & owned, seeded & owned


@pytest.mark.parametrize("tmpl,proj", list(_UPGRADE_MAP) + list(_SEED_MAP),
                         ids=[p for _t, p in list(_UPGRADE_MAP) + list(_SEED_MAP)])
def test_every_mapped_template_ships_in_this_build(tmpl: str, proj: str) -> None:
    """A map entry with no template silently manages nothing."""
    assert (_TEMPLATES_DIR / tmpl).exists(), f"{proj}: template {tmpl} is not packaged"


def test_every_doc_type_is_managed(scaffolded: set[str]) -> None:
    """Doc types define the schema; a project must not be left on an old one.

    Stated separately from the blanket check because this is the case that
    actually broke, and a named test says so when it breaks again.
    """
    doc_types = {f for f in scaffolded if f.startswith("DHF/config/doc_types/")}
    assert doc_types, "no doc types scaffolded — the fixture is wrong"
    assert doc_types <= _managed(), f"unmanaged doc types: {sorted(doc_types - _managed())}"


class TestSeededFilesBelongToTheProject:
    """Seeded files carry project decisions; upgrade must not overwrite them.

    `safety_activities.yaml` is an interpretation of the §5 activity table that
    the project is expected to edit. If upgrade treated it like a managed file,
    an edited copy would read as "outdated" and --apply would silently replace
    the project's agreed scope with the shipped default.
    """

    def _project(self, tmp_path: Path) -> Path:
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Seeded")
        return tmp_path

    def test_an_edited_seed_file_is_never_reported_outdated(self, tmp_path: Path) -> None:
        from medharness.workflows.upgrade import check_upgrade

        root = self._project(tmp_path)
        target = root / "DHF" / "config" / "safety_activities.yaml"
        target.write_text(target.read_text() + "\n# this project's own decision\n")

        report = check_upgrade(root)
        outdated = {e["file"] for e in report["outdated"]}
        assert "DHF/config/safety_activities.yaml" not in outdated

    def test_apply_does_not_overwrite_an_edited_seed_file(self, tmp_path: Path) -> None:
        from medharness.workflows.upgrade import apply_upgrade

        root = self._project(tmp_path)
        target = root / "DHF" / "config" / "safety_activities.yaml"
        edited = target.read_text() + "\n# this project's own decision\n"
        target.write_text(edited)

        apply_upgrade(root)
        assert target.read_text() == edited, "upgrade discarded the project's edits"

    def test_a_missing_seed_file_is_created(self, tmp_path: Path) -> None:
        from medharness.workflows.upgrade import apply_upgrade

        root = self._project(tmp_path)
        target = root / "DHF" / "config" / "safety_activities.yaml"
        target.unlink()

        apply_upgrade(root)
        assert target.exists(), "a project upgrading from an older version never gets it"
