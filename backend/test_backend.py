from fastapi.testclient import TestClient
from app.main import app
import os
import shutil

client = TestClient(app)

def setup_test_data():
    # Create dummy data in repo_root for testing
    # Assuming we are in backend dir
    repo_root = "../repo_root"
    
    # Create SRS
    srs_dir = os.path.join(repo_root, "specifications/03_software_reqs")
    os.makedirs(srs_dir, exist_ok=True)
    with open(os.path.join(srs_dir, "SRS-001.yaml"), "w") as f:
        f.write("""
id: SRS-001
title: Login
content: User shall login.
links: []
verification_status: PENDING
""")

    # Create Test
    test_dir = os.path.join(repo_root, "specifications/05_test_cases")
    os.makedirs(test_dir, exist_ok=True)
    with open(os.path.join(test_dir, "TC-VER-001.yaml"), "w") as f:
        f.write("""
id: TC-VER-001
title: Verify Login
content: Test login.
links: ["SRS-001"]
verification_status: PASS
""")

def test_api():
    setup_test_data()
    
    # Test Items
    response = client.get("/api/items")
    assert response.status_code == 200
    items = response.json()
    print(f"Items found: {len(items)}")
    assert len(items) >= 2
    
    # Test Graph Analysis
    response = client.get("/api/graph/analyze")
    assert response.status_code == 200
    stats = response.json()
    print("Graph Stats:", stats)
    assert stats["node_count"] >= 2
    
    # Test Coverage
    response = client.get("/api/graph/coverage")
    assert response.status_code == 200
    coverage = response.json()
    print("Coverage:", coverage)
    assert coverage["SRS"] == 100.0

if __name__ == "__main__":
    test_api()
