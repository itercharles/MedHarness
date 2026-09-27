"""`medharness context` — one command, scoped by the CR's own state.

It replaced `overview`, `implementation` and `for-stage analyze|design|develop`.
The stage argument encoded something the CR already records: before `build plan`
it has no `affected_items`, so an agent needs the whole DHF to choose what to
change; after, it needs only what the CR affects.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from dhfkit.cli import main as dhfkit_main
from medharness.cli import main


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


def _invoke(dhf: Path, *args: str) -> dict:
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "context", *args])
    assert result.exit_code == 0, result.output
    return json.loads(result.output.splitlines()[0])


def _srs(dhf: Path) -> str:
    created = CliRunner().invoke(dhfkit_main, [
        "--dhf", str(dhf), "item", "create", "--type", "SRS",
        "--data", json.dumps({"title": "Req", "verification_criteria": "T1 passes"}),
    ])
    assert created.exit_code == 0, created.output
    return json.loads(created.output.splitlines()[0])["id"]


class TestWithoutACR:
    def test_the_whole_dhf_and_its_verdict(self, tmp_path: Path) -> None:
        payload = _invoke(_make_dhf(tmp_path))
        assert {"project", "item_count", "items", "traceability"} <= set(payload)
        assert "cr" not in payload

    def test_junit_adds_test_coverage(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        (tmp_path / "r.xml").write_text(
            '<testsuites><testsuite name="s" tests="1"><testcase classname="t" name="a"/>'
            "</testsuite></testsuites>")
        assert "test_coverage" in _invoke(dhf, "--junit", str(tmp_path / "r.xml"))


class TestBeforeTheCRRecordsWhatItAffects:
    def test_every_item_summarized_and_the_full_cr(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001", triage_result={"verdict": "approved"})
        payload = _invoke(dhf, "--cr", "CR-001")
        assert payload["cr"]["triage_result"]["verdict"] == "approved"
        assert payload["items"], "choosing what to change needs the whole DHF"
        assert "affected_items" not in payload


class TestAfterTheCRRecordsWhatItAffects:
    def test_only_the_affected_items_in_full(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        srs = _srs(dhf)
        _write_cr(dhf, "CR-001", affected_items=[srs],
                  implementation_notes="Plan.", proposed_new_items=[])
        payload = _invoke(dhf, "--cr", "CR-001")
        assert [it["id"] for it in payload["affected_items"]] == [srs]
        assert payload["affected_items"][0]["verification_criteria"] == "T1 passes"
        assert payload["cr"]["implementation_notes"] == "Plan."
        assert "items" not in payload
        assert "module_map" in payload


def test_an_unknown_cr_says_so(tmp_path: Path) -> None:
    assert _invoke(_make_dhf(tmp_path), "--cr", "CR-999")["cr"] == {"id": "CR-999", "found": False}
