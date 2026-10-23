"""`verify approval --release` passes once each role has signed its documents' current hashes and the quality lead the release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from fixtures.approvals import Project, build_project, entry

SOFTWARE_LEAD_DOCUMENTS = ["SRS", "SWDD", "MODULE", "SOUP"]


@pytest.fixture
def project(tmp_path: Path) -> Project:
    project = build_project(tmp_path)
    project.ready_to_release()
    project.release()
    return project


def _created(result) -> dict:
    assert result.exit_code == 0, result.stderr
    return json.loads(result.stdout)


def test_the_software_lead_signs_the_documents_they_own_in_one_record(project: Project) -> None:
    created = _created(project.sign("Lead"))

    record = Path(created["path"])
    assert record.parent == project.dhf / "approvals" / "release-1.0.0"
    assert created["id"] == record.stem and created["release"] == "1.0.0"
    assert created["signer"] == "Lead" and created["roles"] == ["software-lead"]
    assert created["statement"] == "I have reviewed the changes to these documents and approve them for release."
    assert created["documents"] == [project.pin(code) for code in sorted(SOFTWARE_LEAD_DOCUMENTS)]
    assert record.with_name(record.name + ".sig").is_file()
    assert len(project.records()) == 1


def test_each_record_names_only_the_roles_it_used(project: Project) -> None:
    created = _created(project.sign("Pat"))

    assert created["roles"] == ["product-manager", "risk-manager"]
    assert [d["id"] for d in created["documents"]] == ["CRS", "RCM", "RISK", "UC"]


def test_the_quality_lead_signs_the_manifest_file_as_the_release(project: Project) -> None:
    created = _created(project.sign("Quinn"))

    manifest = project.dhf / "releases" / "1.0.0" / "manifest.yaml"
    assert created["roles"] == ["quality-lead"]
    assert created["documents"] == [{"id": "release", "hash": "sha256:" + hashlib.sha256(manifest.read_bytes()).hexdigest()}]


def test_the_release_fails_naming_each_missing_role_until_all_have_signed(project: Project) -> None:
    before = project.verify("--release", "1.0.0")
    assert before["passed"] is False
    errors = " ".join(before["errors"])
    assert "UC document" in errors and "product-manager: Pat" in errors
    assert "SYS document" in errors and "system-architect: Sam" in errors
    assert "RISK document" in errors and "risk-manager: Pat" in errors
    assert "SRS document" in errors and "software-lead: Lead" in errors
    assert "The release of 1.0.0" in errors and "quality-lead: Quinn" in errors

    project.sign("Lead")
    project.sign("Pat")
    partial = project.verify("--release", "1.0.0")
    assert partial["passed"] is False and "SYS document" in " ".join(partial["errors"])
    assert "SRS document" not in " ".join(partial["errors"])

    project.sign("Sam")
    project.sign("Quinn")
    after = project.verify("--release", "1.0.0")
    assert after["passed"] is True, after["errors"]
    assert after["summary"] == "release 1.0.0: 11 of 11 signature(s) in place"


def test_plain_verify_never_asks_for_a_signature(project: Project) -> None:
    answer = project.verify()

    assert answer["passed"] is True, answer["errors"]
    assert answer["summary"] == "0 valid approval record(s) in the log"


def test_editing_an_item_after_the_manifest_fails_with_a_drift_finding(project: Project) -> None:
    for who in ("Lead", "Pat", "Sam", "Quinn"):
        project.sign(who)
    assert project.verify("--release", "1.0.0")["passed"] is True

    project.edit("SWDD-001", content="Edited after the manifest.")

    answer = project.verify("--release", "1.0.0")
    assert answer["passed"] is False
    assert any("SWDD-001 (SWDD) was edited after the manifest" in e and "build release" in e for e in answer["errors"])


def test_an_item_added_or_removed_after_the_manifest_is_named(project: Project) -> None:
    project.item_file("SOUP-001").unlink()

    errors = " ".join(project.verify("--release", "1.0.0")["errors"])

    assert "SOUP-001 (SOUP) was removed after the manifest" in errors


def test_an_item_outside_every_document_still_breaks_the_dhf_hash(project: Project) -> None:
    project.edit("DEF-001", title="Edited after the manifest.")

    answer = project.verify("--release", "1.0.0")

    assert answer["passed"] is False
    assert any("in an item no document lists" in e for e in answer["errors"])


def test_a_signature_over_an_older_manifest_hash_does_not_count(project: Project) -> None:
    _created(project.sign("Lead"))
    project.edit("SRS-001", content="A late fix.")
    project.release("1.0.0", "--cr", "CR-001")

    errors = " ".join(project.verify("--release", "1.0.0")["errors"])
    assert "SRS document" in errors and "SWDD document" not in errors

    again = _created(project.sign("Lead"))
    assert [d["id"] for d in again["documents"]] == ["SRS"], "the documents that did not change stay signed"
    assert "SRS document" not in " ".join(project.verify("--release", "1.0.0")["errors"])


def test_signing_the_same_hashes_twice_records_nothing_the_second_time(project: Project) -> None:
    project.sign("Lead")

    result = project.sign("Lead")

    assert result.exit_code == 0
    assert "Nothing to sign" in json.loads(result.stdout)["summary"]
    assert len(project.records()) == 1


def test_a_signer_is_shown_the_changes_to_each_document_and_may_decline(project: Project) -> None:
    result = project.run("item", "approve", "--key", str(project.keys["Lead"]), "--release", "1.0.0", input="n\n")

    assert result.exit_code == 1
    assert "SRS" in result.stderr and "SRS-001 (CR-001)" in result.stderr and "Added (1)" in result.stderr
    assert not (project.dhf / "approvals").exists()


def test_a_signature_by_a_role_that_does_not_own_the_document_does_not_count(project: Project) -> None:
    project.forge("Pat", signer="Pat", roles=["product-manager"], documents=[project.pin("SRS")])

    answer = project.verify("--release", "1.0.0")

    assert any("SRS document" in e and "software-lead" in e for e in answer["errors"])


def test_a_role_the_signer_does_not_hold_does_not_count(project: Project) -> None:
    project.forge("Pat", signer="Pat", roles=["software-lead"], documents=[project.pin("SRS")])

    answer = project.verify("--release", "1.0.0")

    assert any("does not hold" in e for e in answer["errors"])
    assert any("SRS document" in e for e in answer["errors"])


def test_a_signature_for_another_release_does_not_count(project: Project) -> None:
    project.forge("Lead", signer="Lead", roles=["software-lead"], documents=[project.pin("SRS")], release="0.9.0")

    assert any("SRS document" in e for e in project.verify("--release", "1.0.0")["errors"])


def test_a_release_without_a_manifest_cannot_be_signed_or_verified(project: Project) -> None:
    signed = project.sign("Lead", "9.9.9")
    answer = project.verify("--release", "9.9.9")

    assert signed.exit_code == 1 and "no manifest" in signed.stderr
    assert answer["passed"] is False and "no manifest" in answer["errors"][0]


def test_a_malformed_manifest_is_named_not_crashed_on(project: Project) -> None:
    (project.dhf / "releases" / "1.0.0" / "manifest.yaml").write_text("documents: 3\n", encoding="utf-8")

    answer = project.verify("--release", "1.0.0")

    assert answer["passed"] is False and "is not a release manifest" in answer["errors"][0]


def test_an_approvers_list_edited_after_the_manifest_is_reported(project: Project) -> None:
    entries = yaml.safe_load(project.approvers_file.read_text())
    entries.append(entry("Mallory", project.keys["Mallory"], ["software-lead"]))
    project.write_approvers(entries)

    assert any("approvers list changed after the manifest" in e for e in project.verify("--release", "1.0.0")["errors"])


def test_a_release_cannot_be_verified_without_an_approvers_list(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)
    project.ready_to_release()
    project.release()

    answer = project.verify("--release", "1.0.0")

    assert answer["passed"] is False
    assert "Approvals are not configured" in answer["errors"][0]


def test_one_person_holding_every_role_signs_everything_in_one_record(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)
    project.write_approvers([entry("Solo", project.keys["Lead"], ["software-lead", "product-manager", "risk-manager",
                                                                    "system-architect", "quality-lead"])])
    project.ready_to_release()
    project.release()

    created = _created(project.sign("Lead"))

    assert len(project.records()) == 1 and created["signer"] == "Solo"
    assert [d["id"] for d in created["documents"]][-1] == "release"
    assert project.verify("--release", "1.0.0")["passed"] is True


def test_a_key_that_is_not_on_the_list_cannot_sign(project: Project) -> None:
    result = project.sign("Mallory")

    assert result.exit_code == 1 and "not on the approvers list" in result.stderr


def test_a_public_key_is_refused_so_ssh_agent_is_never_used(project: Project) -> None:
    pub = project.keys["Lead"].with_name("Lead.pub")

    result = project.run("item", "approve", "--key", str(pub), "--release", "1.0.0", "--yes")

    assert result.exit_code == 1 and "never ssh-agent" in result.stderr


def test_release_and_approvers_are_exclusive(project: Project) -> None:
    neither = project.approve("Lead")
    both = project.approve("Lead", "--release", "1.0.0", "--approvers")

    assert neither.exit_code == 2 and both.exit_code == 2
    assert "exactly one" in neither.output


def test_the_rel_moving_on_after_signing_is_not_drift(project: Project) -> None:
    """The REL is the record of the release, not its content: approving it after the signatures must not undo them."""
    for name in ("Lead", "Pat", "Sam", "Quinn"):
        project.sign(name)
    rels = sorted((project.dhf / "items").rglob("REL-*.yaml"))
    rel = rels[-1]
    data = yaml.safe_load(rel.read_text())
    data["status"] = "approved"
    rel.write_text(yaml.safe_dump(data))

    after = project.verify("--release", "1.0.0")
    assert after["passed"] is True, after["errors"]
