#!/usr/bin/env python3
"""
Migration script to create DHF requirement files from the complete requirements set.
"""

import yaml
from pathlib import Path

# Base directory
DHF_ITEMS = Path("/Users/chenwenliang/code/CompliantFlow/DHF/items")

# Use Cases
use_cases = [
    {
        "id": "UC-001",
        "title": "Manage Requirements",
        "content": "**Actor:** Requirements Engineer\n**Goal:** Create, update, and maintain requirements with proper review and approval",
        "status": "approved"
    },
    {
        "id": "UC-002",
        "title": "Verify Traceability",
        "content": "**Actor:** Quality Engineer\n**Goal:** Ensure complete traceability and identify gaps",
        "status": "approved"
    },
    {
        "id": "UC-003",
        "title": "Generate Specification Documents",
        "content": "**Actor:** Documentation Specialist\n**Goal:** Produce regulatory submission documents",
        "status": "approved"
    },
    {
        "id": "UC-004",
        "title": "Manage Change Requests",
        "content": "**Actor:** Change Control Board Member\n**Goal:** Assess impact of proposed changes and make approval decisions",
        "status": "approved"
    },
    {
        "id": "UC-005",
        "title": "Check Compliance Policies",
        "content": "**Actor:** Regulatory Affairs Specialist\n**Goal:** Validate DHF against regulatory requirements",
        "status": "approved"
    }
]

# Customer Requirements
customer_requirements = [
    {
        "id": "CRS-001",
        "title": "IEC 62304 Compliance",
        "content": "The system shall support IEC 62304 medical device software lifecycle processes including requirements management, traceability, verification, and configuration management.",
        "rationale": "Required for medical device regulatory approval",
        "stakeholder": "Regulatory Affairs",
        "priority": "Critical",
        "derives_from": ["UC-002", "UC-005"],
        "status": "approved"
    },
    {
        "id": "CRS-002",
        "title": "Complete Traceability",
        "content": "The system shall maintain complete traceability from user needs through requirements, design, implementation, and testing to demonstrate regulatory compliance.",
        "rationale": "FDA and EU MDR require traceability throughout product lifecycle",
        "stakeholder": "Quality Assurance",
        "priority": "Critical",
        "derives_from": ["UC-001", "UC-002"],
        "status": "approved"
    },
    {
        "id": "CRS-003",
        "title": "Complete Audit Trail",
        "content": "The system shall provide complete, tamper-evident audit trail of all changes to DHF items including who made changes, when, and why.",
        "rationale": "Required for 21 CFR Part 11 electronic records compliance",
        "stakeholder": "Quality Assurance",
        "priority": "Critical",
        "derives_from": ["UC-001"],
        "status": "approved"
    },
    {
        "id": "CRS-004",
        "title": "Automated Documentation",
        "content": "The system shall automatically generate specification documents in formats suitable for regulatory submission to reduce manual effort and errors.",
        "rationale": "Manual documentation is time-consuming and error-prone",
        "stakeholder": "Documentation Team",
        "priority": "High",
        "derives_from": ["UC-003"],
        "status": "approved"
    },
    {
        "id": "CRS-005",
        "title": "Usability",
        "content": "The system shall be easy to learn and use for engineers with minimal training.",
        "rationale": "User adoption depends on ease of use",
        "stakeholder": "Development Team",
        "priority": "High",
        "derives_from": ["UC-001"],
        "status": "approved"
    },
    {
        "id": "CRS-006",
        "title": "Configurable Workflows",
        "content": "The system shall allow customization of document types, workflows, and validation rules without code changes to adapt to different regulatory frameworks.",
        "rationale": "Different products and regions have different requirements",
        "stakeholder": "Process Owner",
        "priority": "Medium",
        "derives_from": ["UC-001", "UC-005"],
        "status": "approved"
    },
    {
        "id": "CRS-007",
        "title": "Portable DHF",
        "content": "The system shall store DHF in human-readable, version-controlled files that can be easily backed up, archived, and submitted to regulatory authorities.",
        "rationale": "DHF must be preserved for product lifetime (10+ years)",
        "stakeholder": "Quality Assurance",
        "priority": "High",
        "derives_from": ["UC-001"],
        "status": "approved"
    },
    {
        "id": "CRS-008",
        "title": "Automated Test Integration",
        "content": "The system shall integrate with automated test frameworks to show real-time test results and verification status for requirements.",
        "rationale": "Manual test tracking is error-prone and outdated",
        "stakeholder": "Test Engineering",
        "priority": "Medium",
        "derives_from": ["UC-002"],
        "status": "approved"
    },
    {
        "id": "CRS-009",
        "title": "Impact Analysis",
        "content": "The system shall automatically identify all items affected by a proposed change to support change control decisions.",
        "rationale": "Manual impact analysis is incomplete and time-consuming",
        "stakeholder": "Change Control Board",
        "priority": "High",
        "derives_from": ["UC-004"],
        "status": "approved"
    }
]

def create_yaml_file(directory: Path, item: dict):
    """Create a YAML file for an item."""
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / f"{item['id']}.yaml"
    
    with open(file_path, 'w') as f:
        yaml.dump(item, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"Created: {file_path}")

def main():
    print("Creating Use Case files...")
    uc_dir = DHF_ITEMS / "00_uc"
    for uc in use_cases:
        create_yaml_file(uc_dir, uc)
    
    print("\nCreating Customer Requirement files...")
    crs_dir = DHF_ITEMS / "01_req_crs"
    for crs in customer_requirements:
        create_yaml_file(crs_dir, crs)
    
    print("\nMigration script completed!")
    print(f"Created {len(use_cases)} Use Cases")
    print(f"Created {len(customer_requirements)} Customer Requirements")

if __name__ == "__main__":
    main()
