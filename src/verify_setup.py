import yaml
from app.schema import ProjectConfig, AtomicItem, SmartDocument, ExternalStub, VerificationStatus

def test_config_loading():
    with open('../DHF/config/project_config.yaml', 'r') as f:
        config_data = yaml.safe_load(f)
    
    config = ProjectConfig(**config_data)
    print("Config loaded successfully:")
    print(config.model_dump_json(indent=2))

def test_models():
    # Atomic Item
    req = AtomicItem(
        id="SRS-001",
        title="Login Requirement",
        content="The system shall allow users to login.",
        links=["SYS-001"],
        verification_status=VerificationStatus.PENDING
    )
    print("\nAtomic Item created:")
    print(req.model_dump_json(indent=2))

    # Smart Document
    plan = SmartDocument(
        id="PLAN-001",
        title="Verification Plan",
        content="# Verification Plan\n\nCoverage: {{ stats.coverage_pct }}%",
        frontmatter={"author": "John Doe"}
    )
    print("\nSmart Document created:")
    print(plan.model_dump_json(indent=2))

    # External Stub
    stub = ExternalStub(
        id="EXT-001",
        title="NMPA Cybersecurity Plan",
        location="http://sharepoint/docs/cybersec_plan.pdf",
        format="pdf",
        compliance_tags=["NMPA", "Cybersecurity"]
    )
    print("\nExternal Stub created:")
    print(stub.model_dump_json(indent=2))

if __name__ == "__main__":
    test_config_loading()
    test_models()
