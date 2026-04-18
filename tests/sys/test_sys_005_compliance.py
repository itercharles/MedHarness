"""
API tests for SYS-005: Compliance Assessment

Verifies: The system shall support compliance assessment against regulatory
policies and standards.

@links: SYS-005
"""

import pytest

from compliantflow.core import CompliantFlowCore
from compliantflow.backends.llm import GeminiBackend, OllamaBackend, get_default_backend
from compliantflow.policy import PolicyEngine


def test_TC_SYS_005_001_load_policy_groups(stub_adapter, governance_dir):
    """
    TC-SYS-005-001: Load Policy Groups (API)

    @links: SYS-005
    @test_id: TC-SYS-005-001

    Verify system can load compliance policy groups.
    """
    core = CompliantFlowCore(stub_adapter)

    assert governance_dir.exists(), "Governance directory should exist"

    policy_files = list(governance_dir.glob("*.yaml"))
    assert len(policy_files) > 0, "Should have at least one policy group"

    policy_group = core.get_policy_group("IEC_62304", governance_dir)

    assert policy_group is not None, "Should load IEC_62304 policy group"
    assert 'title' in policy_group
    assert 'policies' in policy_group


def test_TC_SYS_005_002_view_policies(stub_adapter, governance_dir):
    """
    TC-SYS-005-002: View Policy Definitions (API)

    @links: SYS-005
    @test_id: TC-SYS-005-002

    Verify system can retrieve policy definitions.
    """
    core = CompliantFlowCore(stub_adapter)

    policy_group = core.get_policy_group("IEC_62304", governance_dir)

    assert policy_group is not None
    assert 'policies' in policy_group

    policies = policy_group['policies']

    assert len(policies) > 0, "Policy group should have policies"

    for policy in policies:
        assert 'id' in policy, "Policy should have id"
        assert 'text' in policy, "Policy should have text/description"
        assert 'status' in policy, "Policy should have status"


def test_TC_SYS_005_003_run_compliance_check(stub_adapter, governance_dir):
    """
    TC-SYS-005-003: Run Compliance Assessment (API)

    @links: SYS-005
    @test_id: TC-SYS-005-003

    Verify system can run compliance checks and produce results.
    """
    core = CompliantFlowCore(stub_adapter)

    report = core.check_compliance("IEC_62304", governance_dir)

    assert report is not None, "Should generate compliance report"
    assert 'score' in report, "Report should have compliance score"
    assert 'results' in report, "Report should have detailed results"

    score = report['score']
    assert 0 <= score <= 100, "Compliance score should be 0-100"

    results = report['results']
    assert len(results) > 0, "Should have policy check results"

    for result in results:
        assert 'policy_id' in result
        assert 'passed' in result
        assert 'details' in result
        assert 'policy_text' in result, "Result should include policy_text from backend"
        assert isinstance(result['policy_text'], str)
        assert len(result['policy_text']) > 0, "policy_text should not be empty"


def test_TC_SYS_005_004_compliance_score_calculation(stub_adapter, governance_dir):
    """
    TC-SYS-005-004: Compliance Score Calculation (API)

    @links: SYS-005
    @test_id: TC-SYS-005-004

    Verify compliance score is calculated correctly.
    """
    core = CompliantFlowCore(stub_adapter)

    report = core.check_compliance("IEC_62304", governance_dir)

    results = report['results']
    total_policies = len(results)
    passed_policies = sum(1 for r in results if r['passed'])

    expected_score = (passed_policies / total_policies * 100) if total_policies > 0 else 0

    actual_score = report['score']
    assert abs(actual_score - expected_score) < 0.1, \
        f"Score should be {expected_score:.1f}, got {actual_score:.1f}"


def test_TC_SYS_005_005_policy_validation_details(stub_adapter, governance_dir):
    """
    TC-SYS-005-005: Policy Validation Details (API)

    @links: SYS-005
    @test_id: TC-SYS-005-005

    Verify compliance check provides detailed validation information.
    """
    core = CompliantFlowCore(stub_adapter)

    report = core.check_compliance("IEC_62304", governance_dir)

    results = report['results']

    for result in results:
        assert result['policy_id'], "Should have policy ID"
        assert isinstance(result['passed'], bool), "Should have boolean pass/fail"
        assert result['details'], "Should have validation details"

        if 'evidence' in result and result['evidence'] is not None:
            assert isinstance(result['evidence'], dict)


def test_TC_SYS_005_006_adapter_document_access(stub_adapter):
    """
    TC-SYS-005-006: Adapter document access API

    @links: SYS-005
    @test_id: TC-SYS-005-006

    Verify get_document() and list_documents() on the stub adapter.
    """
    docs = stub_adapter.list_documents()
    assert isinstance(docs, list)
    assert "test_plan" in docs, "test_plan document should be listed"

    content = stub_adapter.get_document("test_plan")
    assert content is not None, "Should retrieve test_plan document"
    assert "testing" in content.lower()
    assert "verification" in content.lower()

    missing = stub_adapter.get_document("nonexistent_document_xyz")
    assert missing is None, "Should return None for missing document"


def test_TC_SYS_005_007_document_content_check(stub_adapter, governance_dir):
    """
    TC-SYS-005-007: document_content policy check

    @links: SYS-005
    @test_id: TC-SYS-005-007

    Verify document_content automation check passes when keywords are present.
    """
    core = CompliantFlowCore(stub_adapter)
    report = core.check_compliance("IEC_62304", governance_dir)

    doc_results = [r for r in report['results'] if r['policy_id'] == 'TEST.doc_content']
    assert len(doc_results) == 1, "Should have TEST.doc_content policy result"

    result = doc_results[0]
    assert result['passed'] is True, f"document_content check should pass: {result['details']}"
    assert 'evidence' in result and result['evidence'] is not None
    assert 'keywords' in result['evidence']


def test_TC_SYS_005_008_attribute_value_check(stub_adapter, governance_dir):
    """
    TC-SYS-005-008: attribute_value policy check

    @links: SYS-005
    @test_id: TC-SYS-005-008

    Verify attribute_value automation check returns structured evidence.
    """
    core = CompliantFlowCore(stub_adapter)
    report = core.check_compliance("IEC_62304", governance_dir)

    attr_results = [r for r in report['results'] if r['policy_id'] == 'TEST.attr_value']
    assert len(attr_results) == 1, "Should have TEST.attr_value policy result"

    result = attr_results[0]
    assert isinstance(result['passed'], bool)
    assert result['details'], "Should have details string"
    assert 'evidence' in result and result['evidence'] is not None
    evidence = result['evidence']
    assert 'total' in evidence
    assert 'matching' in evidence
    assert 'non_matching' in evidence


def test_TC_SYS_005_009_default_backend_prefers_gemini(monkeypatch):
    """
    TC-SYS-005-009: get_default_backend prefers Gemini when GEMINI_API_KEY is set.

    @links: SYS-009
    @test_id: TC-SYS-005-009
    """
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("COMPLIANTFLOW_OLLAMA_URL", "http://localhost:11434")

    backend = get_default_backend()

    assert isinstance(backend, GeminiBackend)


def test_TC_SYS_005_010_default_backend_uses_ollama_when_gemini_absent(monkeypatch):
    """
    TC-SYS-005-010: get_default_backend selects Ollama when only Ollama is configured.

    @links: SYS-009
    @test_id: TC-SYS-005-010
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("COMPLIANTFLOW_OLLAMA_URL", "http://localhost:11434")

    backend = get_default_backend()

    assert isinstance(backend, OllamaBackend)


def test_TC_SYS_005_011_semantic_check_reports_missing_backend(stub_adapter):
    """
    TC-SYS-005-011: semantic policy checks fail with a clear explanation when no LLM backend is configured.

    @links: SYS-009
    @test_id: TC-SYS-005-011
    """
    core = CompliantFlowCore(stub_adapter)
    engine = PolicyEngine(core, llm_backend=None)

    with pytest.raises(RuntimeError, match="Semantic compliance checks require an LLM backend"):
        engine._check_document_semantic(
            doc_id="test_plan",
            requirement="Describe the verification milestones.",
        )


def test_TC_SYS_005_012_no_open_defects_passes_when_none_blocking(stub_adapter, governance_dir):
    """
    TC-SYS-005-012: no_open_defects passes when no Critical/High defects are open.

    @links: SYS-005
    @test_id: TC-SYS-005-012

    The test dataset contains DEF-001 (closed/High) and DEF-002 (closed/Low).
    Neither is in an open/in_progress state, so the check must pass.
    """
    core = CompliantFlowCore(stub_adapter)
    engine = PolicyEngine(core)

    passed, details, evidence = engine._check_no_open_defects(
        severity_threshold=['Critical', 'High'],
    )

    assert passed is True
    assert evidence['blocking_defects'] == []
    assert 'Critical' in evidence['severity_threshold']
    assert 'High' in evidence['severity_threshold']


def test_TC_SYS_005_013_no_open_defects_fails_when_blocking_defect_exists(stub_adapter):
    """
    TC-SYS-005-013: no_open_defects fails when a Critical/High defect is open.

    @links: SYS-005
    @test_id: TC-SYS-005-013

    Inject a Critical open defect into the stub adapter and verify the check
    surfaces it with structured evidence including the defect UID.
    """
    stub_adapter.create_item({
        'id': 'DEF-TEST',
        'title': 'Critical Open Defect',
        'description': 'A critical defect in open state.',
        'severity': 'Critical',
        'status': 'open',
    })

    core = CompliantFlowCore(stub_adapter)
    engine = PolicyEngine(core)

    passed, details, evidence = engine._check_no_open_defects(
        severity_threshold=['Critical', 'High'],
    )

    assert passed is False
    blocking_ids = [b['uid'] for b in evidence['blocking_defects']]
    assert 'DEF-TEST' in blocking_ids
    assert 'DEF-TEST' in details


def test_TC_SYS_005_014_persist_compliance_run(stub_adapter, governance_dir):
    """
    TC-SYS-005-014: check_compliance_group with persist=True appends a run
    record to the adapter's compliance run store.

    @test_id: TC-SYS-005-014
    @links: SYS-012

    Verifies that passing persist=True to CompliantFlowCore.check_compliance_group
    results in exactly one compliance run record being stored via record_compliance_run,
    and that the record contains the expected fields (source_id, score,
    passed_policies, total_policies, timestamp).
    """
    core = CompliantFlowCore(stub_adapter)
    report = core.check_compliance("IEC_62304", governance_dir, persist=True)

    assert report is not None
    runs = stub_adapter.get_compliance_runs("IEC_62304")
    assert len(runs) == 1, f"Expected 1 compliance run, got {len(runs)}"

    run = runs[0]
    assert run.get("source_id") == "IEC_62304"
    assert "score" in run
    assert "passed_policies" in run
    assert "total_policies" in run
    assert "timestamp" in run
