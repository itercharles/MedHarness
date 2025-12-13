from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

def test_audit():
    # We rely on the data created by test_backend.py
    # SRS-001 is an orphan (no SYS parent).
    # No stubs exist.
    
    response = client.post("/api/audit/run")
    assert response.status_code == 200
    violations = response.json()
    print("Violations found:", len(violations))
    for v in violations:
        print(f"- [{v['severity']}] {v['message']}")
        
    # Expect at least:
    # 1. Orphan error for SRS-001
    # 2. Missing stub warnings for NMPA/Cybersecurity
    
    orphan_errors = [v for v in violations if "Orphan" in v['message']]
    stub_warnings = [v for v in violations if "Missing required external document" in v['message']]
    
    assert len(orphan_errors) >= 1
    assert len(stub_warnings) >= 2

if __name__ == "__main__":
    test_audit()
