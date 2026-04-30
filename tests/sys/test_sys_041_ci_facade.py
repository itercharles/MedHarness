"""
Tests for SYS-041: CI gate, evidence, and artifact facade commands.

Verifies that product CI can call CompliantFlow's stable ci namespace instead
of depending directly on DHF utils commands or storage paths.

@links: SYS-041
"""

import json
from pathlib import Path

from click.testing import CliRunner

from compliantflow.cli import main


class FakeCore:
    def __init__(self, traceability=None, coverage=None, adapter=None):
        self.traceability = traceability or {"valid": True, "issues": []}
        self.coverage = coverage or {"passed": True, "results": []}
        self.injected = []
        self._adapter = adapter or FakeAdapter()

    def inject_junit_results(self, paths):
        self.injected = paths

    def validate(self):
        return self.traceability

    def check_coverage(self, pairs):
        self.coverage["pairs"] = pairs
        return self.coverage


class FakeAdapter:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.imported = []
        self.doc_types = ["SYS", "SRS"]

    def import_results_from_file(self, **kwargs):
        self.imported.append(kwargs)
        return self.results.pop(0)

    def get_available_doc_types(self):
        return list(self.doc_types)

    def validate_traceability(self):
        return {"passed": True, "required": {"passed": True, "failures": []},
                "coverage": [], "deprecation_warnings": [], "summary": "PASS"}

    def generate_doc(self, doc_type_code):
        doc_dir = self._dhf_root / "specs" if hasattr(self, "_dhf_root") else Path("/tmp")
        doc_dir.mkdir(parents=True, exist_ok=True)
        out = doc_dir / f"{doc_type_code}.pdf"
        out.write_text("fake pdf", encoding="utf-8")
        return {"doc_type": doc_type_code, "output_path": str(out), "version": "1.0"}

    @property
    def _config(self):
        class Cfg:
            doc_types = []

            def get_doc_type(self, code):
                from unittest.mock import MagicMock
                m = MagicMock()
                m.code = code
                m.prefix = f"{code}-"
                m.has_verification = True
                return m

            def get_doc_type_by_prefix(self, pfx):
                return self.get_doc_type(pfx.rstrip("-"))

        c = Cfg()
        c.doc_types = [c.get_doc_type(t) for t in self.doc_types]
        return c


def _invoke(monkeypatch, args, core=None, adapter=None, patch_artifacts=True):
    if core is not None:
        monkeypatch.setattr("compliantflow.cli._make_core", lambda ctx: core)
    if adapter is not None:
        monkeypatch.setattr("compliantflow.cli._make_adapter", lambda ctx: adapter)
    if patch_artifacts:
        # Make artifact generation a no-op for unit tests.
        stub_artifact = lambda *a, **kw: {"out_dir": str(a[3]) if len(a) > 3 else str(kw.get("out_dir", "")),
                                          "specifications": [],
                                          "plans": [],
                                          "traceability": {"path": "/tmp/trace.pdf"},
                                          "junit_files": [str(p) for p in (a[6] if len(a) > 6 else kw.get("junit_paths", []))]}
        monkeypatch.setattr("compliantflow.cli._run_artifact_generation", stub_artifact)
        monkeypatch.setattr("compliantflow.cli._generate_plan_artifacts", lambda *a, **kw: [])
        monkeypatch.setattr("compliantflow.cli._generate_specification_artifacts",
                            lambda *a, **kw: [{"doc_type": "SYS", "path": "specs/SYS.pdf"}])
    # Avoid dhf_util import in unit tests
    monkeypatch.setattr("compliantflow.cli._summarize_junit_file",
                        lambda p: {"path": str(p), "imported": 1, "skipped": 0,
                                   "items_updated": [], "failed_tcs": []})
    return CliRunner().invoke(main, args)


def test_TC_SYS_041_001_ci_gate_acceptance_passes_with_default_coverage(monkeypatch):
    """
    TC-SYS-041-001: ci gate acceptance evaluates traceability and default coverage.

    @test_id: TC-SYS-041-001
    @links: SYS-041
    """
    core = FakeCore(coverage={"passed": True, "results": [
        {"parent_type": "UC", "child_type": "CRS", "covered": 1, "total": 1, "passed": True},
    ]})

    result = _invoke(monkeypatch, ["ci", "gate", "acceptance"], core=core)

    assert result.exit_code == 0
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is True
    assert ["UC", "CRS"] in payload["coverage"]["pairs"]
    assert ["SRS", "SWDD"] in payload["coverage"]["pairs"]


def test_TC_SYS_041_002_ci_gate_acceptance_fails_on_traceability_issue(monkeypatch):
    """
    TC-SYS-041-002: ci gate acceptance exits nonzero when traceability fails.

    @test_id: TC-SYS-041-002
    @links: SYS-041
    """
    core = FakeCore(
        traceability={"valid": False, "issues": [{"type": "orphan", "items": ["SYS-999"]}]},
        coverage={"passed": True, "results": []},
    )

    result = _invoke(monkeypatch, ["ci", "gate", "acceptance"], core=core)

    assert result.exit_code == 1
    assert json.loads(result.output.splitlines()[0])["passed"] is False
    assert "SYS-999" in result.output


def test_TC_SYS_041_003_ci_evidence_import_aggregates_multiple_junit_files(
    monkeypatch,
    tmp_path,
):
    """
    TC-SYS-041-003: ci evidence import aggregates adapter import summaries.

    @test_id: TC-SYS-041-003
    @links: SYS-041
    """
    first = tmp_path / "first.xml"
    second = tmp_path / "second.xml"
    first.write_text("<testsuite/>", encoding="utf-8")
    second.write_text("<testsuite/>", encoding="utf-8")
    adapter = FakeAdapter(results=[
        {
            "recorded": [
                {"tc_id": "TC-SYS-001-001", "links": ["SYS-001"], "testing_status": "PASS"},
            ],
            "skipped": 0,
        },
        {
            "recorded": [
                {"tc_id": "TC-SYS-002-001", "links": ["SYS-001", "SYS-002"], "testing_status": "FAIL"},
            ],
            "skipped": 1,
        },
    ])

    result = _invoke(
        monkeypatch,
        [
            "ci", "evidence", "import",
            str(first), str(second),
            "--tester", "ci",
            "--run-id", "123",
        ],
        adapter=adapter,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output.splitlines()[0])
    assert payload["imported"] == 2
    assert payload["skipped"] == 1
    assert payload["items_updated"] == ["SYS-001", "SYS-002"]
    assert payload["failed_tcs"] == ["TC-SYS-002-001"]
    assert adapter.imported[0]["tester"] == "ci"
    assert adapter.imported[0]["run_id"] == "123"


def test_TC_SYS_041_004_ci_artifacts_generate_orchestrates_adapter_and_report_helpers(
    monkeypatch,
    tmp_path,
):
    """
    TC-SYS-041-004: ci artifacts generate writes a structured artifact manifest.

    @test_id: TC-SYS-041-004
    @links: SYS-041
    """
    out_dir = tmp_path / "artifacts"
    pdf = tmp_path / "SYS.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    class ArtifactAdapter:
        def get_available_doc_types(self):
            return ["SYS"]

        def export_pdf(self, doc_type):
            assert doc_type == "SYS"
            return {"doc_type": doc_type, "pdf_path": str(pdf), "version": "1.0"}

    monkeypatch.setattr("compliantflow.cli._make_adapter", lambda ctx: ArtifactAdapter())
    monkeypatch.setattr("compliantflow.cli._make_core", lambda ctx: object())
    monkeypatch.setattr(
        "compliantflow.cli._generate_plan_artifacts",
        lambda dhf_path, output_dir: [{"source": "plan.md", "path": str(output_dir / "plans" / "plan.pdf")}],
    )
    monkeypatch.setattr(
        "compliantflow.cli._write_traceability_report",
        lambda core, doc_types, output, junit_paths: {"path": str(output), "rows": 3},
    )

    result = CliRunner().invoke(main, ["ci", "artifacts", "generate", "--out-dir", str(out_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output.splitlines()[0])
    assert payload["specifications"][0]["doc_type"] == "SYS"
    assert Path(payload["specifications"][0]["path"]).exists()
    assert payload["plans"][0]["source"] == "plan.md"
    assert payload["traceability"]["rows"] == 3


def test_TC_SYS_041_005_ci_run_acceptance_collects_recursive_junit_inputs(
    monkeypatch,
    tmp_path,
):
    """
    TC-SYS-041-005: ci run acceptance collects junit files from files and directories.

    @test_id: TC-SYS-041-005
    @links: SYS-041
    """
    direct = tmp_path / "verification-junit.xml"
    direct.write_text("<testsuite/>", encoding="utf-8")
    junit_dir = tmp_path / "nested-results"
    nested_dir = junit_dir / "deep"
    nested_dir.mkdir(parents=True)
    nested = nested_dir / "extra.xml"
    nested.write_text("<testsuite/>", encoding="utf-8")
    missing_dir = tmp_path / "missing-results"
    core = FakeCore(
        coverage={
            "passed": True,
            "results": [
                {"parent_type": "UC", "child_type": "CRS", "covered": 1, "total": 1, "passed": True},
            ],
        }
    )

    result = _invoke(
        monkeypatch,
        [
            "ci", "run", "acceptance",
            "--junit", str(direct),
            "--junit-dir", str(junit_dir),
            "--junit-dir", str(missing_dir),
        ],
        core=core,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output.splitlines()[0])
    assert payload["junit_files"] == [str(direct), str(nested)]
    assert core.injected == [direct, nested]
    assert payload["coverage"]["pairs"] == [
        ["UC", "CRS"],
        ["CRS", "SYS"],
        ["SYS", "SRS"],
        ["SRS", "SWDD"],
    ]


def test_TC_SYS_041_006_ci_run_artifacts_collects_junit_inputs_for_traceability(
    monkeypatch,
    tmp_path,
):
    """
    TC-SYS-041-006: ci run artifacts passes collected junit files into traceability generation.

    @test_id: TC-SYS-041-006
    @links: SYS-041
    """
    out_dir = tmp_path / "artifacts"
    direct = tmp_path / "verification-junit.xml"
    direct.write_text("<testsuite/>", encoding="utf-8")
    junit_dir = tmp_path / "junit-results"
    nested_dir = junit_dir / "nested"
    nested_dir.mkdir(parents=True)
    nested = nested_dir / "system.xml"
    nested.write_text("<testsuite/>", encoding="utf-8")
    missing_dir = tmp_path / "missing-results"
    pdf = tmp_path / "SYS.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    traceability_capture = {}

    class ArtifactAdapter:
        def get_available_doc_types(self):
            return ["SYS"]

        def export_pdf(self, doc_type):
            assert doc_type == "SYS"
            return {"doc_type": doc_type, "pdf_path": str(pdf), "version": "1.0"}

    monkeypatch.setattr("compliantflow.cli._make_adapter", lambda ctx: ArtifactAdapter())
    monkeypatch.setattr("compliantflow.cli._make_core", lambda ctx: object())
    def fake_generate_plan_artifacts(dhf_path, output_dir):
        plan_path = output_dir / "plans" / "plan.pdf"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text("plan pdf", encoding="utf-8")
        return [{"source": "plan.md", "path": str(plan_path)}]

    def fake_generate_specification_artifacts(adapter, out_dir, doc_types):
        spec_path = out_dir / "specifications" / "SYS.pdf"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("spec pdf", encoding="utf-8")
        return [{"doc_type": "SYS", "path": str(spec_path), "source": str(pdf), "version": "1.0"}]

    monkeypatch.setattr("compliantflow.cli._generate_plan_artifacts", fake_generate_plan_artifacts)
    monkeypatch.setattr("compliantflow.cli._generate_specification_artifacts", fake_generate_specification_artifacts)
    monkeypatch.setattr(
        "compliantflow.cli._write_traceability_report",
        lambda core, doc_types, output, junit_paths: traceability_capture.update({
            "doc_types": list(doc_types),
            "output": str(output),
            "junit_paths": list(junit_paths),
        }) or {"path": str(output), "rows": 3},
    )

    result = _invoke(
        monkeypatch,
        [
            "ci", "run", "artifacts",
            "--out-dir", str(out_dir),
            "--junit", str(direct),
            "--junit-dir", str(junit_dir),
            "--junit-dir", str(missing_dir),
            "--skip-plans",
        ],
        patch_artifacts=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output.splitlines()[0])
    assert payload["junit_files"] == [str(direct), str(nested)]
    assert traceability_capture["junit_paths"] == [str(direct), str(nested)]
    assert traceability_capture["doc_types"] == ["UC", "CRS", "SYS", "SRS", "SWDD"]
    assert payload["plans"] == []
    assert Path(payload["specifications"][0]["path"]).exists()


def test_TC_SYS_041_007_ci_evidence_record_orchestrates_verification_evidence(
    monkeypatch,
    tmp_path,
):
    """
    TC-SYS-041-007: ci evidence record runs tests and writes artifact-based evidence.

    @test_id: TC-SYS-041-007
    @links: SYS-041
    """
    dhf_root = tmp_path / "DHF"
    dhf_root.mkdir(parents=True)
    gov_dir = tmp_path / "governance"
    gov_dir.mkdir()
    junit_dir = tmp_path / "junit"
    out_dir = tmp_path / "evidence"
    first_xml = junit_dir / "sys.xml"
    second_xml = junit_dir / "crs.xml"

    monkeypatch.setattr("compliantflow.cli._make_core", lambda ctx: object())
    monkeypatch.setattr(
        "compliantflow.cli._run_pytest_junit",
        lambda test_paths, out_dir: [first_xml, second_xml],
    )
    monkeypatch.setattr(
        "compliantflow.cli._summarize_junit_file",
        lambda path: {
            "path": str(path),
            "imported": 1,
            "skipped": 0,
            "items_updated": ["SYS-001"],
            "failed_tcs": [],
        },
    )
    monkeypatch.setattr(
        "compliantflow.cli._run_compliance_checks",
        lambda core, governance_dir, standards: [
            {
                "standard": standard,
                "score": 100,
                "passed_policies": 2,
                "total_policies": 2,
                "failed_policies": 0,
            }
            for standard in standards
        ],
    )

    result = CliRunner().invoke(
        main,
        [
            "--dhf", str(dhf_root),
            "ci", "evidence", "record",
            "--test-path", "tests/sys",
            "--test-path", "tests/crs",
            "--junit-dir", str(junit_dir),
            "--out-dir", str(out_dir),
            "--governance-dir", str(gov_dir),
            "--standard", "IEC_62304",
            "--run-id", "123",
            "--run-url", "https://example.test/run/123",
            "--commit", "abcdef123456",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[0])
    assert payload["imported"] == 2
    assert payload["run_id"] == "123"
    assert payload["commit_sha"] == "abcdef123456"
    summary = json.loads((out_dir / "evidence-summary.json").read_text(encoding="utf-8"))
    assert summary["imported"] == 2
    assert summary["failed_standards"] == []


# ── ci evidence bundle tests ────────────────────────────────────────────

def _make_junit_xml(name: str, tests: list[dict]) -> Path:
    p = Path(f"/tmp/{name}")
    suites = "\n".join(
        f'  <testsuite name="{t["suite"]}" tests="{t["count"]}">\n'
        + "\n".join(
            f'    <testcase classname="{tc["class"]}" name="{tc["name"]}" time="0.01"'
            + (">" if tc.get("status") == "PASS" else ">")
            + (f'\n      <failure message="{tc.get("message", "")}"/>' if tc.get("status") == "FAIL" else "")
            + "\n    </testcase>"
            for tc in t["cases"]
        )
        + "\n  </testsuite>"
        for t in tests
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<testsuites>\n{suites}\n</testsuites>\n'
    p.write_text(xml, encoding="utf-8")
    return p


class TestEvidenceBundle:
    """@links: SYS-041"""

    def test_bundle_gate_pass_generates_manifest(self, monkeypatch, tmp_path):
        core = FakeCore(coverage={"passed": True, "results": []})
        adapter = FakeAdapter()
        junit = _make_junit_xml("srs.xml", [
            {"suite": "srs", "count": 1, "cases": [
                {"class": "TestFoo", "name": "test_pass @links:SRS-001", "status": "PASS"},
            ]},
        ])
        out = tmp_path / "evidence"

        result = _invoke(monkeypatch, [
            "--dhf", str(tmp_path),
            "ci", "evidence", "bundle",
            "--out-dir", str(out),
            "--junit", str(junit),
            "--run-id", "42",
            "--run-url", "https://ci.test/42",
            "--commit", "abc123",
        ], core=core, adapter=adapter)

        assert result.exit_code == 0, result.output
        assert (out / "evidence-summary.json").exists()
        manifest = json.loads((out / "evidence-manifest.json").read_text(encoding="utf-8"))
        assert manifest["gate_passed"] is True
        assert manifest["acceptance_result"] == "PASS"
        assert manifest["run_id"] == "42"
        assert manifest["commit_sha"] == "abc123"
        assert len(manifest["files"]) >= 1  # at least evidence-summary

    def test_bundle_gate_fail_exits_nonzero(self, monkeypatch, tmp_path):
        core = FakeCore(
            traceability={"valid": False, "issues": [{"type": "orphan", "items": ["SRS-099"]}]},
            coverage={"passed": False, "results": [
                {"parent_type": "UC", "child_type": "CRS", "covered": 0, "total": 5, "passed": False},
            ]},
        )
        adapter = FakeAdapter()
        out = tmp_path / "evidence"

        result = _invoke(monkeypatch, [
            "--dhf", str(tmp_path),
            "ci", "evidence", "bundle",
            "--out-dir", str(out),
            "--coverage-pair", "UC:CRS",
        ], core=core, adapter=adapter)

        assert result.exit_code != 0

    def test_bundle_continue_on_gate_failure_exits_zero(self, monkeypatch, tmp_path):
        core = FakeCore(
            traceability={"valid": False, "issues": [{"type": "orphan", "items": ["SRS-099"]}]},
            coverage={"passed": False, "results": [
                {"parent_type": "UC", "child_type": "CRS", "covered": 0, "total": 5, "passed": False},
            ]},
        )
        adapter = FakeAdapter()
        out = tmp_path / "evidence"

        result = _invoke(monkeypatch, [
            "--dhf", str(tmp_path),
            "ci", "evidence", "bundle",
            "--out-dir", str(out),
            "--continue-on-gate-failure",
            "--coverage-pair", "UC:CRS",
        ], core=core, adapter=adapter)

        assert result.exit_code == 0, result.output
        manifest = json.loads((out / "evidence-manifest.json").read_text(encoding="utf-8"))
        assert manifest["gate_passed"] is False

    def test_bundle_missing_junit_dir_is_ignored(self, monkeypatch, tmp_path):
        core = FakeCore(coverage={"passed": True, "results": []})
        adapter = FakeAdapter()
        out = tmp_path / "evidence"

        result = _invoke(monkeypatch, [
            "--dhf", str(tmp_path),
            "ci", "evidence", "bundle",
            "--out-dir", str(out),
            "--junit-dir", str(tmp_path / "nonexistent"),
        ], core=core, adapter=adapter)

        assert result.exit_code == 0, result.output

    def test_bundle_manifest_contains_sha256(self, monkeypatch, tmp_path):
        core = FakeCore(coverage={"passed": True, "results": []})
        adapter = FakeAdapter()
        junit = _make_junit_xml("sys.xml", [
            {"suite": "sys", "count": 1, "cases": [
                {"class": "TestBar", "name": "test_pass", "status": "PASS"},
            ]},
        ])
        out = tmp_path / "evidence"

        result = _invoke(monkeypatch, [
            "--dhf", str(tmp_path),
            "ci", "evidence", "bundle",
            "--out-dir", str(out),
            "--junit", str(junit),
        ], core=core, adapter=adapter)

        assert result.exit_code == 0, result.output
        manifest = json.loads((out / "evidence-manifest.json").read_text(encoding="utf-8"))
        for f in manifest["files"]:
            assert len(f["sha256"]) == 64
            assert f["size"] > 0

    def test_bundle_no_dhf_mutation_calls(self, monkeypatch, tmp_path):
        core = FakeCore(coverage={"passed": True, "results": []})

        class TrackingAdapter(FakeAdapter):
            wrote = False
            def import_results_from_file(self, **kwargs):
                self.wrote = True
                return {"recorded": [], "skipped": 0}

        adapter = TrackingAdapter()
        junit = _make_junit_xml("test.xml", [
            {"suite": "t", "count": 1, "cases": [
                {"class": "T", "name": "t1", "status": "PASS"},
            ]},
        ])
        out = tmp_path / "evidence"

        result = _invoke(monkeypatch, [
            "--dhf", str(tmp_path),
            "ci", "evidence", "bundle",
            "--out-dir", str(out),
            "--junit", str(junit),
        ], core=core, adapter=adapter)

        assert result.exit_code == 0, result.output
        assert not adapter.wrote, "bundle must not call DHF write methods"


# ── ci dhf-validate tests ──────────────────────────────────────────────────


class _FakeLocalDHFAdapter:
    """Fake adapter for ci dhf-validate tests."""
    def __init__(self, dhf_path, schema_valid=True, item_count=10,
                 trace_passed=True, trace_failures=None, coverage_results=None):
        self.dhf_path = dhf_path
        self._schema_valid = schema_valid
        self._item_count = item_count
        self._trace_passed = trace_passed
        self._trace_failures = trace_failures or []
        self._coverage_results = coverage_results or []

    def validate_schema(self):
        return {"valid": self._schema_valid, "errors": [],
                "item_count": self._item_count}

    def validate_traceability(self):
        return {
            "passed": self._trace_passed and len(self._trace_failures) == 0,
            "required": {"passed": len(self._trace_failures) == 0,
                          "failures": self._trace_failures},
            "coverage": self._coverage_results,
            "deprecation_warnings": [],
            "summary": "PASS" if self._trace_passed else "FAIL",
        }


def _mock_dhf_validate(monkeypatch, mock_adapter=None, mock_core=None):
    """Patch the deps used by ci dhf-validate: LocalDHFAdapter and CompliantFlowCore."""
    if mock_adapter is not None:
        monkeypatch.setattr(
            "dhf_util.local_adapter.LocalDHFAdapter",
            lambda dhf_path, auto_commit=False: mock_adapter if not callable(mock_adapter) else mock_adapter(dhf_path),
        )
    # Always provide a stub core — ci dhf-validate always creates one.
        class _StubCore:
            def __init__(self, adapter=None, llm_backend=None): pass
            def check_coverage(self, pairs): return {"passed": True, "results": []}
            def check_compliance(self, group_id, governance_dir): return {"score": 100.0}
    core = mock_core
    if isinstance(core, type):
        core = core()
    if core is None:
        core = _StubCore()
    monkeypatch.setattr(
        "compliantflow.core.CompliantFlowCore",
        lambda adapter, llm_backend=None: core,
    )


def test_dhf_validate_schema_pass(monkeypatch, tmp_path):
    _mock_dhf_validate(monkeypatch, mock_adapter=_FakeLocalDHFAdapter(str(tmp_path)))

    result = CliRunner().invoke(main, [
        "ci", "dhf-validate",
        "--dhf", str(tmp_path),
        "--run-schema",
        "--no-run-traceability",
    ])
    assert result.exit_code == 0
    assert "PASS [schema]" in result.output


def test_dhf_validate_schema_fail(monkeypatch, tmp_path):
    _mock_dhf_validate(monkeypatch,
                       mock_adapter=lambda dhf: _FakeLocalDHFAdapter(dhf, schema_valid=False))

    result = CliRunner().invoke(main, [
        "ci", "dhf-validate",
        "--dhf", str(tmp_path),
        "--run-schema",
        "--no-run-traceability",
    ])
    assert result.exit_code != 0
    assert "FAIL [schema]" in result.output


def test_dhf_validate_traceability_required_fail(monkeypatch, tmp_path):
    _mock_dhf_validate(monkeypatch,
                       mock_adapter=lambda dhf: _FakeLocalDHFAdapter(dhf,
                           trace_passed=False,
                           trace_failures=[{"id": "RCM-001", "issue": "RCM implements → SYS (count=0)"}],
                           coverage_results=[
                               {"parent_type": "UC", "child_type": "CRS", "passed": True,
                                "total": 5, "covered": 5, "uncovered": []},
                           ],
                       ))

    result = CliRunner().invoke(main, [
        "ci", "dhf-validate",
        "--dhf", str(tmp_path),
        "--run-traceability",
        "--no-run-schema",
    ])
    assert result.exit_code != 0
    assert "FAIL [required]" in result.output


def test_dhf_validate_coverage_fail_with_flag(monkeypatch, tmp_path):
    _mock_dhf_validate(monkeypatch,
                       mock_adapter=lambda dhf: _FakeLocalDHFAdapter(dhf,
                           coverage_results=[
                               {"parent_type": "CRS", "child_type": "SYS", "passed": False,
                                "total": 10, "covered": 9, "uncovered": ["CRS-011"]},
                           ],
                       ))

    result = CliRunner().invoke(main, [
        "ci", "dhf-validate",
        "--dhf", str(tmp_path),
        "--run-traceability",
        "--no-run-schema",
        "--fail-on-uncovered",
    ])
    assert result.exit_code != 0
    assert "FAIL [coverage]" in result.output


def test_dhf_validate_coverage_pass_without_flag(monkeypatch, tmp_path):
    _mock_dhf_validate(monkeypatch,
                       mock_adapter=lambda dhf: _FakeLocalDHFAdapter(dhf,
                           coverage_results=[
                               {"parent_type": "CRS", "child_type": "SYS", "passed": False,
                                "total": 10, "covered": 9, "uncovered": ["CRS-011"]},
                           ],
                       ))

    result = CliRunner().invoke(main, [
        "ci", "dhf-validate",
        "--dhf", str(tmp_path),
        "--run-traceability",
        "--no-run-schema",
    ])
    assert result.exit_code == 0  # uncovered items don't fail without --fail-on-uncovered


def test_dhf_validate_compliance_pass(monkeypatch, tmp_path):
    class FakeCore:
        def check_compliance(self, group_id, governance_dir):
            return {"score": 100.0, "passed_policies": 5, "total_policies": 5}

    _mock_dhf_validate(monkeypatch,
                       mock_adapter=_FakeLocalDHFAdapter(str(tmp_path)),
                       mock_core=FakeCore())

    result = CliRunner().invoke(main, [
        "ci", "dhf-validate",
        "--dhf", str(tmp_path),
        "--run-compliance",
        "--compliance-standard", "IEC_62304",
        "--no-run-schema",
        "--no-run-traceability",
    ])
    assert result.exit_code == 0
    assert "PASS [compliance]" in result.output


def test_dhf_validate_compliance_fail(monkeypatch, tmp_path):
    class FakeCore:
        def check_compliance(self, group_id, governance_dir):
            return {"score": 75.0, "passed_policies": 3, "total_policies": 4}

    _mock_dhf_validate(monkeypatch,
                       mock_adapter=_FakeLocalDHFAdapter(str(tmp_path)),
                       mock_core=FakeCore())

    result = CliRunner().invoke(main, [
        "ci", "dhf-validate",
        "--dhf", str(tmp_path),
        "--run-compliance",
        "--compliance-standard", "IEC_62304",
        "--no-run-schema",
        "--no-run-traceability",
    ])
    assert result.exit_code != 0
    assert "FAIL [compliance]" in result.output
    assert "3/4 (75.0%)" in result.output


def test_dhf_validate_compliance_missing_group(monkeypatch, tmp_path):
    class FakeCore:
        def check_compliance(self, group_id, governance_dir):
            return None

    _mock_dhf_validate(monkeypatch,
                       mock_adapter=_FakeLocalDHFAdapter(str(tmp_path)),
                       mock_core=FakeCore())

    result = CliRunner().invoke(main, [
        "ci", "dhf-validate",
        "--dhf", str(tmp_path),
        "--run-compliance",
        "--compliance-standard", "IEC_62304",
        "--no-run-schema",
        "--no-run-traceability",
    ])
    assert result.exit_code != 0
    assert "FAIL [compliance]" in result.output
