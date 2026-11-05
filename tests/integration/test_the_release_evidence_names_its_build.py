"""The evidence bundle of a release says what it was built from, and an auditor can trust its headline.

A mock audit of a real project's bundle found: the manifest hashed everything but the test results, the baseline
named neither the commit nor the tool, and every traceability chain read `not_verified` because design items were
expected to carry tests.
"""

from __future__ import annotations

import hashlib
import json
from importlib import metadata
from pathlib import Path

import pytest

from medharness.validation import release as release_cases
from medharness.validation.case import invoke
from medharness.validation.project import git


@pytest.fixture
def project(tmp_path: Path) -> Path:
    release_cases.releasable(tmp_path)
    return tmp_path


def _release(root: Path) -> Path:
    code, report, _ = invoke(root, "build", "release", "--version", "1.0.0", "--out-dir", str(root / "out"),
                             "--junit", str(root / "results" / "junit.xml"))
    assert code == 0, report.get("errors")
    return root / "out"


@pytest.mark.dhf_links("SRS-048")
@pytest.mark.dhf_testing("T3")
def test_the_manifest_hashes_the_test_results_the_release_was_given(project: Path) -> None:
    out = _release(project)

    manifest = json.loads((out / "evidence-manifest.json").read_text())
    hashes = {f["path"]: f["sha256"] for f in manifest["files"]}
    given = (project / "results" / "junit.xml").read_bytes()
    assert hashes["test-results/junit.xml"] == hashlib.sha256(given).hexdigest()
    assert (out / "test-results" / "junit.xml").read_bytes() == given
    summary = json.loads((out / "evidence-summary.json").read_text())
    assert summary["artifacts"]["junit_files"] == ["test-results/junit.xml"]


def test_a_directory_of_test_results_is_copied_whole_and_two_with_one_name_do_not_overwrite(project: Path) -> None:
    for name in ("srs", "sys"):
        (project / "more" / name).mkdir(parents=True)
        (project / "more" / name / "junit.xml").write_text((project / "results" / "junit.xml").read_text() + f"<!--{name}-->")
    code, report, _ = invoke(project, "build", "release", "--version", "1.0.0", "--out-dir", str(project / "out"),
                             "--junit", str(project / "results" / "junit.xml"),
                             "--junit", str(project / "more" / "srs"), "--junit", str(project / "more" / "sys"))
    assert code == 0, report.get("errors")

    summary = json.loads((project / "out" / "evidence-summary.json").read_text())
    names = summary["artifacts"]["junit_files"]
    assert len(names) == 3 and len(set(names)) == 3
    assert all((project / "out" / n).is_file() for n in names)


@pytest.mark.dhf_links("SRS-048")
@pytest.mark.dhf_testing("T4")
def test_the_baseline_names_the_commit_and_the_tool_and_the_sbom_subject_the_release(project: Path) -> None:
    git(project, "init", "-q", "-b", "main")
    git(project, "config", "user.email", "t@example.com")
    git(project, "config", "user.name", "t")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "base")
    import subprocess
    head = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

    out = _release(project)

    baseline = json.loads((out / "release-baseline.json").read_text())
    assert baseline["commit_sha"] == head
    assert baseline["medharness_version"] == metadata.version("medharness")
    assert json.loads((out / "sbom.cdx.json").read_text())["metadata"]["component"]["version"] == "1.0.0"


def test_a_chain_whose_requirements_are_verified_reads_verified_though_design_items_have_no_tests(project: Path) -> None:
    out = _release(project)

    report = json.loads((out / "traceability" / "Requirements_Traceability_Report.json").read_text())

    assert report["rows"], "no chain in the report"
    for row in report["rows"]:
        assert "SWDD" not in row["level_statuses"], "design items are not verified by tests"
        assert row["verification_status"] == "verified", row
