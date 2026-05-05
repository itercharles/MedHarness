"""Integration tests against scaffolded starter DHF: validates core workflows.

Scaffolds a temp DHF from templates, then runs schema validation, item ops,
doc generation, template rendering, and ci test-coverage against it.

"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

from medharness.workflows.init import _scaffold_dhf, _replace_placeholders


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def dhf():
    """Scaffold a fresh DHF from templates for each test."""
    with tempfile.TemporaryDirectory() as tmp:
        dhf_dir = Path(tmp) / "starter-dhf"
        _scaffold_dhf(dhf_dir)
        _replace_placeholders(dhf_dir, "Test Project")
        yield dhf_dir


def _dhf(dhf_root: str, *args: str) -> "subprocess.CompletedProcess":
    import subprocess
    return subprocess.run(
        [sys.executable, "-m", "medharness", "--dhf", dhf_root, "dhf"] + list(args),
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


def _cf(dhf_root: str, *args: str) -> "subprocess.CompletedProcess":
    import subprocess
    return subprocess.run(
        [sys.executable, "-m", "medharness", "--dhf", dhf_root, *args],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


DHF_DIRS = str  # will be set to scaffolded DHF/DHF path


class TestSchemaValidation:
    """Schema validation against the scaffolded starter DHF."""

    def test_validate_schema_passes(self, dhf):
        dhf_root = str(dhf / "DHF")
        r = _dhf(dhf_root, "validate", "schema")
        assert r.returncode == 0, f"Schema validation failed:\n{r.stderr}"

    def test_validate_traceability_runs(self, dhf):
        dhf_root = str(dhf / "DHF")
        r = _dhf(dhf_root, "validate", "traceability")
        assert r.returncode in (0, 1)


class TestItemOperations:
    """Item operations against the scaffolded starter DHF."""

    def test_all_12_types_have_items(self, dhf):
        dhf_root = str(dhf / "DHF")
        expected = ["UC", "CRS", "SYS", "SRS", "SWDD", "SYSARCH", "RISK", "RCM", "CR", "REL", "DEF", "SOUP"]
        for code in expected:
            r = _dhf(dhf_root, "item", "list", "--type", code)
            assert r.returncode == 0, f"item list --type {code} failed: {r.stderr}"
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            assert len(lines) == 1, f"Expected 1 {code} item, got {len(lines)}"

    def test_item_get_starter_items(self, dhf):
        dhf_root = str(dhf / "DHF")
        for uid in ("CRS-001", "SYS-001", "RISK-001", "CR-001"):
            r = _dhf(dhf_root, "item", "get", uid)
            assert r.returncode == 0, f"item get {uid} failed: {r.stderr}"
            item = json.loads(r.stdout)
            assert item["id"] == uid
            assert "Starter" in item.get("title", "")


class TestDocGeneration:
    """Document generation against the scaffolded starter DHF."""

    def test_doc_generate_all_types(self, dhf):
        dhf_root = str(dhf / "DHF")
        for dt in ("UC", "CRS", "SYS", "SRS", "SWDD", "SYSARCH", "RISK", "RCM", "CR"):
            r = _dhf(dhf_root, "doc", "generate", dt)
            if r.returncode != 0:
                stderr = r.stderr
                if "cannot load library" in stderr:
                    continue  # WeasyPrint/Pango missing
                pytest.fail(f"doc generate {dt} failed:\n{stderr}")
            result = json.loads(r.stdout)
            assert Path(result["output_path"]).exists(), f"Output missing for {dt}: {result['output_path']}"


class TestCICoverageGate:
    """Behavioral regression for ci test-coverage user feature."""

    def test_coverage_gate_evaluates(self, dhf):
        dhf_root = str(dhf / "DHF")
        import tempfile
        with tempfile.TemporaryDirectory() as junit_tmp:
            xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="demo" tests="1">
    <testcase name="test_starter_crs_coverage">
      <properties>
        <property name="medharness.id" value="TC-CRS-001-001"/>
        <property name="medharness.links" value="CRS-001"/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""
            (Path(junit_tmp) / "demo.xml").write_text(xml)
            r = _cf(dhf_root, "ci", "test-coverage", "--dhf", dhf_root,
                    "--junit-dir", junit_tmp, "--requirement-type", "CRS")
            assert r.returncode in (0, 1), f"ci test-coverage crashed:\n{r.stderr}"
            assert "CRS" in (r.stderr + r.stdout)


class TestScaffoldGuidance:
    """Verify 'replace me' guidance in scaffolded output."""

    def test_readme_has_replace_guidance(self, dhf):
        readme = (dhf / "DHF" / "README.md").read_text()
        assert "starter sample content" in readme.lower() or "replace" in readme.lower()

    def test_development_plan_has_starter_note(self, dhf):
        plan = (dhf / "DHF" / "documents" / "plans" / "development_plan.md").read_text()
        assert "starter" in plan.lower() or "replace" in plan.lower()

