import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent
sys.path.append(str(backend_path))

from traceability.compliant_flow_core import CompliantFlowCore

def verify_relations():
    # Initialize core
    repo_root = backend_path.parent / "repo_root"
    core = CompliantFlowCore(repo_root)
    
    print(f"Loaded {len(core.graph.graph.nodes)} nodes")
    print(f"Loaded {len(core.graph.graph.edges)} edges")
    
    # Check edges
    valid_relations = {
        ('TC-SYS', 'SYS'): 'verifies',
        ('TC-SDS', 'SDS'): 'verifies',
        ('TC-CRS', 'CRS'): 'validates',
        ('RCM', 'RISK'): 'mitigates',
        ('SYS', 'CRS'): 'satisfies',
        ('SYS', 'RCM'): 'implements',
        ('SDS', 'SYS'): 'implements'
    }
    
    found_relations = 0
    passed = True
    
    for u, v, data in core.graph.graph.edges(data=True):
        edge_type = data.get('type')
        
        # Get prefixes
        def get_prefix(node_id):
            parts = node_id.split('-')
            if parts[0] == 'TC':
                return f"{parts[0]}-{parts[1]}"
            return parts[0]

        u_prefix = get_prefix(u)
        v_prefix = get_prefix(v)
        
        # Check if this edge matches a known relation pattern
        pair = (u_prefix, v_prefix)
        
        if pair in valid_relations:
            expected = valid_relations[pair]
            if edge_type == expected:
                print(f"[PASS] {u} -> {v}: {edge_type}")
                found_relations += 1
            else:
                print(f"[FAIL] {u} -> {v}: Expected {expected}, got {edge_type}")
                passed = False
        else:
             # Basic check that it is at least not 'links' if we expected something else, 
             # but here we just print what we found for info
             print(f"[INFO] {u} -> {v}: {edge_type}")

    if found_relations == 0:
        print("Warning: No specific relations found to verify. Ensure you have data.")
        
    if passed:
        print("SUCCESS: All checked relations matched configuration.")
    else:
        print("FAILURE: Some relations did not match configuration.")
        exit(1)

if __name__ == "__main__":
    verify_relations()
