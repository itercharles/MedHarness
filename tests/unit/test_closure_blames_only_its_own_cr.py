"""A CR answers for what it changed, not for the DHF's backlog.

`cr_closure_gate` ran `validate_verification_completeness` over every item of
every type the CR proposed, so a starter `SRS-001` that never declared a
verification method failed the closure gate of an unrelated CR — and blocked
its merge. The gate already knew the scope: the CR's `affected_items` and the
items matching its `proposed_new_items`.
"""

from __future__ import annotations

from pathlib import Path

from medharness.services.ci import validate_verification_completeness


def _dhf_with_two_requirements(tmp_path: Path) -> Path:
    import subprocess
    import sys

    subprocess.run([sys.executable, "-c", "from medharness.cli import main; main()", "init"],
                   cwd=tmp_path, capture_output=True, check=False)
    dhf = tmp_path / "DHF"
    (dhf / "items" / "03_srs" / "SRS-002.yaml").write_text(
        "id: SRS-002\n"
        "derives_from:\n- SYS-001\n"
        "title: Scoped requirement\n"
        "verification_method:\n- Inspection\n"
        "verification_criteria: inspected\n"
        "type: SRS\n",
        encoding="utf-8",
    )
    return dhf


class TestScopeIsHonoured:
    def test_an_item_outside_the_scope_is_not_reported(self, tmp_path: Path) -> None:
        dhf = _dhf_with_two_requirements(tmp_path)

        unscoped = validate_verification_completeness(dhf, req_types=("SRS",))
        assert any(g["id"] == "SRS-001" for g in unscoped["details"]["missing_method"]), (
            "the starter SRS-001 declares no verification_method; if it stops "
            "being a gap this test proves nothing"
        )

        scoped = validate_verification_completeness(
            dhf, req_types=("SRS",), item_ids={"SRS-002"},
        )
        assert not any(g["id"] == "SRS-001"
                       for g in scoped["details"]["missing_method"]), (
            "SRS-001 is outside the given scope and was still reported"
        )

    def test_a_gap_inside_the_scope_is_still_reported(self, tmp_path: Path) -> None:
        """Scoping must narrow the blame, not disable the check."""
        dhf = _dhf_with_two_requirements(tmp_path)
        (dhf / "items" / "03_srs" / "SRS-002.yaml").write_text(
            "id: SRS-002\nderives_from:\n- SYS-001\ntitle: Scoped requirement\ntype: SRS\n",
            encoding="utf-8",
        )
        scoped = validate_verification_completeness(
            dhf, req_types=("SRS",), item_ids={"SRS-002"},
        )
        assert scoped["passed"] is False
        assert [g["id"] for g in scoped["details"]["missing_method"]] == ["SRS-002"]

    def test_no_scope_still_scans_everything(self, tmp_path: Path) -> None:
        """`verify tests` is a DHF-wide gate and must keep seeing the whole DHF."""
        dhf = _dhf_with_two_requirements(tmp_path)
        result = validate_verification_completeness(dhf, req_types=("SRS",))
        assert any(g["id"] == "SRS-001" for g in result["details"]["missing_method"])

    def test_an_empty_scope_reports_nothing(self, tmp_path: Path) -> None:
        """An empty set is a known-empty scope, not "unknown, scan it all"."""
        dhf = _dhf_with_two_requirements(tmp_path)
        result = validate_verification_completeness(dhf, req_types=("SRS",), item_ids=set())
        assert result["details"]["missing_method"] == []


class TestTheGateUsesTheScope:
    def test_the_closure_gate_does_not_report_an_unrelated_item(self, tmp_path: Path) -> None:
        import yaml

        from medharness.services.ci import cr_closure_gate

        dhf = _dhf_with_two_requirements(tmp_path)
        cr = dhf / "items" / "07_cr" / "CR-001.yaml"
        data = yaml.safe_load(cr.read_text())
        data.update({
            "proposed_new_items": [{"type": "SRS", "title": "Scoped requirement"}],
            "affected_items": ["SRS-002"],
            "implementation_notes": "n",
            "affected_risk_items": [],
            "triage_result": {"verdict": "approved"},
        })
        cr.write_text(yaml.safe_dump(data), encoding="utf-8")

        result = cr_closure_gate("CR-001", dhf)
        reported = [g["id"] for g in result["details"]["verification_gaps"]]
        assert "SRS-001" not in reported, (
            f"CR-001 touched SRS-002; the gate blamed it for {reported}"
        )
