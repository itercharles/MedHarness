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
            "medharness", "verify", "dhf",
            "--dhf", str(scaffolded_dhf / "DHF"),
        )
        assert r.returncode == 0, r.stderr

    def test_dhf_validate_schema_only(self, scaffolded_dhf):
        """verify dhf --no-run-traceability passes on a clean DHF."""
        r = _run(
            "medharness", "verify", "dhf",
            "--dhf", str(scaffolded_dhf / "DHF"),
            "--no-run-traceability",
        )
        assert r.returncode == 0, r.stderr

    def test_dhf_validate_with_coverage_pairs(self, scaffolded_dhf):
        """verify dhf with explicit coverage pairs."""
        r = _run(
            "medharness", "verify", "dhf",
            "--dhf", str(scaffolded_dhf / "DHF"),
            "--coverage-pair", "UC:CRS",
        )
        assert r.returncode == 0, r.stderr


class TestCITestCoverage:
    """Functional tests for verify tests."""

    def test_test_coverage_no_junit(self, scaffolded_dhf, tmp_path):
        """verify tests fails when no JUnit files provided."""
        r = _run(
            "medharness", "verify", "tests",
            "--dhf", str(scaffolded_dhf / "DHF"),
        )
        assert r.returncode != 0

    def test_test_coverage_with_junit(self, scaffolded_dhf, tmp_path):
        """verify tests runs with JUnit evidence."""
        junit_file = tmp_path / "results.xml"
        junit_file.write_text(JUNIT_XML)
        r = _run(
            "medharness", "verify", "tests",
            "--dhf", str(scaffolded_dhf / "DHF"),
            "--junit", str(junit_file),
        )
        assert r.returncode in (0, 1), r.stderr + r.stdout


class TestCIEvidence:
    """Functional tests for evidence bundle."""

    def test_evidence_bundle(self, scaffolded_dhf, tmp_path):
        """evidence bundle produces an out-dir (consume-at-bundle model).

        The bundle defaults to HTML precisely so this needs no native renderer.
        This test previously bailed out whenever weasyprint was missing, which
        meant it asserted nothing at all on CI — and hid the fact that the
        bundle could not be built on a base install.

        --continue-on-gate-failure because a starter DHF has no JUnit evidence,
        so the acceptance gate correctly fails; the artifacts are what is under
        test here, not the gate verdict.
        """
        out_dir = tmp_path / "bundle"
        dhf_root = scaffolded_dhf / "DHF"
        r = _run(
            "medharness", "--dhf", str(dhf_root),
            "evidence", "bundle",
            "--out-dir", str(out_dir),
            "--continue-on-gate-failure",
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "gate_passed" in data
        assert (out_dir / "evidence-manifest.json").exists()

        specs = list((out_dir / "specifications").glob("*.html"))
        assert specs, "no specifications rendered into the bundle"
        assert "<!DOCTYPE html>" in specs[0].read_text()

    def test_evidence_bundle_gate_failure_exits_nonzero(self, scaffolded_dhf, tmp_path):
        """Without --continue-on-gate-failure a failing gate must block."""
        r = _run(
            "medharness", "--dhf", str(scaffolded_dhf / "DHF"),
            "evidence", "bundle",
            "--out-dir", str(tmp_path / "bundle"),
        )
        assert r.returncode != 0
        assert "acceptance gate failed" in r.stderr.lower()


