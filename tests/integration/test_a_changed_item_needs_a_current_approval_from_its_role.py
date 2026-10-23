"""A changed item passes `verify approval` once the role its type names has signed its current content."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fixtures.approvals import Project, build_project


@pytest.fixture
def project(tmp_path: Path) -> Project:
    project = build_project(tmp_path)
    project.edit("SRS-001", content="Changed requirement.")
    return project


def test_a_changed_srs_without_approval_fails_naming_who_may_approve_it(project: Project) -> None:
    answer = project.verify()

    assert answer["passed"] is False
    assert answer["summary"] == "1 item(s) checked; 1 missing approval(s)"
    assert "SRS-001" in answer["errors"][0] and "software-lead" in answer["errors"][0]
    assert "Lead" in answer["errors"][0]


def test_an_unchanged_item_needs_no_approval_unless_asked_for_all(project: Project) -> None:
    assert "SYS-001" not in " ".join(project.verify()["errors"])
    assert "SYS-001" in " ".join(project.verify("--all")["errors"])


def test_the_software_lead_approving_makes_it_pass(project: Project) -> None:
    result = project.approve("Lead")

    assert result.exit_code == 0, result.stderr
    created = json.loads(result.stdout)
    record = Path(created["path"])
    assert created["id"] == record.stem and created["roles"] == ["software-lead"] and created["cr"] is None
    assert record.parent == project.dhf / "approvals" / "unscoped"
    assert created["items"] == [project.pin("SRS-001")]
    assert record.with_name(record.name + ".sig").is_file()
    assert project.verify()["passed"] is True


def test_editing_the_srs_afterwards_makes_the_approval_stale(project: Project) -> None:
    project.approve("Lead")
    project.edit("SRS-001", content="Changed again.")

    answer = project.verify()

    assert answer["passed"] is False
    assert "SRS-001" in answer["errors"][0]


def test_approving_the_same_content_twice_records_nothing_the_second_time(project: Project) -> None:
    project.approve("Lead")

    result = project.approve("Lead")

    assert result.exit_code == 0
    assert "Nothing pending" in json.loads(result.stdout)["summary"]
    assert len(project.records()) == 1


def test_an_approver_cannot_choose_a_role_they_do_not_hold(project: Project) -> None:
    result = project.approve("Pat", "--role", "software-lead")

    assert result.exit_code == 1
    assert "does not hold" in result.stderr
    assert project.verify()["passed"] is False


def test_an_approver_whose_role_is_not_the_types_has_nothing_to_approve(project: Project) -> None:
    result = project.approve("Pat")

    assert result.exit_code == 0
    assert "Nothing pending" in json.loads(result.stdout)["summary"]


def test_an_approval_signed_for_a_role_outside_the_signers_does_not_count(project: Project) -> None:
    project.forge("Pat", signer="Pat", roles=["software-lead"], items=[project.pin("SRS-001")])

    answer = project.verify()

    assert answer["passed"] is False
    assert any("does not hold" in e for e in answer["errors"])


def test_an_approval_by_a_role_that_is_not_the_types_does_not_cover_it(project: Project) -> None:
    project.forge("Pat", signer="Pat", roles=["product-manager"], items=[project.pin("SRS-001")])

    answer = project.verify()

    assert answer["passed"] is False
    assert "has no current approval" in answer["errors"][0]


def test_a_key_that_is_not_on_the_list_does_not_count(project: Project) -> None:
    project.forge("Mallory", signer="Lead", roles=["software-lead"], items=[project.pin("SRS-001")])

    answer = project.verify()

    assert answer["passed"] is False
    assert any("not on the approvers list" in e for e in answer["errors"])
    assert any("SRS-001" in e and "no current approval" in e for e in answer["errors"])


def test_a_key_that_is_not_on_the_list_cannot_approve(project: Project) -> None:
    result = project.approve("Mallory")

    assert result.exit_code == 1
    assert "not on the approvers list" in result.stderr


def test_a_public_key_is_refused_so_ssh_agent_is_never_used(project: Project) -> None:
    pub = project.keys["Lead"].with_name("Lead.pub")

    result = project.run("item", "approve", "--key", str(pub), "--since-ref", "main", "--yes")

    assert result.exit_code == 1
    assert "never ssh-agent" in result.stderr


def test_one_statement_covers_items_for_two_roles_held_by_one_person(project: Project) -> None:
    project.edit("CR-001", title="A changed CR.")

    result = project.approve("Lead")

    created = json.loads(result.stdout)
    assert created["roles"] == ["ccb", "software-lead"]
    assert {e["id"] for e in created["items"]} == {"SRS-001", "CR-001"}
    assert next(e for e in created["items"] if e["id"] == "CR-001")["meaning"] == "new"
    assert project.verify()["passed"] is True


def test_cr_narrows_approval_to_the_items_it_lists_and_itself(project: Project) -> None:
    project.edit("SYS-001", content="Also changed.")
    project.edit("CR-001", affected_items=["SYS-001"])

    created = json.loads(project.approve("Lead", "--cr", "CR-001").stdout)

    assert [e["id"] for e in created["items"]] == ["CR-001"]
    assert created["cr"] == "CR-001"
    assert Path(created["path"]).parent == project.dhf / "approvals" / "CR-001"
    assert project.verify()["passed"] is False, "SYS-001 is listed by the CR but needs the system architect"


def test_all_approves_items_that_were_never_approved(project: Project) -> None:
    before = project.verify("--all")
    assert before["passed"] is False and "SRS-001" in " ".join(before["errors"])

    created = json.loads(project.approve("Lead", "--all").stdout)

    assert {"SRS-001", "SWDD-001", "MODULE-001", "SOUP-001", "CR-001"} <= {e["id"] for e in created["items"]}
    after = project.verify("--all")
    assert "SRS-001" not in " ".join(after["errors"])
    assert "no current approval" in " ".join(after["errors"]), "product-manager and others still owe theirs"


def test_declining_the_confirmation_records_nothing(project: Project) -> None:
    result = project.run("item", "approve", "--key", str(project.keys["Lead"]), "--since-ref", "main", input="n\n")

    assert result.exit_code == 1
    assert "SRS-001" in result.stderr
    assert not (project.dhf / "approvals").exists()
