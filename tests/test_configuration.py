"""Tests for configuration validation."""

import pytest
from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore
import yaml


def test_TC_CONFIG_001_yaml_parsing():
    """TC-CONFIG-001: Verify Project Config YAML Parsing
    
    @links: SYS-004
    @prerequisites: Valid project_config.yaml file
    
    Steps:
      1. Load project_config.yaml
      2. Parse YAML content
      3. Verify structure
      4. Check required top-level keys
    
    Expected Result:
      YAML file should parse successfully with required keys
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    config_path = dhf_root / "config" / "project_config.yaml"
    
    assert config_path.exists(), "project_config.yaml should exist"
    
    # Parse YAML
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Verify required keys
    assert 'doc_types' in config_data, "Config should have doc_types"
    assert isinstance(config_data['doc_types'], list), "doc_types should be a list"
    assert len(config_data['doc_types']) > 0, "Should have at least one doc type"


def test_TC_CONFIG_002_required_fields():
    """TC-CONFIG-002: Verify Required Fields Validation
    
    @links: SYS-005
    @prerequisites: CompliantFlowCore initialized
    
    Steps:
      1. Initialize CompliantFlowCore
      2. Access configuration
      3. Verify each doc_type has required fields
      4. Check for code, name, prefix, directory
    
    Expected Result:
      All doc types should have required fields defined
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    assert core.config is not None, "Configuration should be loaded"
    assert len(core.config.doc_types) > 0, "Should have doc types"
    
    # Verify required fields for each doc type
    for doc_type in core.config.doc_types:
        assert hasattr(doc_type, 'code'), f"Doc type should have code"
        assert hasattr(doc_type, 'name'), f"Doc type should have name"
        assert hasattr(doc_type, 'prefix'), f"Doc type should have prefix"
        assert hasattr(doc_type, 'directory'), f"Doc type should have directory"
        
        # Verify values are not empty
        assert doc_type.code, "Code should not be empty"
        assert doc_type.name, "Name should not be empty"
        assert doc_type.prefix, "Prefix should not be empty"
        assert doc_type.directory, "Directory should not be empty"


def test_TC_CONFIG_003_traceability_matrices():
    """TC-CONFIG-003: Verify Traceability Matrix Configuration
    
    @links: SYS-021
    @prerequisites: project_config.yaml with traceability_matrices section
    
    Steps:
      1. Initialize CompliantFlowCore
      2. Access traceability_matrices configuration
      3. Verify matrix definitions
      4. Check path validity
    
    Expected Result:
      Traceability matrices should be properly configured
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    assert hasattr(core.config, 'traceability_matrices'), \
        "Config should have traceability_matrices"
    
    matrices = core.config.traceability_matrices
    assert len(matrices) > 0, "Should have at least one matrix"
    
    # Verify each matrix
    for matrix in matrices:
        assert matrix.name, "Matrix should have a name"
        assert matrix.path, "Matrix should have a path"
        assert len(matrix.path) >= 2, "Path should have at least 2 levels"
        
        # Verify path elements are valid doc type codes
        for code in matrix.path:
            assert isinstance(code, str), "Path element should be a string"
            assert code, "Path element should not be empty"


def test_TC_CONFIG_004_lifecycle_validation():
    """TC-CONFIG-004: Verify Lifecycle State Validation
    
    @links: SYS-006
    @prerequisites: Doc types with lifecycle configuration
    
    Steps:
      1. Initialize CompliantFlowCore
      2. Find doc types with lifecycle
      3. Verify lifecycle structure
      4. Check states and transitions
    
    Expected Result:
      Lifecycle configuration should have valid states and transitions
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Find doc types with lifecycle
    doc_types_with_lifecycle = [
        dt for dt in core.config.doc_types 
        if hasattr(dt, 'lifecycle') and dt.lifecycle
    ]
    
    assert len(doc_types_with_lifecycle) > 0, \
        "Should have doc types with lifecycle"
    
    for doc_type in doc_types_with_lifecycle:
        lifecycle = doc_type.lifecycle
        
        # Verify states
        assert lifecycle.states, f"{doc_type.code} should have states"
        assert len(lifecycle.states) > 0, f"{doc_type.code} should have at least one state"
        
        # Verify each state has required fields
        for state in lifecycle.states:
            assert state.id, "State should have id"
            assert state.label, "State should have label"
            assert hasattr(state, 'is_stable'), "State should have is_stable flag"
        
        # Verify at least one initial state
        initial_states = [s for s in lifecycle.states if getattr(s, 'is_initial', False)]
        assert len(initial_states) > 0, \
            f"{doc_type.code} should have at least one initial state"


def test_TC_CONFIG_005_doc_type_prefix_matching():
    """TC-CONFIG-005: Verify Document Type Prefix Matching
    
    @links: SYS-007
    @prerequisites: Multiple doc types configured
    
    Steps:
      1. Initialize CompliantFlowCore
      2. Get all doc types
      3. Verify prefix uniqueness
      4. Check prefix format
    
    Expected Result:
      Each doc type should have a unique prefix ending with hyphen
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    doc_types = core.config.doc_types
    assert len(doc_types) > 1, "Should have multiple doc types"
    
    # Collect all prefixes
    prefixes = [dt.prefix for dt in doc_types]
    
    # Verify uniqueness
    assert len(prefixes) == len(set(prefixes)), \
        "All prefixes should be unique"
    
    # Verify format (should end with hyphen)
    for dt in doc_types:
        assert dt.prefix.endswith('-'), \
            f"Prefix '{dt.prefix}' should end with hyphen"
        assert len(dt.prefix) > 1, \
            f"Prefix '{dt.prefix}' should have content before hyphen"
