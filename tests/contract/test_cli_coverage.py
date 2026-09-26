"""Contract tests: functional coverage for CI gate, evidence, and artifact commands."""
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run(*args: str) -> "subprocess.CompletedProcess":
    import subprocess
    return subprocess.run(
        [sys.executable, "-m", *args],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


JUNIT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="test_suite" tests="1" failures="0" errors="0" time="0.1">
    <testcase classname="test_example" name="test_case_1" time="0.01">
      <properties>
        <property name="medharness.links" value="SYS-001"/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>
"""


class TestCIDhfValidate:
    """Functional tests for verify dhf."""

    def test_dhf_validate_passes(self, scaffolded_dhf):
        """verify dhf passes on a clean scaffolded DHF."""
        r = _run(
            "medharness", "--dhf", str(scaffolded_dhf / "DHF"),
            "verify", "dhf",
        )
        assert r.returncode == 0, r.stderr

    def test_dhf_validate_with_coverage_pairs(self, scaffolded_dhf):
        """verify dhf with explicit coverage pairs."""
        r = _run(
            "medharness", "--dhf", str(scaffolded_dhf / "DHF"),
            "verify", "dhf",
            "--coverage-pair", "UC:CRS",
        )
        assert r.returncode == 0, r.stderr


class TestCITestCoverage:
    """Functional tests for verify tests."""

    def test_test_coverage_no_junit(self, scaffolded_dhf, tmp_path):
        """verify tests fails when no JUnit files provided."""
        r = _run(
            "medharness", "--dhf", str(scaffolded_dhf / "DHF"),
            "verify", "tests",
        )
        assert r.returncode != 0

    def test_test_coverage_with_junit(self, scaffolded_dhf, tmp_path):
        """verify tests runs with JUnit evidence."""
        junit_file = tmp_path / "results.xml"
        junit_file.write_text(JUNIT_XML)
        r = _run(
            "medharness", "--dhf", str(scaffolded_dhf / "DHF"),
            "verify", "tests",
            "--junit", str(junit_file),
        )
        assert r.returncode in (0, 1), r.stderr + r.stdout


class TestBuildRelease:
    """`build release` writes everything one release needs, in one directory."""

    def test_a_starter_dhf_builds_a_release(self, scaffolded_dhf, tmp_path):
        """HTML by default, so this needs no native renderer.

        The bundle it replaces ran a private gate that failed every starter DHF
        — CR, DEF, REL and SOUP items were "orphans" for not linking anywhere,
        which they are not meant to. Callers passed --continue-on-gate-failure
        on every run to get past it.
        """
        out_dir = tmp_path / "release"
        r = _run(
            "medharness", "--dhf", str(scaffolded_dhf / "DHF"),
            "build", "release", "--version", "1.0.0", "--out-dir", str(out_dir),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["outcome"] == "completed" and data["errors"] == []
        assert data["rel_uid"] is None, "a dry run recorded a REL item"

        for name in ("release-baseline.json", "software-bom.json", "sbom.cdx.json",
                     "evidence-manifest.json"):
            assert (out_dir / name).exists(), f"{name} was not written"
        specs = list((out_dir / "specifications").glob("*.html"))
        assert specs and "<!DOCTYPE html>" in specs[0].read_text()

        # The manifest is written last so that it covers the baseline too.
        manifest = json.loads((out_dir / "evidence-manifest.json").read_text())
        assert "release-baseline.json" in {f["path"] for f in manifest["files"]}

    def test_a_failing_release_exits_nonzero_and_says_why(self, scaffolded_dhf, tmp_path):
        dhf = scaffolded_dhf / "DHF"
        rcm = next((dhf / "items").rglob("RCM-*.yaml"))
        rcm.write_text(rcm.read_text().replace("RISK-001", "RISK-404"))
        out_dir = tmp_path / "release"

        r = _run(
            "medharness", "--dhf", str(dhf),
            "build", "release", "--version", "1.0.0", "--out-dir", str(out_dir), "--write",
        )
        assert r.returncode == 1
        assert "RISK-404" in r.stderr and "No REL item was recorded" in r.stderr
        # The evidence is still written, so the failure can be inspected.
        assert (out_dir / "evidence-manifest.json").exists()


