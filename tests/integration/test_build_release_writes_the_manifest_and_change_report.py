"""`build release --write` writes what the release's signatures cover and what changed since the last release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from fixtures.approvals import Project, build_project


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(pairs: list[tuple[str, str]]) -> str:
    return "sha256:" + hashlib.sha256("\n".join(f"{u}:{h}" for u, h in sorted(pairs)).encode()).hexdigest()


def _released(tmp_path: Path, *, with_approvers: bool = True) -> Project:
    project = build_project(tmp_path, with_approvers=with_approvers)
    project.ready_to_release()
    project.release()
    return project


@pytest.mark.dhf_links("SRS-049")
@pytest.mark.dhf_testing("T1")
def test_the_manifest_hashes_every_item_and_each_document(tmp_path: Path) -> None:
    project = _released(tmp_path)

    manifest = project.manifest()

    all_items = {p.stem: _sha(p) for p in (project.dhf / "items").rglob("*.yaml")}
    content = {uid: h for uid, h in all_items.items() if not uid.startswith("REL-")}
    assert manifest["version"] == "1.0.0"
    assert manifest["dhf_hash"] == _digest(list(content.items())), "every item but the release records"
    assert manifest["approvers_hash"] == _sha(project.approvers_file)
    srs = manifest["documents"]["SRS"]
    assert srs["items"] == [{"id": "SRS-001", "hash": all_items["SRS-001"]}]
    assert srs["hash"] == _digest([("SRS-001", all_items["SRS-001"])])
    rendered = project.root / "rel" / "1.0.0" / srs["file"]
    assert srs["file"] == "specifications/SRS_Specification_1.0.0.html" and rendered.is_file()
    assert srs["file_hash"] == _sha(rendered)
    assert {"UC", "CRS", "SYS", "SYSARCH", "SRS", "SWDD", "MODULE", "SOUP", "RISK", "RCM", "CR"} <= set(manifest["documents"])
    assert "REL" not in manifest["documents"]


@pytest.mark.dhf_links("SRS-049")
@pytest.mark.dhf_testing("T2")
def test_the_manifest_is_written_without_an_approvers_list_too(tmp_path: Path) -> None:
    project = _released(tmp_path, with_approvers=False)

    assert project.manifest()["approvers_hash"] is None
    assert (project.dhf / "releases" / "1.0.0" / "changes.md").is_file()


@pytest.mark.dhf_links("SRS-047")
@pytest.mark.dhf_testing("T1")
def test_the_release_is_recorded_as_a_draft_for_the_signatures_to_cover(tmp_path: Path) -> None:
    project = _released(tmp_path)

    report = json.loads(project.run("build", "release", "--version", "1.0.1", "--out-dir", str(project.root / "rel" / "1.0.1"),
                                    "--junit", str(project.junit), "--write").stdout.splitlines()[0])

    assert yaml.safe_load(project.item_file(report["rel_uid"]).read_text())["status"] == "draft"


@pytest.mark.dhf_links("SRS-048")
@pytest.mark.dhf_testing("T1")
def test_a_dry_run_and_a_failed_release_write_nothing_into_the_dhf(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.ready_to_release()
    dry = project.run("build", "release", "--version", "1.0.0", "--out-dir", str(project.root / "rel"), "--junit", str(project.junit))
    project.edit("CR-001", status="design")
    failed = project.run("build", "release", "--version", "1.0.0", "--cr", "CR-001", "--out-dir", str(project.root / "rel"),
                         "--junit", str(project.junit), "--write")

    assert dry.exit_code == 0 and failed.exit_code == 1
    assert not (project.dhf / "releases").exists()


@pytest.mark.dhf_links("SRS-047")
@pytest.mark.dhf_testing("T3")
def test_the_first_release_lists_every_item_as_added(tmp_path: Path) -> None:
    project = _released(tmp_path)

    changes = (project.dhf / "releases" / "1.0.0" / "changes.md").read_text()

    assert "first release, so every item is added" in changes
    assert "## SRS\n\nAdded (1)\n\n- SRS-001 (CR-001)\n" in changes
    assert "Modified" not in changes and "Removed" not in changes


@pytest.mark.dhf_links("SRS-047")
@pytest.mark.dhf_testing("T4")
def test_a_later_release_lists_only_what_changed_with_the_cr_that_lists_it(tmp_path: Path) -> None:
    project = _released(tmp_path)
    project.edit("SRS-001", content="Changed after the first release.")
    project.edit("SYS-001", content="Also changed, but no CR lists it.")
    project.release("1.1.0", "--cr", "CR-001")

    changes = (project.dhf / "releases" / "1.1.0" / "changes.md").read_text()

    assert "Compared with release 1.0.0." in changes
    assert "## SRS\n\nModified (1)\n\n- SRS-001 (CR-001)\n" in changes
    assert "## SYS\n\nModified (1)\n\n- SYS-001\n" in changes
    assert "## SWDD\n\nNo changes.\n" in changes
    assert "Added" not in changes.split("## SRS")[0] and "SRS-001 (CR-001)" not in changes.split("## SYS")[1]


@pytest.mark.dhf_links("SRS-047")
@pytest.mark.dhf_testing("T5")
def test_an_item_removed_between_releases_is_listed_as_removed(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.ready_to_release()
    extra = project.item_file("SOUP-001").with_name("SOUP-002.yaml")
    extra.write_text(project.item_file("SOUP-001").read_text().replace("SOUP-001", "SOUP-002"))
    project.release()
    extra.unlink()

    project.release("1.1.0", "--cr", "CR-001")

    changes = (project.dhf / "releases" / "1.1.0" / "changes.md").read_text()
    assert "## SOUP\n\nRemoved (1)\n\n- SOUP-002\n" in changes


def test_release_files_do_not_disturb_the_dhf_checks(tmp_path: Path) -> None:
    project = _released(tmp_path)

    def strict() -> dict:
        return json.loads(project.run("verify", "dhf", "--strict").stdout.splitlines()[0])

    with_files = strict()
    (project.dhf / "releases" / "1.0.0" / "manifest.yaml").rename(tmp_path / "moved.yaml")
    (project.dhf / "releases" / "1.0.0" / "changes.md").unlink()

    assert strict() == with_files
    assert "manifest" not in project.run("item", "list").stdout
