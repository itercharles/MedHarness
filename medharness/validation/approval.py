"""`verify approval`: a release is signed by the roles that own its documents, over their current hashes (SRS-016 to SRS-023).

Each case signs with throwaway SSH keys, so it needs `ssh-keygen` as well as git.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from medharness.validation.case import Case, check
from medharness.validation.project import git
from medharness.validation.signing import Project, build_project, entry, make_key, project_in

TOOLS = ("git", "ssh-keygen")
SIGNERS = ("Lead", "Pat", "Sam", "Quinn")


def released(root: Path) -> None:
    project = build_project(root)
    project.ready_to_release()
    project.release()


def released_without_approvers(root: Path) -> None:
    project = build_project(root, with_approvers=False)
    project.ready_to_release()
    project.release()


def signed_and_merged(root: Path) -> None:
    """Lead's signature committed and merged into `main`, and a new branch from there."""
    released(root)
    project = project_in(root)
    _sign(project, "Lead")
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "signed")
    git(project.root, "checkout", "-q", "main")
    git(project.root, "merge", "-q", "--ff-only", "feat")
    git(project.root, "checkout", "-q", "-b", "next")


def approvers_on_main(root: Path) -> None:
    build_project(root)


def no_approvers(root: Path) -> None:
    build_project(root, with_approvers=False)


def _sign(project: Project, who: str, version: str = "1.0.0") -> dict:
    result = project.sign(who, version)
    check(result.exit_code == 0, f"{who} could not sign {version}: {result.stderr[-400:]}")
    return json.loads(result.stdout)


def _release_errors(project: Project) -> str:
    return " ".join(project.verify("--release", "1.0.0")["errors"])


def _passes(answer: dict) -> None:
    check(answer["passed"] is True, f"refused: {answer['errors']}")


def _fails(answer: dict, *needles: str) -> None:
    check(answer["passed"] is False, "passed")
    for needle in needles:
        check(any(needle in e for e in answer["errors"]), f"no error says {needle!r}: {answer['errors']}")


# --- SRS-016: each document needs its owning role's signature over its current hash --------------

def each_missing_role_is_named(root: Path) -> None:
    project = project_in(root)
    errors = _release_errors(project)
    for document, role in (("UC document", "product-manager: Pat"), ("SYS document", "system-architect: Sam"),
                           ("RISK document", "risk-manager: Pat"), ("SRS document", "software-lead: Lead"),
                           ("The release of 1.0.0", "quality-lead: Quinn")):
        check(document in errors and role in errors, f"{document} is not named with {role}: {errors}")
    _sign(project, "Lead")
    _sign(project, "Pat")
    errors = _release_errors(project)
    check("SYS document" in errors and "SRS document" not in errors, f"after Lead and Pat signed: {errors}")


def role_that_does_not_own_the_document(root: Path) -> None:
    project = project_in(root)
    project.forge("Pat", signer="Pat", roles=["product-manager"], documents=[project.pin("SRS")])
    _fails(project.verify("--release", "1.0.0"), "SRS document")


def role_the_signer_does_not_hold(root: Path) -> None:
    project = project_in(root)
    project.forge("Pat", signer="Pat", roles=["software-lead"], documents=[project.pin("SRS")])
    _fails(project.verify("--release", "1.0.0"), "does not hold", "SRS document")


def signature_for_another_release(root: Path) -> None:
    project = project_in(root)
    project.forge("Lead", signer="Lead", roles=["software-lead"], documents=[project.pin("SRS")], release="0.9.0")
    _fails(project.verify("--release", "1.0.0"), "SRS document")


def signature_over_an_older_hash(root: Path) -> None:
    project = project_in(root)
    _sign(project, "Lead")
    project.edit("SRS-001", content="A late fix.")
    project.release("1.0.0", "--cr", "CR-001")
    errors = _release_errors(project)
    check("SRS document" in errors and "SWDD document" not in errors, f"after the manifest changed: {errors}")
    again = _sign(project, "Lead")
    check([d["id"] for d in again["documents"]] == ["SRS"], f"signed again: {again['documents']}")
    check("SRS document" not in _release_errors(project), "the new signature does not count")


# --- SRS-017: the release role signs the manifest ------------------------------------------------

def release_role_has_not_signed(root: Path) -> None:
    project = project_in(root)
    for who in ("Lead", "Pat", "Sam"):
        _sign(project, who)
    answer = project.verify("--release", "1.0.0")
    _fails(answer)
    check(len(answer["errors"]) == 1 and answer["errors"][0].startswith("The release of 1.0.0")
          and "quality-lead: Quinn" in answer["errors"][0], f"errors: {answer['errors']}")


def manifest_rebuilt_after_the_release_role_signed(root: Path) -> None:
    project = project_in(root)
    for who in SIGNERS:
        _sign(project, who)
    _passes(project.verify("--release", "1.0.0"))
    project.edit("SRS-001", content="A late fix.")
    project.release("1.0.0", "--cr", "CR-001")
    answer = project.verify("--release", "1.0.0")
    check(any(e.startswith("The release of 1.0.0") for e in answer["errors"]), f"errors: {answer['errors']}")


# --- SRS-018: what is absent or malformed --------------------------------------------------------

def release_without_a_manifest(root: Path) -> None:
    project = project_in(root)
    signed = project.sign("Lead", "9.9.9")
    answer = project.verify("--release", "9.9.9")
    check(signed.exit_code == 1 and "no manifest" in signed.stderr, f"signing exited {signed.exit_code}")
    check(answer["passed"] is False and "no manifest" in answer["errors"][0], f"errors: {answer['errors']}")


def malformed_manifest(root: Path) -> None:
    project = project_in(root)
    (project.dhf / "releases" / "1.0.0" / "manifest.yaml").write_text("documents: 3\n", encoding="utf-8")
    answer = project.verify("--release", "1.0.0")
    check(answer["passed"] is False and "is not a release manifest" in answer["errors"][0], f"errors: {answer['errors']}")


def release_without_an_approvers_list(root: Path) -> None:
    answer = project_in(root).verify("--release", "1.0.0")
    check(answer["passed"] is False and "Approvals are not configured" in answer["errors"][0], f"errors: {answer['errors']}")


# --- SRS-019: forged, unsigned or altered records ------------------------------------------------

def _srs_unsigned(answer: dict) -> bool:
    return any("SRS document" in e for e in answer["errors"])


def tampered_record(root: Path) -> None:
    project = project_in(root)
    record = project.records()[0]
    record.write_text(record.read_text(encoding="utf-8").replace("id: SRS", "id: SYS"), encoding="utf-8")
    answer = project.verify("--release", "1.0.0")
    _fails(answer, "signature does not verify")
    check(_srs_unsigned(answer), "the tampered record still counts")


def record_without_its_signature(root: Path) -> None:
    project = project_in(root)
    project.records()[0].with_suffix(".yaml.sig").unlink()
    answer = project.verify("--release", "1.0.0")
    _fails(answer, "no signature file")
    check(_srs_unsigned(answer), "the unsigned record still counts")


def record_naming_another_signer(root: Path) -> None:
    project = project_in(root)
    project.forge("Lead", signer="Pat", roles=["software-lead"], documents=[project.pin("SRS")])
    _fails(project.verify(), "its key belongs to Lead")


def record_id_differs_from_its_file(root: Path) -> None:
    project = project_in(root)
    project.forge("Lead", signer="Lead", roles=["software-lead"], documents=[project.pin("SRS")],
                  file_id="01JB3KQ7Z8X4M2N5P6R7S8T9VA")
    answer = project.verify("--release", "1.0.0")
    _fails(answer, "differs from its file name")
    check(_srs_unsigned(answer), "the misnamed record still counts")


# --- SRS-020: the log is append-only -------------------------------------------------------------

def committed_record_modified(root: Path) -> None:
    project = project_in(root)
    record = project.records()[0]
    record.write_text(record.read_text(encoding="utf-8").replace("I have reviewed", "I skimmed"), encoding="utf-8")
    _fails(project.verify(), f"{record.name} was modified", "append-only")


def committed_signature_modified(root: Path) -> None:
    project = project_in(root)
    sig = project.records()[0].with_suffix(".yaml.sig")
    sig.write_text(sig.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    _fails(project.verify(), f"{sig.name} was modified")


def committed_record_deleted(root: Path) -> None:
    project = project_in(root)
    record = project.records()[0]
    record.unlink()
    _fails(project.verify(), f"{record.name} was deleted")


# --- SRS-021: drift after the manifest -----------------------------------------------------------

def item_edited_after_the_manifest(root: Path) -> None:
    project = project_in(root)
    for who in SIGNERS:
        _sign(project, who)
    _passes(project.verify("--release", "1.0.0"))
    project.edit("SWDD-001", content="Edited after the manifest.")
    _fails(project.verify("--release", "1.0.0"), "SWDD-001 (SWDD) was edited after the manifest")


def item_removed_after_the_manifest(root: Path) -> None:
    project = project_in(root)
    project.item_file("SOUP-001").unlink()
    _fails(project.verify("--release", "1.0.0"), "SOUP-001 (SOUP) was removed after the manifest")


def item_outside_every_document(root: Path) -> None:
    project = project_in(root)
    project.edit("DEF-001", title="Edited after the manifest.")
    _fails(project.verify("--release", "1.0.0"), "in an item no document lists")


def approvers_list_edited_after_the_manifest(root: Path) -> None:
    project = project_in(root)
    entries = yaml.safe_load(project.approvers_file.read_text(encoding="utf-8"))
    entries.append(entry("Mallory", project.keys["Mallory"], ["software-lead"]))
    project.write_approvers(entries)
    _fails(project.verify("--release", "1.0.0"), "approvers list changed after the manifest")


# --- SRS-022: the approvers list guards itself ---------------------------------------------------

def _add_mallory(project: Project) -> None:
    entries = yaml.safe_load(project.approvers_file.read_text(encoding="utf-8"))
    entries.append(entry("Mallory", project.keys["Mallory"], ["software-lead", "ccb"]))
    project.write_approvers(entries)


def key_added_without_the_earlier_list(root: Path) -> None:
    project = project_in(root)
    _add_mallory(project)
    answer = project.verify()
    _fails(answer)
    check("approvers.yaml changed" in answer["errors"][0] and "Lead, Pat, Sam, Quinn" in answer["errors"][0],
          f"errors: {answer['errors']}")


def added_key_approves_its_own_addition(root: Path) -> None:
    project = project_in(root)
    _add_mallory(project)
    check(project.approve("Mallory", "--approvers").exit_code == 0, "Mallory could not sign the list")
    answer = project.verify()
    _fails(answer)
    check("approvers.yaml changed" in answer["errors"][0], f"errors: {answer['errors']}")


def list_edited_after_its_approval(root: Path) -> None:
    project = project_in(root)
    _add_mallory(project)
    check(project.approve("Lead", "--approvers").exit_code == 0, "Lead could not sign the list")
    entries = yaml.safe_load(project.approvers_file.read_text(encoding="utf-8"))
    entries[2]["roles"].append("quality-lead")
    project.write_approvers(entries)
    _fails(project.verify())


def unrelated_key_does_not_stand_in(root: Path) -> None:
    project = project_in(root)
    project.keys["Other"] = make_key(project.keys["Lead"].parent, "Other")
    entries = yaml.safe_load(project.approvers_file.read_text(encoding="utf-8"))
    entries.append(entry("Other", project.keys["Other"], ["ccb"]))
    project.write_approvers(entries)
    project.approve("Other", "--approvers")
    _fails(project.verify())


def deleting_the_list_does_not_switch_approvals_off(root: Path) -> None:
    project = project_in(root)
    project.approvers_file.unlink()
    answer = project.verify()
    _fails(answer)
    check("approvers.yaml" in answer["errors"][0], f"errors: {answer['errors']}")


# --- SRS-023: a fully signed release passes ------------------------------------------------------

def every_role_signed(root: Path) -> None:
    project = project_in(root)
    for who in SIGNERS:
        _sign(project, who)
    answer = project.verify("--release", "1.0.0")
    _passes(answer)
    check(answer["summary"] == "release 1.0.0: 11 of 11 signature(s) in place", f"summary: {answer['summary']!r}")


def one_person_holding_every_role(root: Path) -> None:
    project = project_in(root)
    project.write_approvers([entry("Solo", project.keys["Lead"], ["software-lead", "product-manager", "risk-manager",
                                                                  "system-architect", "quality-lead"])])
    project.release("1.0.0", "--cr", "CR-001")
    created = _sign(project, "Lead")
    check(len(project.records()) == 1 and created["signer"] == "Solo", f"records: {project.records()}")
    _passes(project.verify("--release", "1.0.0"))


def release_record_moving_on_is_not_drift(root: Path) -> None:
    project = project_in(root)
    for who in SIGNERS:
        _sign(project, who)
    rel = sorted((project.dhf / "items").rglob("REL-*.yaml"))[-1]
    data = yaml.safe_load(rel.read_text(encoding="utf-8"))
    data["status"] = "approved"
    rel.write_text(yaml.safe_dump(data), encoding="utf-8")
    _passes(project.verify("--release", "1.0.0"))


def malformed_list_is_named(root: Path) -> None:
    project = project_in(root)
    project.approvers_file.write_text("name: Lead\n", encoding="utf-8")
    answer = project.verify()
    _fails(answer)
    check("must be a list of approvers" in answer["errors"][0], f"errors: {answer['errors']}")


def first_list_is_the_root_of_trust(root: Path) -> None:
    project = project_in(root)
    project.write_approvers([entry("Lead", project.keys["Lead"], ["software-lead"])])
    answer = project.verify()
    _passes(answer)
    check(any("root of trust" in w for w in answer["warnings"]), f"warnings: {answer['warnings']}")


def change_approved_from_the_earlier_list(root: Path) -> None:
    project = project_in(root)
    _add_mallory(project)
    result = project.approve("Lead", "--approvers")
    check(result.exit_code == 0, f"Lead could not sign the list: {result.stderr[-400:]}")
    _passes(project.verify())


CASES = [
    Case("each_missing_role_is_named", "SRS-016", ("T1",), released, each_missing_role_is_named, TOOLS),
    Case("role_that_does_not_own_the_document", "SRS-016", ("T2",), released, role_that_does_not_own_the_document, TOOLS),
    Case("role_the_signer_does_not_hold", "SRS-016", ("T3",), released, role_the_signer_does_not_hold, TOOLS),
    Case("signature_for_another_release", "SRS-016", ("T4",), released, signature_for_another_release, TOOLS),
    Case("signature_over_an_older_hash", "SRS-016", ("T5",), released, signature_over_an_older_hash, TOOLS),
    Case("release_role_has_not_signed", "SRS-017", ("T1",), released, release_role_has_not_signed, TOOLS),
    Case("manifest_rebuilt_after_the_release_role_signed", "SRS-017", ("T2",), released,
         manifest_rebuilt_after_the_release_role_signed, TOOLS),
    Case("release_without_a_manifest", "SRS-018", ("T1",), released, release_without_a_manifest, TOOLS),
    Case("malformed_manifest", "SRS-018", ("T2",), released, malformed_manifest, TOOLS),
    Case("release_without_an_approvers_list", "SRS-018", ("T3",), released_without_approvers,
         release_without_an_approvers_list, TOOLS),
    Case("tampered_record", "SRS-019", ("T1",), signed_and_merged, tampered_record, TOOLS),
    Case("record_without_its_signature", "SRS-019", ("T2",), signed_and_merged, record_without_its_signature, TOOLS),
    Case("record_naming_another_signer", "SRS-019", ("T3",), signed_and_merged, record_naming_another_signer, TOOLS),
    Case("record_id_differs_from_its_file", "SRS-019", ("T4",), released, record_id_differs_from_its_file, TOOLS),
    Case("committed_record_modified", "SRS-020", ("T1",), signed_and_merged, committed_record_modified, TOOLS),
    Case("committed_signature_modified", "SRS-020", ("T2",), signed_and_merged, committed_signature_modified, TOOLS),
    Case("committed_record_deleted", "SRS-020", ("T3",), signed_and_merged, committed_record_deleted, TOOLS),
    Case("item_edited_after_the_manifest", "SRS-021", ("T1",), released, item_edited_after_the_manifest, TOOLS),
    Case("item_removed_after_the_manifest", "SRS-021", ("T2",), released, item_removed_after_the_manifest, TOOLS),
    Case("item_outside_every_document", "SRS-021", ("T3",), released, item_outside_every_document, TOOLS),
    Case("approvers_list_edited_after_the_manifest", "SRS-021", ("T4",), released,
         approvers_list_edited_after_the_manifest, TOOLS),
    Case("key_added_without_the_earlier_list", "SRS-022", ("T1",), approvers_on_main, key_added_without_the_earlier_list, TOOLS),
    Case("added_key_approves_its_own_addition", "SRS-022", ("T2",), approvers_on_main,
         added_key_approves_its_own_addition, TOOLS),
    Case("list_edited_after_its_approval", "SRS-022", ("T3",), approvers_on_main, list_edited_after_its_approval, TOOLS),
    Case("unrelated_key_does_not_stand_in", "SRS-022", ("T4",), approvers_on_main, unrelated_key_does_not_stand_in, TOOLS),
    Case("deleting_the_list_does_not_switch_approvals_off", "SRS-022", ("T5",), approvers_on_main,
         deleting_the_list_does_not_switch_approvals_off, TOOLS),
    Case("malformed_list_is_named", "SRS-022", ("T6",), approvers_on_main, malformed_list_is_named, TOOLS),
    Case("every_role_signed", "SRS-023", ("T1",), released, every_role_signed, TOOLS),
    Case("one_person_holding_every_role", "SRS-023", ("T2",), released_without_approvers, one_person_holding_every_role, TOOLS),
    Case("release_record_moving_on_is_not_drift", "SRS-023", ("T3",), released, release_record_moving_on_is_not_drift, TOOLS),
    Case("first_list_is_the_root_of_trust", "SRS-023", ("T4",), no_approvers, first_list_is_the_root_of_trust, TOOLS),
    Case("change_approved_from_the_earlier_list", "SRS-023", ("T5",), approvers_on_main,
         change_approved_from_the_earlier_list, TOOLS),
]
