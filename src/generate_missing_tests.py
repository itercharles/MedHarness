
from pathlib import Path
import sys
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from traceability.compliant_flow_core import CompliantFlowCore

def generate_missing_tests():
    print("--- Generating Missing Test Cases ---\n")
    
    # Initialize Core
    dhf_root = Path(__file__).resolve().parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    items = core.get_all_items()
    
    # Map of requirement type to test directory and prefix
    config = {
        'CRS': {
            'dir': dhf_root / "items/06_tc_crs",
            'prefix': 'TC-CRS',
            'title_prefix': 'Validate'
        },
        'SYS': {
            'dir': dhf_root / "items/05_tc_sys",
            'prefix': 'TC-SYS',
            'title_prefix': 'Verify'
        },
        'SDS': {
            'dir': dhf_root / "items/07_tc_sds",
            'prefix': 'TC-SDS',
            'title_prefix': 'Unit Test'
        }
    }
    
    # 1. Identify all Requirements and existing Test Cases
    requirements = []
    test_cases = []
    
    for item in items:
        uid = item['id']
        prefix = uid.split('-')[0]
        
        if prefix in ['CRS', 'SYS', 'SDS']:
            requirements.append(item)
        elif prefix in ['TC']:
            test_cases.append(item)
            
    # 2. Map covered requirements
    covered_req_ids = set()
    for tc in test_cases:
        for link in tc.get('links', []):
            covered_req_ids.add(link)
            
    print(f"Total Requirements: {len(requirements)}")
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"Covered Requirements: {len(covered_req_ids)}")
    
    # 3. Generate missing TCs
    generated_count = 0
    
    for req in requirements:
        if req['id'] in covered_req_ids:
            continue
            
        req_id = req['id']
        req_type = req_id.split('-')[0]
        
        if req_type not in config:
            continue
            
        # Determine new TC ID
        # We try to match ID if possible: SYS-001 -> TC-SYS-001
        # If TC-SYS-001 exists (but points elsewhere? unlikely), we might skip or append
        # But for now, let's assume 1:1 naming is safe if we strictly base it on Req ID
        
        if req_type == 'SDS':
             # SDS-001 -> TC-SDS-001
             tc_id = f"TC-{req_id}"
        elif req_type == 'SYS':
             tc_id = f"TC-{req_id}"
        elif req_type == 'CRS':
             tc_id = f"TC-{req_id}"
             
        # Check if this ID already exists (maybe it exists but doesn't link to the req? unlikely)
        if any(t['id'] == tc_id for t in test_cases):
            print(f"Skipping {req_id}: {tc_id} already exists but doesn't link to it.")
            continue
            
        print(f"Generating {tc_id} for {req_id}...")
        
        cfg = config[req_type]
        cfg['dir'].mkdir(parents=True, exist_ok=True)
        
        new_tc = {
            'id': tc_id,
            'title': f"{cfg['title_prefix']} {req.get('title', 'Requirement')}",
            'content': f"Test case to verify: {req.get('content', '')}",
            'links': [req_id],
            'verification_status': 'PENDING'
        }
        
        file_path = cfg['dir'] / f"{tc_id}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(new_tc, f, default_flow_style=False, sort_keys=False)
            
        generated_count += 1
        
    print(f"\nGenerated {generated_count} new test cases.")

if __name__ == "__main__":
    generate_missing_tests()
