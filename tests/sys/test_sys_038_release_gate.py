"""
API tests for CR-024: Release Gate Enforcement via CLI.

Verifies that compliantflow validate release checks:
  1. REL item exists
  2. All included CRs are completed
  3. No open DEF items exist
  4. All SYS items have verification_status == 'verified'

@links: SYS-006, CRS-008
"""

import pytest
import yaml
from pathlib import Path

from utils.local_adapter import LocalDHFAdapter
from utils.models.item import Item
from utils.models.config import ProjectConfig
from utils.repository.saver import ItemSaver
from compliantflow.core import CompliantFlowCore


def _make_core(test_dhf_root):
    return CompliantFlowCore(LocalDHFAdapter(test_dhf_root, auto_commit=False))


def _enable_verification(test_dhf_root: Path) -> None:
    """Add has_verification: true to the SYS doc type in the test config."""
    sys_config_path = test_dhf_root / "config" / "doc_types" / "sys.yaml"
    with open(sys_config_path) as f:
        cfg = yaml.safe_load(f)
    cfg["has_verification"] = True
    with open(sys_config_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)


def _save(test_dhf_root, data: dict):
    config = ProjectConfig.load(test_dhf_root / "config")
    saver = ItemSaver(test_dhf_root / "items", git_repo=None, project_config=config)
    saver.save(Item.model_validate(data))


def test_TC_SYS_038_001_release_gate_passes_when_all_criteria_met(test_dhf_root):
    """
    TC-SYS-038-001: validate_release passes when all criteria are satisfied.

    A REL item with completed CRs, no open DEFs, and all SYS items verified
    should pass all four gate checks.

    @test_id: TC-SYS-038-001
    @links: SYS-006, CRS-008
    """
    # Completed CR
    _save(test_dhf_root, {
        'id': 'CR-REL-001', 'title': 'Completed CR', 'description': 'done',
        'justification': 'done', 'status': 'completed',
    })
    # REL referencing only completed CRs
    _save(test_dhf_root, {
        'id': 'REL-TEST-001', 'title': 'Test Release', 'version': '1.0.0',
        'status': 'draft', 'included_items': ['CR-REL-001'],
    })
    # Mark all SYS items as verified via direct result recording
    _enable_verification(test_dhf_root)
    adapter = LocalDHFAdapter(test_dhf_root, auto_commit=False)
    adapter.record_test_result(tc_id='TC-SYS-999', testing_status='PASS',
                               tester='test-setup', links=['SYS-001', 'SYS-002'])
    core = _make_core(test_dhf_root)

    report = core.validate_release('REL-TEST-001')

    assert report['passed'] is True, f"Expected gate to pass: {report}"
    assert all(c['passed'] for c in report['checks'])


def test_TC_SYS_038_002_release_gate_fails_for_incomplete_cr(test_dhf_root):
    """
    TC-SYS-038-002: validate_release fails when an included CR is not completed.

    If a CR in included_items has status != 'completed', the crs_completed
    check must fail and the overall gate must fail.

    @test_id: TC-SYS-038-002
    @links: SYS-006, CRS-008
    """
    # Draft CR (not completed)
    _save(test_dhf_root, {
        'id': 'CR-REL-002', 'title': 'Draft CR', 'description': 'pending',
        'justification': 'pending', 'status': 'draft',
    })
    _save(test_dhf_root, {
        'id': 'REL-TEST-002', 'title': 'Test Release', 'version': '1.0.0',
        'status': 'draft', 'included_items': ['CR-REL-002'],
    })

    core = _make_core(test_dhf_root)
    report = core.validate_release('REL-TEST-002')

    assert report['passed'] is False
    cr_check = next(c for c in report['checks'] if c['name'] == 'crs_completed')
    assert cr_check['passed'] is False
    assert 'CR-REL-002' in str(cr_check.get('items', ''))


def test_TC_SYS_038_003_release_gate_fails_for_open_defect(test_dhf_root):
    """
    TC-SYS-038-003: validate_release fails when an open DEF item exists.

    A DEF item with status 'open' or 'in_progress' must cause the
    no_open_defects check to fail.

    @test_id: TC-SYS-038-003
    @links: SYS-006, CRS-008
    """
    _save(test_dhf_root, {
        'id': 'DEF-TEST-001', 'title': 'Open Defect',
        'description': 'Bug found', 'severity': 'High', 'status': 'open',
    })
    _save(test_dhf_root, {
        'id': 'REL-TEST-003', 'title': 'Test Release', 'version': '1.0.0',
        'status': 'draft', 'included_items': [],
    })

    core = _make_core(test_dhf_root)
    report = core.validate_release('REL-TEST-003')

    assert report['passed'] is False
    def_check = next(c for c in report['checks'] if c['name'] == 'no_open_defects')
    assert def_check['passed'] is False
    assert 'DEF-TEST-001' in str(def_check.get('items', ''))


def test_TC_SYS_038_004_release_gate_fails_for_unverified_sys(test_dhf_root):
    """
    TC-SYS-038-004: validate_release fails when SYS items are not verified.

    SYS items without verification_status == 'verified' must cause the
    sys_requirements_verified check to fail.

    @test_id: TC-SYS-038-004
    @links: SYS-006, CRS-008
    """
    _save(test_dhf_root, {
        'id': 'REL-TEST-004', 'title': 'Test Release', 'version': '1.0.0',
        'status': 'draft', 'included_items': [],
    })
    # SYS-001 and SYS-002 exist in fixtures but have no test results → not_verified
    core = _make_core(test_dhf_root)
    report = core.validate_release('REL-TEST-004')

    assert report['passed'] is False
    sys_check = next(c for c in report['checks'] if c['name'] == 'sys_requirements_verified')
    assert sys_check['passed'] is False


def test_TC_SYS_038_005_release_gate_fails_for_nonexistent_rel(test_dhf_root):
    """
    TC-SYS-038-005: validate_release fails with a clear error when REL ID does not exist.

    @test_id: TC-SYS-038-005
    @links: SYS-006, CRS-008
    """
    core = _make_core(test_dhf_root)
    report = core.validate_release('REL-DOES-NOT-EXIST')

    assert report['passed'] is False
    assert report['checks'][0]['name'] == 'rel_exists'
    assert report['checks'][0]['passed'] is False
