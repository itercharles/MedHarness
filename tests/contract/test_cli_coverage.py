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
    """Functional tests for ci dhf-validate."""

    def test_dhf_validate_passes(self, scaffolded_dhf):
        """ci dhf-validate passes on a clean scaffolded DHF."""
        r = _run(
            "medharness", "ci", "dhf-validate",
            "--dhf", str(scaffolded_dhf / "DHF"),
        )
        assert r.returncode == 0, r.stderr

    def test_dhf_validate_schema_only(self, scaffolded_dhf):
        """ci dhf-validate --no-run-traceability passes on a clean DHF."""
        r = _run(
            "medharness", "ci", "dhf-validate",
            "--dhf", str(scaffolded_dhf / "DHF"),
            "--no-run-traceability",
        )
        assert r.returncode == 0, r.stderr

    def test_dhf_validate_with_coverage_pairs(self, scaffolded_dhf):
        """ci dhf-validate with explicit coverage pairs."""
        r = _run(
            "medharness", "ci", "dhf-validate",
            "--dhf", str(scaffolded_dhf / "DHF"),
            "--coverage-pair", "UC:CRS",
        )
        assert r.returncode == 0, r.stderr


class TestCITestCoverage:
    """Functional tests for ci test-coverage."""

    def test_test_coverage_no_junit(self, scaffolded_dhf, tmp_path):
        """ci test-coverage fails when no JUnit files provided."""
        r = _run(
            "medharness", "ci", "test-coverage",
            "--dhf", str(scaffolded_dhf / "DHF"),
        )
        assert r.returncode != 0

    def test_test_coverage_with_junit(self, scaffolded_dhf, tmp_path):
        """ci test-coverage runs with JUnit evidence."""
        junit_file = tmp_path / "results.xml"
        junit_file.write_text(JUNIT_XML)
        r = _run(
            "medharness", "ci", "test-coverage",
            "--dhf", str(scaffolded_dhf / "DHF"),
            "--junit", str(junit_file),
        )
        assert r.returncode in (0, 1), r.stderr + r.stdout


class TestCIEvidence:
    """Functional tests for ci evidence import/bundle."""

    def test_evidence_import(self, scaffolded_dhf, tmp_path):
        """ci evidence import ingests a JUnit file (persist-first pattern)."""
        junit_file = tmp_path / "results.xml"
        junit_file.write_text(JUNIT_XML)
        dhf_root = scaffolded_dhf / "DHF"
        r = _run(
            "medharness", "--dhf", str(dhf_root),
            "ci", "evidence", "import",
            str(junit_file),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "imported" in data

    def test_evidence_bundle(self, scaffolded_dhf, tmp_path):
        """ci evidence bundle produces an out-dir (consume-at-bundle model)."""
        out_dir = tmp_path / "bundle"
        dhf_root = scaffolded_dhf / "DHF"
        r = _run(
            "medharness", "--dhf", str(dhf_root),
            "ci", "evidence", "bundle",
            "--out-dir", str(out_dir),
        )
        if r.returncode != 0 and ("cannot load library" in r.stderr or "weasyprint" in r.stderr.lower() or "no module" in r.stderr.lower()):
            return  # weasyprint not available on this system
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "gate_passed" in data
        assert (out_dir / "evidence-manifest.json").exists()


class TestCIArtifacts:
    """Functional tests for ci artifacts generate."""

    def test_artifacts_generate(self, scaffolded_dhf, tmp_path):
        """ci artifacts generate produces Markdown specs + JSON traceability report."""
        out_dir = tmp_path / "artifacts"
        dhf_root = scaffolded_dhf / "DHF"
        r = _run(
            "medharness", "--dhf", str(dhf_root),
            "ci", "artifacts", "generate",
            "--out-dir", str(out_dir),
            "--skip-plans",
        )
        if r.returncode != 0 and ("cannot load library" in r.stderr or "weasyprint" in r.stderr.lower() or "no module" in r.stderr.lower()):
            return
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "traceability" in data

    def test_artifacts_generate_with_junit_dir(self, scaffolded_dhf, tmp_path):
        """ci artifacts generate picks up JUnit from directories."""
        junit_dir = tmp_path / "junit"
        junit_dir.mkdir()
        (junit_dir / "results.xml").write_text(JUNIT_XML)
        out_dir = tmp_path / "artifacts2"
        dhf_root = scaffolded_dhf / "DHF"
        r = _run(
            "medharness", "--dhf", str(dhf_root),
            "ci", "artifacts", "generate",
            "--out-dir", str(out_dir),
            "--junit-dir", str(junit_dir),
            "--skip-plans",
        )
        if r.returncode != 0 and ("cannot load library" in r.stderr or "weasyprint" in r.stderr.lower() or "no module" in r.stderr.lower()):
            return
        assert r.returncode == 0, r.stderr
