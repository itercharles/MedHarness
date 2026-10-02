"""`cr_context` — what `build plan` and `build code` are told about a CR.

Scoped by the CR's own state rather than a stage argument: before `build plan`
it has no `affected_items`, so the model needs the whole DHF to choose what to
change; after, it needs only what the CR affects. The keys are the same either
way; `scope` says which.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main
from dhfkit.item_store import ItemStore
from medharness.services.context import cr_context
from dhfkit.tests.fixtures import bare_dhf


def _make_dhf(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    bare_dhf(dhf)
    return dhf


def _write_cr(dhf: Path, cr_id: str, **fields) -> None:
    """Write a CR item YAML. Field values must be str, list[str|dict], or dict."""
    cr_dir = dhf / "items" / "07_cr"
    cr_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {cr_id}", f'title: "Test CR"']
    for k, v in fields.items():
        if isinstance(v, str):
            lines.append(f"{k}: {repr(v)}")
        elif isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            else:
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {repr(item) if isinstance(item, str) else item}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for dk, dv in v.items():
                lines.append(f"  {dk}: {repr(dv)}")
    (cr_dir / f"{cr_id}.yaml").write_text("\n".join(lines) + "\n")


def _context(dhf: Path, cr_id: str) -> dict:
    return cr_context(ItemStore(dhf), cr_id)


def _srs(dhf: Path) -> str:
    created = CliRunner().invoke(main, [
        "--dhf", str(dhf), "item", "create", "--type", "SRS",
        "--data", json.dumps({"title": "Req", "verification_criteria": "T1 passes"}),
    ])
    assert created.exit_code == 0, created.output
    return json.loads(created.output.splitlines()[0])["id"]


KEYS = {"project", "cr", "scope", "types", "items", "modules", "risks", "chains"}


class TestTheShapeDoesNotDependOnTheCR:
    def test_the_same_keys_before_and_after_build_plan(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001")
        _write_cr(dhf, "CR-002", affected_items=[_srs(dhf)])
        before, after = _context(dhf, "CR-001"), _context(dhf, "CR-002")
        assert set(before) == set(after) == KEYS
        assert (before["scope"], after["scope"]) == ("whole_dhf", "affected")


class TestBeforeTheCRRecordsWhatItAffects:
    def test_every_item_summarized_and_the_full_cr(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        srs = _srs(dhf)
        _write_cr(dhf, "CR-001", triage_result={"verdict": "approved"})
        payload = _context(dhf, "CR-001")
        assert payload["scope"] == "whole_dhf"
        assert payload["cr"]["triage_result"]["verdict"] == "approved"
        assert [it["id"] for it in payload["items"]] == ["CR-001", srs], (
            "choosing what to change needs the whole DHF")
        assert "verification_criteria" not in payload["items"][1], "the whole DHF is summarized"


class TestAfterTheCRRecordsWhatItAffects:
    def test_only_the_affected_items_in_full(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        srs = _srs(dhf)
        _write_cr(dhf, "CR-001", affected_items=[srs],
                  implementation_notes="Plan.")
        payload = _context(dhf, "CR-001")
        assert payload["scope"] == "affected"
        assert [it["id"] for it in payload["items"]] == [srs]
        assert payload["items"][0]["verification_criteria"] == "T1 passes"
        assert payload["cr"]["implementation_notes"] == "Plan."


def test_an_unknown_cr_says_so(tmp_path: Path) -> None:
    assert _context(_make_dhf(tmp_path), "CR-999")["cr"] == {"id": "CR-999", "found": False}


def test_types_name_the_project_codes(tmp_path: Path) -> None:
    types = _context(_make_dhf(tmp_path), "CR-001")["types"]
    sys_type = next(t for t in types if t["code"] == "SYS")
    assert sys_type["display_name"] == "System Requirement" and sys_type["role"] == "system_requirement"
    assert [(l["field"], l["targets"]) for l in sys_type["links"]] == [("satisfies", ["CRS"])]


def test_project_survives_a_relative_dhf_path(tmp_path: Path, monkeypatch) -> None:
    """`--dhf DHF` is how the docs and the CI recipe invoke the stages, and
    `Path("DHF").parent.name` is the empty string."""
    _make_dhf(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert _context(Path("DHF"), "CR-001")["project"], "project name came back empty"


class TestThePlanPromptForALargeDHF:
    """`build plan` cannot list a thousand items; it lists where requirements enter."""

    def _plan_prompt(self, dhf: Path) -> str:
        from medharness.services.prompt_assembly import _assemble_generate_dhf_prompt

        return _assemble_generate_dhf_prompt("CR-001", dhf_path=dhf)

    def _items(self, dhf: Path) -> tuple[str, str]:
        runner = CliRunner()
        entry = json.loads(runner.invoke(main, [
            "--dhf", str(dhf), "item", "create", "--type", "UC", "--data", '{"title": "Entry item"}',
        ]).output.splitlines()[0])["id"]
        return entry, _srs(dhf)

    def test_above_the_limit_only_entry_types_are_listed(self, tmp_path: Path, monkeypatch) -> None:
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001")
        entry, srs = self._items(dhf)
        monkeypatch.setattr("medharness.services.prompt_assembly.MAX_ITEMS", 2)

        prompt = self._plan_prompt(dhf)

        assert f"- {entry} — Entry item" in prompt
        assert f"- {srs} —" not in prompt
        assert "item list --brief" in prompt
        assert "SRS: 1" in prompt, "the type counts still say what the DHF holds"

    def test_at_the_limit_every_item_is_listed(self, tmp_path: Path, monkeypatch) -> None:
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001")
        entry, srs = self._items(dhf)
        monkeypatch.setattr("medharness.services.prompt_assembly.MAX_ITEMS", 3)

        prompt = self._plan_prompt(dhf)

        assert f"- {entry} —" in prompt and f"- {srs} —" in prompt


class TestWhatThePlanPromptRenders:
    def test_a_risk_line_carries_no_empty_severity_bracket(self, tmp_path: Path) -> None:
        from medharness.services.prompt_assembly import _assemble_generate_dhf_prompt

        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001")
        CliRunner().invoke(main, [
            "--dhf", str(dhf), "item", "create", "--type", "RISK", "--data", '{"title": "Wrong patient"}',
        ])

        prompt = _assemble_generate_dhf_prompt("CR-001", dhf_path=dhf)

        assert "Wrong patient" in prompt
        assert "[—" not in prompt

    def test_the_prompt_is_generic(self, tmp_path: Path) -> None:
        from medharness.services.prompt_assembly import _assemble_generate_dhf_prompt

        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001")

        prompt = _assemble_generate_dhf_prompt("CR-001", dhf_path=dhf)

        for stale in ("one per SRS requirement", "one per SYS requirement", "development_plan.md", "DICOM"):
            assert stale not in prompt


class TestTheDesignReviewSeesTheNeighbourhood:
    """The review reads a diff; what sits beside a changed item is added from the DHF."""

    def _create(self, dhf: Path, type_: str, **data) -> str:
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "create", "--type", type_,
                                      "--data", json.dumps(data)])
        assert r.exit_code == 0, r.output
        return json.loads(r.stdout.splitlines()[0])["id"]

    def _review_prompt(self, dhf: Path, **changed) -> str:
        from medharness.services.prompt_assembly import _assemble_review_design_prompt

        return _assemble_review_design_prompt(
            "CR-001", dhf, {"created": [], "updated": [], "deleted": [], **changed})

    def _dhf(self, tmp_path: Path) -> tuple[Path, str, list[str]]:
        dhf = _make_dhf(tmp_path)
        sys_ = self._create(dhf, "SYS", title="Export report", category="Functional", content="Exports.")
        srs = [self._create(dhf, "SRS", title=f"Export rule {n}", derives_from=[sys_],
                            verification_criteria="T1 passes") for n in range(3)]
        return dhf, sys_, srs

    def test_a_changed_item_comes_with_its_parent_and_its_siblings(self, tmp_path: Path) -> None:
        dhf, sys_, srs = self._dhf(tmp_path)

        prompt = self._review_prompt(dhf, updated=[srs[0]])

        assert f"### {srs[0]} — Export rule 0 (updated)" in prompt
        assert f"Parent chain: {sys_} — Export report" in prompt
        assert f"{srs[1]} — Export rule 1" in prompt and f"{srs[2]} — Export rule 2" in prompt
        assert "(2)" in prompt

    def test_siblings_are_capped_with_a_count_of_the_rest(self, tmp_path: Path) -> None:
        dhf, sys_, srs = self._dhf(tmp_path)
        for n in range(3, 20):
            self._create(dhf, "SRS", title=f"Export rule {n}", derives_from=[sys_], verification_criteria="T1")

        prompt = self._review_prompt(dhf, updated=[srs[0]])

        assert "(19)" in prompt and "and 4 more" in prompt

    def test_a_created_item_that_duplicates_a_neighbour_names_it(self, tmp_path: Path) -> None:
        dhf, sys_, srs = self._dhf(tmp_path)
        twin = self._create(dhf, "SRS", title="Export rule 1", derives_from=[sys_], verification_criteria="T1")

        prompt = self._review_prompt(dhf, created=[twin])

        assert f"Closest existing item of the same type: {srs[1]} — Export rule 1 (similarity 1.00)" in prompt

    def test_an_unlike_created_item_names_no_twin(self, tmp_path: Path) -> None:
        dhf, sys_, _ = self._dhf(tmp_path)
        other = self._create(dhf, "SRS", title="Authenticate users with a one-time code",
                             content="Send a six digit code by SMS.", derives_from=[sys_],
                             verification_criteria="T1")

        assert "Closest existing item" not in self._review_prompt(dhf, created=[other])

    def test_an_item_where_requirements_enter_has_no_parent_chain(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        uc = self._create(dhf, "UC", title="Export a report")

        assert "none (this is where requirements enter)" in self._review_prompt(dhf, updated=[uc])

    def test_a_change_that_touched_no_item_adds_nothing(self, tmp_path: Path) -> None:
        dhf, _, _ = self._dhf(tmp_path)

        assert "## Neighbourhood of the Changed Items" not in self._review_prompt(dhf)
