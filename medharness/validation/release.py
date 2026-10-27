"""`build release`: a release ships only what the gates still pass, and records what it shipped (SRS-043 to SRS-050)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from medharness.validation.case import Case, check, invoke
from medharness.validation.project import edit, item_path, junit, scaffolded, starter, verify_the_starter

CLOSED = {"status": "completed", "implementation_notes": "Scale the dose by the calibration factor.",
          "affected_risk_items": [], "affected_items": ["SRS-001"]}


def releasable(root: Path) -> None:
    """The starter with CR-001 properly closed over SRS-001, and a JUnit that verifies every requirement."""
    starter(root, "Release")
    edit(root, "CR-001", **CLOSED)


def placeholder_starter(root: Path) -> None:
    scaffolded(root, "Release")
    verify_the_starter(root / "DHF", root / "results")
    edit(root, "CR-001", **CLOSED)


def _release(root: Path, *args: str, version: str = "1.0.0", results: Path | None = None) -> tuple[int, dict, str]:
    return invoke(root, "build", "release", "--version", version, "--out-dir", str(root / "out" / version),
                  "--junit", str(results or root / "results" / "junit.xml"), *args)


def _refused(root: Path, *needles: str, args: tuple[str, ...] = (), results: Path | None = None) -> dict:
    code, report, _ = _release(root, *args, results=results)
    check(code == 1 and report["outcome"] == "completed_with_errors" and report["rel_uid"] is None,
          f"exited {code}, outcome {report.get('outcome')}, rel_uid {report.get('rel_uid')}: {report.get('errors')}")
    for needle in needles:
        check(any(needle in e for e in report["errors"]), f"no error says {needle!r}: {report['errors']}")
    return report


def _released(root: Path, *args: str, version: str = "1.0.0") -> dict:
    code, report, _ = _release(root, *args, version=version)
    check(code == 0 and report["outcome"] == "completed", f"exited {code}: {report.get('errors')}")
    return report


def _rels(root: Path) -> list[str]:
    return sorted(p.stem for p in (root / "DHF" / "items").rglob("REL-*.yaml"))


def _nothing_recorded(root: Path) -> None:
    check(_rels(root) == ["REL-001"], f"a REL was recorded for a failed release: {_rels(root)}")
    check(not (root / "DHF" / "releases").exists(), "DHF/releases was written for a failed release")


# --- SRS-043: the DHF must pass verify dhf --strict ----------------------------------------------

def dangling_link_blocks_the_release(root: Path) -> None:
    edit(root, "RCM-001", mitigates=["RISK-404"])
    _refused(root, "DHF:", "RISK-404", args=("--write",))
    _nothing_recorded(root)


def placeholder_starter_cannot_be_released(root: Path) -> None:
    _refused(root, "DHF:", "placeholder")


def coverage_gap_blocks_the_release(root: Path) -> None:
    item_path(root, "SWDD-001").unlink()
    _refused(root, "SRS->SWDD: 1 uncovered", args=("--write",))
    _nothing_recorded(root)


# --- SRS-044: every included CR must be completed and still close --------------------------------

def unfinished_cr_blocks_the_release(root: Path) -> None:
    for state in ("design", "develop", "cancelled", "rejected"):
        edit(root, "CR-001", status=state)
        _refused(root, f"CR-001: CR is in state '{state}'", args=("--cr", "CR-001"))


def missing_cr_blocks_the_release(root: Path) -> None:
    _refused(root, "CR-404: CR not found", args=("--cr", "CR-404"))


def cr_completed_by_hand_blocks_the_release(root: Path) -> None:
    edit(root, "CR-001", status="completed", implementation_notes=None, affected_risk_items=None)
    report = _refused(root, args=("--write",))
    check(any(e.startswith("CR-001:") and "implementation_notes" in e for e in report["errors"]),
          f"the closure findings are not reported: {report['errors']}")
    _nothing_recorded(root)
    edit(root, "CR-001", **CLOSED)
    check(_released(root)["cr_ids"] == ["CR-001"], "a properly closed CR is not released")


def _cr(root: Path, uid: str, **fields) -> None:
    source = item_path(root, "CR-001")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    data.update({"id": uid, "title": uid, **fields})
    (source.parent / f"{uid}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def default_crs_are_the_unreleased_completed_ones(root: Path) -> None:
    _cr(root, "CR-003")
    _cr(root, "CR-002")
    _cr(root, "CR-004", status="develop")
    edit(root, "REL-001", included_items=["CR-002"])
    cr_ids = _released(root)["cr_ids"]
    check(cr_ids == ["CR-001", "CR-003"], f"included {cr_ids}, not the completed CRs no REL lists, sorted")


# --- SRS-045: open defects need a rationale ------------------------------------------------------

def unassessed_defect_blocks_the_release(root: Path) -> None:
    edit(root, "DEF-001", status="open")
    _refused(root, "DEF-001 is unresolved (state 'open') and has no release_rationale", args=("--write",))
    _nothing_recorded(root)


def one_unassessed_among_several(root: Path) -> None:
    edit(root, "DEF-001", status="open", release_rationale="Cosmetic.")
    for uid in ("DEF-002", "DEF-003"):
        source = item_path(root, "DEF-001")
        (source.parent / f"{uid}.yaml").write_text(source.read_text(encoding="utf-8").replace("DEF-001", uid), encoding="utf-8")
    edit(root, "DEF-003", release_rationale=None)
    report = _refused(root, "DEF-003 is unresolved")
    check(not any(e.startswith(("DEF-001", "DEF-002")) for e in report["errors"]), f"assessed defects blamed: {report['errors']}")


def which_states_are_anomalies(root: Path) -> None:
    for state in ("resolved", "closed", "cancelled"):
        edit(root, "DEF-001", status=state)
        _released(root)
    for state in ("draft", "open", "in_progress", None):
        edit(root, "DEF-001", status=state)
        _refused(root, "DEF-001 is unresolved")


def assessed_defect_is_carried_as_an_anomaly(root: Path) -> None:
    edit(root, "DEF-001", status="open", release_rationale="Cosmetic; no effect on the dose.")
    report = _released(root, "--write")
    baseline = json.loads((root / "out" / "1.0.0" / "release-baseline.json").read_text(encoding="utf-8"))
    rel = yaml.safe_load(item_path(root, report["rel_uid"]).read_text(encoding="utf-8"))
    for where, anomalies in (("baseline", baseline["known_anomalies"]), ("REL item", rel["known_anomalies"])):
        check([(a["defect"], a["rationale"]) for a in anomalies] == [("DEF-001", "Cosmetic; no effect on the dose.")],
              f"the {where} carries {anomalies}")


# --- SRS-046: the JUnit must verify every requirement --------------------------------------------

def unverified_requirement_blocks_the_release(root: Path) -> None:
    partial = junit(root / "results" / "partial.xml", ("test_others", "CRS-001,SYS-001", "passed"))
    report = _refused(root, results=partial)
    check(any(e.startswith("Tests:") and "SRS" in e for e in report["errors"]), f"no Tests: finding: {report['errors']}")


def verified_requirements_release(root: Path) -> None:
    _released(root)


def junit_is_required(root: Path) -> None:
    code, _, stderr = invoke(root, "build", "release", "--version", "1.0.0", "--out-dir", str(root / "out"))
    check(code == 2 and "--junit" in stderr, f"exited {code}; stderr: {stderr[-300:]!r}")


# --- SRS-047: --write records the release only when it passed ------------------------------------

def written_release_is_a_draft_with_its_records(root: Path) -> None:
    report = _released(root, "--write")
    rel = yaml.safe_load(item_path(root, report["rel_uid"]).read_text(encoding="utf-8"))
    check(rel["status"] == "draft", f"the REL is {rel['status']!r}, not draft")
    for name in ("manifest.yaml", "changes.md"):
        check((root / "DHF" / "releases" / "1.0.0" / name).is_file(), f"{name} was not written")


def _snapshot(directory: Path) -> dict[str, bytes]:
    return {str(p.relative_to(directory)): p.read_bytes() for p in sorted(directory.rglob("*")) if p.is_file()}


def dry_run_leaves_the_dhf_alone(root: Path) -> None:
    before = _snapshot(root / "DHF")
    _released(root)
    check(_snapshot(root / "DHF") == before, "a dry run changed the DHF")
    check((root / "out" / "1.0.0" / "release-baseline.json").is_file(), "the dry run wrote nothing to --out-dir")


def _changes(root: Path, version: str) -> str:
    return (root / "DHF" / "releases" / version / "changes.md").read_text(encoding="utf-8")


def first_release_adds_everything(root: Path) -> None:
    _released(root, "--write")
    changes = _changes(root, "1.0.0")
    check("first release, so every item is added" in changes and "## SRS\n\nAdded (1)\n\n- SRS-001 (CR-001)\n" in changes,
          f"changes.md:\n{changes[:600]}")
    check("Modified" not in changes and "Removed" not in changes, "the first release lists modified or removed items")


def later_release_lists_what_changed(root: Path) -> None:
    _released(root, "--write")
    edit(root, "SRS-001", content="Changed after the first release.")
    edit(root, "SYS-001", content="Also changed, but no CR lists it.")
    _released(root, "--write", "--cr", "CR-001", version="1.1.0")
    changes = _changes(root, "1.1.0")
    for expected in ("Compared with release 1.0.0.", "## SRS\n\nModified (1)\n\n- SRS-001 (CR-001)\n",
                     "## SYS\n\nModified (1)\n\n- SYS-001\n", "## SWDD\n\nNo changes.\n"):
        check(expected in changes, f"changes.md lacks {expected!r}:\n{changes[:800]}")


def removed_item_is_listed(root: Path) -> None:
    source = item_path(root, "SOUP-001")
    extra = source.with_name("SOUP-002.yaml")
    extra.write_text(source.read_text(encoding="utf-8").replace("SOUP-001", "SOUP-002"), encoding="utf-8")
    _released(root, "--write")
    extra.unlink()
    _released(root, "--write", "--cr", "CR-001", version="1.1.0")
    check("## SOUP\n\nRemoved (1)\n\n- SOUP-002\n" in _changes(root, "1.1.0"), "SOUP-002 is not listed as removed")


# --- SRS-048: a failing release writes evidence, not records -------------------------------------

def failing_release_records_nothing(root: Path) -> None:
    edit(root, "CR-001", status="design")
    _refused(root, args=("--cr", "CR-001", "--write"))
    _nothing_recorded(root)


def failing_release_writes_its_evidence(root: Path) -> None:
    edit(root, "CR-001", status="design")
    report = _refused(root, args=("--cr", "CR-001", "--write"))
    check((root / "out" / "1.0.0" / "evidence-manifest.json").is_file(), "evidence-manifest.json is missing")
    check(any(a.startswith("specifications/SRS_Specification_") for a in report["artifacts"]),
          f"no specification in {report['artifacts']}")


# --- SRS-049: the manifest leaves the release records out ----------------------------------------

def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(pairs) -> str:
    return "sha256:" + hashlib.sha256("\n".join(f"{u}:{h}" for u, h in sorted(pairs)).encode()).hexdigest()


def manifest_hashes_everything_but_releases(root: Path) -> None:
    _released(root, "--write")
    manifest = yaml.safe_load((root / "DHF" / "releases" / "1.0.0" / "manifest.yaml").read_text(encoding="utf-8"))
    items = {p.stem: _sha(p) for p in (root / "DHF" / "items").rglob("*.yaml")}
    content = [(uid, h) for uid, h in items.items() if not uid.startswith("REL-")]
    check(manifest["dhf_hash"] == _digest(content), "dhf_hash is not the digest of every item but the REL items")
    srs = manifest["documents"]["SRS"]
    check(srs["items"] == [{"id": "SRS-001", "hash": items["SRS-001"]}] and srs["hash"] == _digest([("SRS-001", items["SRS-001"])]),
          f"the SRS document is hashed wrongly: {srs}")
    check("REL" not in manifest["documents"], "REL is among the documents")


def manifest_without_approvers(root: Path) -> None:
    _released(root, "--write")
    manifest = yaml.safe_load((root / "DHF" / "releases" / "1.0.0" / "manifest.yaml").read_text(encoding="utf-8"))
    check(manifest["approvers_hash"] is None, f"approvers_hash is {manifest['approvers_hash']!r} without an approvers list")


# --- SRS-050: the software BOM -------------------------------------------------------------------

def unreadable_manifest_is_named(root: Path) -> None:
    (root / "deps.lock").write_text("not a manifest\n", encoding="utf-8")
    _refused(root, f"Unsupported manifest format for BOM: {root / 'deps.lock'}", args=("--manifest", str(root / "deps.lock")))


def malformed_package_json_is_a_parse_failure(root: Path) -> None:
    (root / "package.json").write_text("{not json", encoding="utf-8")
    report = _refused(root, f"Failed to parse BOM manifest {root / 'package.json'}", args=("--manifest", str(root / "package.json")))
    check(not any("Unsupported" in e for e in report["errors"]), f"reported as unsupported: {report['errors']}")


def bom_lists_soup_and_packages(root: Path) -> None:
    (root / "package.json").write_text(json.dumps({"name": "app", "version": "1.0.0", "dependencies": {"left-pad": "1.3.0"}}),
                                       encoding="utf-8")
    _released(root, "--manifest", str(root / "package.json"))
    bom = json.loads((root / "out" / "1.0.0" / "software-bom.json").read_text(encoding="utf-8"))
    check([s["uid"] for s in bom["dhf_soup"]] == ["SOUP-001"], f"dhf_soup: {bom['dhf_soup']}")
    check([(p["name"], p["version"]) for p in bom["manifest_packages"]] == [("left-pad", "1.3.0")],
          f"manifest_packages: {bom['manifest_packages']}")


CASES = [
    Case("dangling_link_blocks_the_release", "SRS-043", ("T1",), releasable, dangling_link_blocks_the_release, tools=()),
    Case("placeholder_starter_cannot_be_released", "SRS-043", ("T2",), placeholder_starter,
         placeholder_starter_cannot_be_released, tools=()),
    Case("coverage_gap_blocks_the_release", "SRS-043", ("T3",), releasable, coverage_gap_blocks_the_release, tools=()),
    Case("unfinished_cr_blocks_the_release", "SRS-044", ("T1",), releasable, unfinished_cr_blocks_the_release, tools=()),
    Case("missing_cr_blocks_the_release", "SRS-044", ("T2",), releasable, missing_cr_blocks_the_release, tools=()),
    Case("cr_completed_by_hand_blocks_the_release", "SRS-044", ("T3",), releasable,
         cr_completed_by_hand_blocks_the_release, tools=()),
    Case("default_crs_are_the_unreleased_completed_ones", "SRS-044", ("T4",), releasable,
         default_crs_are_the_unreleased_completed_ones, tools=()),
    Case("unassessed_defect_blocks_the_release", "SRS-045", ("T1",), releasable, unassessed_defect_blocks_the_release, tools=()),
    Case("one_unassessed_among_several", "SRS-045", ("T2",), releasable, one_unassessed_among_several, tools=()),
    Case("which_states_are_anomalies", "SRS-045", ("T3",), releasable, which_states_are_anomalies, tools=()),
    Case("assessed_defect_is_carried_as_an_anomaly", "SRS-045", ("T4",), releasable,
         assessed_defect_is_carried_as_an_anomaly, tools=()),
    Case("unverified_requirement_blocks_the_release", "SRS-046", ("T1",), releasable,
         unverified_requirement_blocks_the_release, tools=()),
    Case("verified_requirements_release", "SRS-046", ("T2",), releasable, verified_requirements_release, tools=()),
    Case("junit_is_required", "SRS-046", ("T3",), releasable, junit_is_required, tools=()),
    Case("written_release_is_a_draft_with_its_records", "SRS-047", ("T1",), releasable,
         written_release_is_a_draft_with_its_records, tools=()),
    Case("dry_run_leaves_the_dhf_alone", "SRS-047", ("T2",), releasable, dry_run_leaves_the_dhf_alone, tools=()),
    Case("first_release_adds_everything", "SRS-047", ("T3",), releasable, first_release_adds_everything, tools=()),
    Case("later_release_lists_what_changed", "SRS-047", ("T4",), releasable, later_release_lists_what_changed, tools=()),
    Case("removed_item_is_listed", "SRS-047", ("T5",), releasable, removed_item_is_listed, tools=()),
    Case("failing_release_records_nothing", "SRS-048", ("T1",), releasable, failing_release_records_nothing, tools=()),
    Case("failing_release_writes_its_evidence", "SRS-048", ("T2",), releasable, failing_release_writes_its_evidence, tools=()),
    Case("manifest_hashes_everything_but_releases", "SRS-049", ("T1",), releasable,
         manifest_hashes_everything_but_releases, tools=()),
    Case("manifest_without_approvers", "SRS-049", ("T2",), releasable, manifest_without_approvers, tools=()),
    Case("unreadable_manifest_is_named", "SRS-050", ("T1",), releasable, unreadable_manifest_is_named, tools=()),
    Case("malformed_package_json_is_a_parse_failure", "SRS-050", ("T2",), releasable,
         malformed_package_json_is_a_parse_failure, tools=()),
    Case("bom_lists_soup_and_packages", "SRS-050", ("T3",), releasable, bom_lists_soup_and_packages, tools=()),
]
