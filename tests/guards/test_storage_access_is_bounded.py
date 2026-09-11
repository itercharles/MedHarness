"""medharness asks the store, except where it builds the store.

`init` and `upgrade` write DHF files directly, and that is a decision rather
than drift: those commands create and maintain the repository skeleton, not the
records inside it. `dhfkit` manages records; giving it a "write my config file"
API to satisfy a rule would put storage in the business of scaffolding.

Everywhere else, reaching for a DHF path is a duplicate of something the store
already does — and does better. `upgrade` parsed global.yaml with a regex that
took a trailing comment as part of the project name; `verify plans` walked
`documents/plans/*.md` because `list_documents()` gave stems with no way to ask
for one category.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MEDHARNESS = ROOT / "medharness"

#: Scaffolding: creating a DHF and keeping its skeleton current.
SCAFFOLD = {"medharness/workflows/init.py", "medharness/workflows/upgrade.py"}

#: A path *built* into the DHF: the `/` join operator followed by one of its
#: directories. A JSON key, a git argument, a variable named doc_types, and a
#: filename quoted inside an error message written for a person are all strings
#: that mention the DHF without reaching into it.
DHF_CONTENT = re.compile(r'/\s*["\'](?:documents|items|config)["\']')


def _modules() -> list[Path]:
    return [
        p for p in sorted(MEDHARNESS.rglob("*.py"))
        if "tests" not in p.parts and "prompts" not in p.parts
    ]


MODULES = _modules()


def test_the_scan_found_modules() -> None:
    assert len(MODULES) > 15, f"only {len(MODULES)} — the scan is broken"


def test_only_the_scaffold_names_dhf_directories() -> None:
    offending = []
    for path in MODULES:
        rel = str(path.relative_to(ROOT))
        if rel in SCAFFOLD:
            continue
        offending += [
            f"{rel}:{i + 1}: {line.strip()[:90]}"
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines())
            if DHF_CONTENT.search(line) and not line.lstrip().startswith("#")
        ]
    assert not offending, (
        "these build a path into the DHF:\n  "
        + "\n  ".join(offending)
        + "\n\nAsk the store instead — list_documents(category), get_document(), "
          "list_items(), ProjectConfig.load(). Only init and upgrade write the "
          "repository skeleton."
    )


class TestTheStoreCanAnswerWhatWasAskedOfTheFilesystem:
    """The rule is only fair if the store offers the alternative."""

    def _adapter(self, tmp_path: Path):
        from dhfkit.local_adapter import LocalDHFAdapter
        from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Bounded")
        return LocalDHFAdapter(tmp_path / "DHF")

    def test_documents_can_be_listed_by_category(self, tmp_path: Path) -> None:
        plans = self._adapter(tmp_path).list_documents("plans")
        assert "development_plan" in plans
        assert not any("specification" in p for p in plans), (
            "the category filter let a spec through"
        )

    def test_an_unknown_category_is_empty_not_everything(self, tmp_path: Path) -> None:
        assert self._adapter(tmp_path).list_documents("nowhere") == []

    def test_a_document_path_is_available_for_reporting(self, tmp_path: Path) -> None:
        """`verify plans` names the file it complains about; a stem is not one."""
        path = self._adapter(tmp_path).document_path("development_plan")
        assert path is not None and path.name == "development_plan.md"

    def test_the_project_name_comes_from_the_config_loader(self, tmp_path: Path) -> None:
        """The regex took a trailing comment as part of the name."""
        from medharness.workflows.init import _replace_placeholders, _scaffold_dhf
        from medharness.workflows.upgrade import _read_project_name

        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Bounded")
        config = tmp_path / "DHF" / "config" / "global.yaml"
        config.write_text(
            re.sub(r"^project_name:.*$", "project_name: Planner  # the product",
                   config.read_text(encoding="utf-8"), count=1, flags=re.M),
            encoding="utf-8",
        )
        assert _read_project_name(tmp_path) == "Planner"
