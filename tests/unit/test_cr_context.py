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

from dhfkit.cli import main as dhfkit_main
from dhfkit.local_adapter import LocalDHFAdapter
from medharness.services.context import cr_context


def _make_dhf(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
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
    return cr_context(LocalDHFAdapter(dhf), cr_id)


def _srs(dhf: Path) -> str:
    created = CliRunner().invoke(dhfkit_main, [
        "--dhf", str(dhf), "item", "create", "--type", "SRS",
        "--data", json.dumps({"title": "Req", "verification_criteria": "T1 passes"}),
    ])
    assert created.exit_code == 0, created.output
    return json.loads(created.output.splitlines()[0])["id"]


KEYS = {"project", "cr", "scope", "types", "items", "modules", "risks"}


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
                  implementation_notes="Plan.", proposed_new_items=[])
        payload = _context(dhf, "CR-001")
        assert payload["scope"] == "affected"
        assert [it["id"] for it in payload["items"]] == [srs]
        assert payload["items"][0]["verification_criteria"] == "T1 passes"
        assert payload["cr"]["implementation_notes"] == "Plan."


def test_an_unknown_cr_says_so(tmp_path: Path) -> None:
    assert _context(_make_dhf(tmp_path), "CR-999")["cr"] == {"id": "CR-999", "found": False}


def test_types_name_the_project_codes(tmp_path: Path) -> None:
    types = _context(_make_dhf(tmp_path), "CR-001")["types"]
    assert {"code": "SYS", "display_name": "System Requirement",
            "role": "system_requirement"} in types


def test_project_survives_a_relative_dhf_path(tmp_path: Path, monkeypatch) -> None:
    """`--dhf DHF` is how the docs and the CI recipe invoke the stages, and
    `Path("DHF").parent.name` is the empty string."""
    _make_dhf(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert _context(Path("DHF"), "CR-001")["project"], "project name came back empty"
