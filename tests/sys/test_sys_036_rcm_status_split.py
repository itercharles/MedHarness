"""
API tests for CR-033: Split RCM implementation_status into two fields.

Verifies that the RCM schema now uses separate implementation_status
(Planned/Implemented) and verification_status (Not Verified/Verified) fields,
and that ISO 14971 policies 7.2.a and 7.6.b check them independently.

@links: SYS-005, SYS-012
"""

import pytest
from pathlib import Path

from utils.local_adapter import LocalDHFAdapter
from utils.repository.loader import ValidationError
from compliantflow.core import CompliantFlowCore


def _make_core(test_dhf_root):
    return CompliantFlowCore(LocalDHFAdapter(test_dhf_root, auto_commit=False))


def _save_rcm(test_dhf_root, rcm_id, implementation_status=None, verification_status=None):
    """Write an RCM item directly via ItemSaver (bypasses adapter validation — for valid items only)."""
    from utils.models.item import Item
    from utils.repository.saver import ItemSaver
    from utils.models.config import ProjectConfig

    config = ProjectConfig.load(test_dhf_root / "config")
    saver = ItemSaver(test_dhf_root / "items", git_repo=None, project_config=config)
    data = {
        'id': rcm_id,
        'title': f'Test RCM {rcm_id}',
        'content': 'Test risk control measure',
        'control_type': 'Protective Measure',
    }
    if implementation_status is not None:
        data['implementation_status'] = implementation_status
    if verification_status is not None:
        data['verification_status'] = verification_status

    item = Item.model_validate(data)
    saver.save(item)


def _get_policy_result(report, policy_id):
    return next((r for r in report['results'] if r['policy_id'] == policy_id), None)


def test_TC_SYS_036_001_planned_rcm_fails_both_policies(test_dhf_root, governance_dir):
    """
    TC-SYS-036-001: RCM in Planned/Not Verified state fails both ISO 14971 policies.

    An RCM with implementation_status=Planned and verification_status=Not Verified
    should fail policy 7.2.a (controls must be Implemented) and policy 7.6.b
    (controls must be Verified).

    @test_id: TC-SYS-036-001
    @links: SYS-005, SYS-012
    """
    _save_rcm(test_dhf_root, 'RCM-TEST-001',
              implementation_status='Planned', verification_status='Not Verified')

    core = _make_core(test_dhf_root)
    report = core.check_compliance("ISO_14971", governance_dir)

    result_72a = _get_policy_result(report, '7.2.a')
    result_76b = _get_policy_result(report, '7.6.b')

    assert result_72a is not None, "Policy 7.2.a should be present"
    assert result_76b is not None, "Policy 7.6.b should be present"
    assert result_72a['passed'] is False, "7.2.a should fail: implementation_status is Planned, not Implemented"
    assert result_76b['passed'] is False, "7.6.b should fail: verification_status is Not Verified, not Verified"


def test_TC_SYS_036_002_implemented_not_verified_passes_72a_fails_76b(test_dhf_root, governance_dir):
    """
    TC-SYS-036-002: Implemented but not-yet-verified RCM passes 7.2.a, fails 7.6.b.

    With the split fields, an RCM that has been implemented but not yet verified
    can now be represented unambiguously. Policy 7.2.a (implementation check)
    passes while 7.6.b (verification check) correctly fails.

    @test_id: TC-SYS-036-002
    @links: SYS-005, SYS-012
    """
    _save_rcm(test_dhf_root, 'RCM-TEST-002',
              implementation_status='Implemented', verification_status='Not Verified')

    core = _make_core(test_dhf_root)
    report = core.check_compliance("ISO_14971", governance_dir)

    result_72a = _get_policy_result(report, '7.2.a')
    result_76b = _get_policy_result(report, '7.6.b')

    assert result_72a is not None
    assert result_76b is not None
    assert result_72a['passed'] is True, "7.2.a should pass: implementation_status == Implemented"
    assert result_76b['passed'] is False, "7.6.b should fail: verification_status == Not Verified"


def test_TC_SYS_036_003_fully_verified_rcm_passes_both_policies(test_dhf_root, governance_dir):
    """
    TC-SYS-036-003: Fully verified RCM passes both ISO 14971 policies.

    An RCM with implementation_status=Implemented and verification_status=Verified
    should pass both policy 7.2.a and policy 7.6.b.

    @test_id: TC-SYS-036-003
    @links: SYS-005, SYS-012
    """
    _save_rcm(test_dhf_root, 'RCM-TEST-003',
              implementation_status='Implemented', verification_status='Verified')

    core = _make_core(test_dhf_root)
    report = core.check_compliance("ISO_14971", governance_dir)

    result_72a = _get_policy_result(report, '7.2.a')
    result_76b = _get_policy_result(report, '7.6.b')

    assert result_72a is not None
    assert result_76b is not None
    assert result_72a['passed'] is True, "7.2.a should pass: implementation_status == Implemented"
    assert result_76b['passed'] is True, "7.6.b should pass: verification_status == Verified"


def test_TC_SYS_036_004_schema_rejects_legacy_verified_implementation_status(test_dhf_root):
    """
    TC-SYS-036-004: Schema validation rejects the removed 'Verified' option on implementation_status.

    After CR-033, 'Verified' is no longer a valid value for implementation_status
    (it only accepts Planned/Implemented). Attempting to create an RCM via the
    adapter with implementation_status=Verified should raise a ValidationError.

    @test_id: TC-SYS-036-004
    @links: SYS-005, SYS-012
    """
    adapter = LocalDHFAdapter(test_dhf_root, auto_commit=False)

    with pytest.raises(ValidationError):
        adapter.create_item({
            'type': 'RCM',
            'title': 'Legacy RCM with old status',
            'content': 'Using removed Verified option',
            'control_type': 'Protective Measure',
            'implementation_status': 'Verified',
        })
