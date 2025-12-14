"""Verify defect tracking requirements and test cases with proper hierarchy."""

from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore

# Initialize core
dhf_root = Path(__file__).parent.parent / "DHF"
core = CompliantFlowCore(dhf_root)

# Get all items
items = core.get_all_items()

print("="*70)
print("DEFECT TRACKING REQUIREMENTS AND TEST CASES - HIERARCHICAL VIEW")
print("="*70)

# Level 1: Customer Requirements
crs_defect = [i for i in items if i['id'] == 'CRS-005']
print("\n📋 LEVEL 1: Customer Requirements")
for req in crs_defect:
    print(f"  ✓ {req['id']}: {req['title']}")
    print(f"    Source: {req.get('source', 'N/A')}")

# Level 2: System Requirements
sys_defect = [i for i in items if i['id'].startswith('SYS-') and i['id'] in [f'SYS-{n:03d}' for n in range(9, 16)]]
print("\n📋 LEVEL 2: System Requirements")
for req in sorted(sys_defect, key=lambda x: x['id']):
    links = req.get('links', [])
    status = req.get('verification_status', 'N/A')
    print(f"  ✓ {req['id']}: {req['title']}")
    print(f"    Links: {links}, Status: {status}")

# Level 3: Software Design Specifications
sds_defect = [i for i in items if i['id'].startswith('SDS-DEF-')]
print("\n📋 LEVEL 3: Software Design Specifications")
for req in sorted(sds_defect, key=lambda x: x['id']):
    links = req.get('links', [])
    component = req.get('component', 'N/A')
    print(f"  ✓ {req['id']}: {req['title']}")
    print(f"    Component: {component}, Links: {links}")

# Test Cases - Customer Validation
tc_crs = [i for i in items if i['id'].startswith('TC-CRS-005')]
print("\n🧪 CUSTOMER VALIDATION TESTS")
for tc in sorted(tc_crs, key=lambda x: x['id']):
    links = tc.get('links', [])
    status = tc.get('verification_status', 'N/A')
    print(f"  ✓ {tc['id']}: {tc['title']}")
    print(f"    Validates: {links}, Status: {status}")

# Test Cases - System Level
tc_sys = [i for i in items if i['id'].startswith('TC-SYS-') and any(i['id'].startswith(f'TC-SYS-{n:03d}') for n in range(9, 16))]
print("\n🧪 SYSTEM LEVEL TESTS")
for tc in sorted(tc_sys, key=lambda x: x['id']):
    links = tc.get('links', [])
    status = tc.get('verification_status', 'N/A')
    print(f"  ✓ {tc['id']}: {tc['title']}")
    print(f"    Verifies: {links}, Status: {status}")

# Test Cases - Design Level
tc_sds = [i for i in items if i['id'].startswith('TC-SDS-DEF-')]
print("\n🧪 DESIGN LEVEL TESTS")
for tc in sorted(tc_sds, key=lambda x: x['id']):
    links = tc.get('links', [])
    status = tc.get('verification_status', 'N/A')
    print(f"  ✓ {tc['id']}: {tc['title']}")
    print(f"    Verifies: {links}, Status: {status}")

# Traceability Matrix
print("\n" + "="*70)
print("TRACEABILITY MATRIX")
print("="*70)

print("\n🔗 CRS-005 → System Requirements:")
for req in sorted(sys_defect, key=lambda x: x['id']):
    if 'CRS-005' in req.get('links', []):
        print(f"  → {req['id']}: {req['title']}")

print("\n🔗 System Requirements → SDS:")
for sys_req in sorted(sys_defect, key=lambda x: x['id']):
    linked_sds = [s for s in sds_defect if sys_req['id'] in s.get('links', [])]
    if linked_sds:
        print(f"\n  {sys_req['id']} → Design Specs:")
        for sds in linked_sds:
            print(f"    → {sds['id']}: {sds['title']}")

print("\n🔗 Requirements → Tests:")
all_reqs = crs_defect + sys_defect + sds_defect
all_tests = tc_crs + tc_sys + tc_sds

for req in sorted(all_reqs, key=lambda x: x['id']):
    linked_tests = [t for t in all_tests if req['id'] in t.get('links', [])]
    if linked_tests:
        print(f"\n  {req['id']} → Tests:")
        for test in sorted(linked_tests, key=lambda x: x['id']):
            print(f"    → {test['id']}: {test['title']}")

# Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"Customer Requirements (CRS):     {len(crs_defect)}")
print(f"System Requirements (SYS):       {len(sys_defect)}")
print(f"Design Specs (SDS):              {len(sds_defect)}")
print(f"Customer Validation Tests:       {len(tc_crs)}")
print(f"System Tests:                    {len(tc_sys)}")
print(f"Design Tests:                    {len(tc_sds)}")
print(f"\nTotal Requirements:              {len(all_reqs)}")
print(f"Total Test Cases:                {len(all_tests)}")

# Coverage analysis
crs_with_tests = len([r for r in crs_defect if any(r['id'] in t.get('links', []) for t in all_tests)])
sys_with_tests = len([r for r in sys_defect if any(r['id'] in t.get('links', []) for t in all_tests)])
sds_with_tests = len([r for r in sds_defect if any(r['id'] in t.get('links', []) for t in all_tests)])

print(f"\nTest Coverage:")
print(f"  CRS: {crs_with_tests}/{len(crs_defect)} ({100*crs_with_tests//len(crs_defect) if crs_defect else 0}%)")
print(f"  SYS: {sys_with_tests}/{len(sys_defect)} ({100*sys_with_tests//len(sys_defect) if sys_defect else 0}%)")
print(f"  SDS: {sds_with_tests}/{len(sds_defect)} ({100*sds_with_tests//len(sds_defect) if sds_defect else 0}%)")
print(f"\n✅ All requirements have test coverage: {crs_with_tests + sys_with_tests + sds_with_tests == len(all_reqs)}")
