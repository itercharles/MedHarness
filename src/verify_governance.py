import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent
sys.path.append(str(src_path))

from traceability.compliant_flow_core import CompliantFlowCore

def main():
    dhf_root = src_path.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # 1. Check IEC_62304 (Regulation)
    print("\n--- Checking IEC_62304 (Regulation) ---")
    report_reg = core.check_compliance("IEC_62304")
    if report_reg:
        print(f"Score: {report_reg['score']}%")
        for res in report_reg['results']:
            status = "PASS" if res['passed'] else "FAIL"
            print(f"[{status}] {res['policy_id']}")
    else:
        print("Failed to load IEC_62304")

    # 2. Check SOP_001 (Procedure)
    print("\n--- Checking SOP_001 (Procedure) ---")
    report_sop = core.check_compliance("SOP_001")
    if report_sop:
        print(f"Score: {report_sop['score']}%")
        for res in report_sop['results']:
            status = "PASS" if res['passed'] else "FAIL"
            print(f"[{status}] {res['policy_id']}")
            if not res['passed']:
                print(f"    Details: {res['details']}")
    else:
        print("Failed to load SOP_001")

    # 3. Check IEC_82304_1 (Standard)
    print("\n--- Checking IEC_82304_1 (Standard) ---")
    report_82304 = core.check_compliance("IEC_82304_1")
    if report_82304:
        print(f"Score: {report_82304['score']}%")
        for res in report_82304['results']:
            status = "PASS" if res['passed'] else "FAIL"
            print(f"[{status}] {res['policy_id']}")
    else:
        print("Failed to load IEC_82304_1")

if __name__ == "__main__":
    main()
