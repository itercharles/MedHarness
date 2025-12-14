"""Simple verification script for defect tracking system."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from traceability.compliant_flow_core import CompliantFlowCore

def main():
    """Verify defect tracking functionality."""
    print("=" * 60)
    print("Defect Tracking System Verification")
    print("=" * 60)
    
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    print(f"\n1. Initializing CompliantFlowCore with DHF root: {dhf_root}")
    
    try:
        core = CompliantFlowCore(dhf_root)
        print("   ✓ Core initialized successfully")
        print(f"   ✓ Defect tracker initialized: {core.defect_tracker is not None}")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return False
    
    # List existing defects
    print("\n2. Listing existing defects in DHF...")
    try:
        defects = core.list_defects()
        print(f"   ✓ Found {len(defects)} defect(s)")
        for defect in defects:
            print(f"     - {defect['id']}: {defect['title']} [{defect['status']}]")
    except Exception as e:
        print(f"   ✗ Failed to list defects: {e}")
        return False
    
    # Test creating a new defect
    print("\n3. Testing defect creation...")
    try:
        test_defect = core.create_defect({
            "title": "Test defect from verification script",
            "description": "This is a test defect to verify the system works",
            "severity": "minor",
            "reported_by": "Verification Script"
        })
        print(f"   ✓ Created defect: {test_defect['id']}")
        print(f"     Title: {test_defect['title']}")
        print(f"     Severity: {test_defect['severity']}")
        print(f"     Status: {test_defect['status']}")
    except Exception as e:
        print(f"   ✗ Failed to create defect: {e}")
        return False
    
    # Test retrieving a defect
    print("\n4. Testing defect retrieval...")
    try:
        retrieved = core.get_defect(test_defect['id'])
        if retrieved:
            print(f"   ✓ Retrieved defect: {retrieved['id']}")
        else:
            print(f"   ✗ Failed to retrieve defect")
            return False
    except Exception as e:
        print(f"   ✗ Failed to retrieve defect: {e}")
        return False
    
    # Test filtering defects
    print("\n5. Testing defect filtering...")
    try:
        critical_defects = core.list_defects(severity="critical")
        print(f"   ✓ Found {len(critical_defects)} critical defect(s)")
        
        open_defects = core.list_defects(status="open")
        print(f"   ✓ Found {len(open_defects)} open defect(s)")
    except Exception as e:
        print(f"   ✗ Failed to filter defects: {e}")
        return False
    
    # Test workflow operations
    print("\n6. Testing workflow operations...")
    try:
        # Assign defect
        result = core.assign_defect(test_defect['id'], "Test Assignee", "Verification Script")
        print(f"   ✓ Assign: {result['message']}")
        
        # Start investigation
        result = core.start_defect_investigation(test_defect['id'], "Test Investigator")
        print(f"   ✓ Start investigation: {result['message']}")
        
        # Resolve defect
        result = core.resolve_defect(
            test_defect['id'],
            "Test root cause",
            "Test resolution",
            "Test Resolver"
        )
        print(f"   ✓ Resolve: {result['message']}")
        
        # Verify resolution
        result = core.verify_defect_resolution(
            test_defect['id'],
            "Test verification",
            "Test Verifier"
        )
        print(f"   ✓ Verify: {result['message']}")
        
        # Close defect
        result = core.close_defect(test_defect['id'], "Test Closer")
        print(f"   ✓ Close: {result['message']}")
        
    except Exception as e:
        print(f"   ✗ Workflow operation failed: {e}")
        return False
    
    # Final verification
    print("\n7. Final verification...")
    try:
        final_defect = core.get_defect(test_defect['id'])
        if final_defect['status'] == 'closed':
            print(f"   ✓ Defect successfully went through full lifecycle")
            print(f"     Final status: {final_defect['status']}")
        else:
            print(f"   ✗ Unexpected final status: {final_defect['status']}")
            return False
    except Exception as e:
        print(f"   ✗ Final verification failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All verification tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
