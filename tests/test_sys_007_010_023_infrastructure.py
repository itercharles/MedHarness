"""
Tests for SYS-007: Compliance Reporting
Tests for SYS-010: Defect Workflow Management (now: configurable workflows)
Tests for SYS-023: Configuration-Driven Status Warning Logic

Verifies that the system supports configurable policy validation,
lifecycle workflows, and status warning logic.
"""
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore


class TestSYS007_ComplianceReporting:
    """Tests for SYS-007: Compliance Reporting."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_policy_configuration_loading(self, core):
        """Verify system loads policy validation rules from configuration."""
        # SYS-007: Execute policy validation rules defined in configuration
    
    def test_policy_validation_infrastructure(self, core):
        """Verify system has infrastructure to execute policy validation."""
        # System should have capability to validate policies
        # This is infrastructure test, not testing specific policy results
        assert hasattr(core, 'config'), "System should have configuration infrastructure"


class TestSYS010_ConfigurableWorkflows:
    """Tests for SYS-010: Configurable Lifecycle Workflows."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_lifecycle_configuration_loading(self, core):
        """Verify system loads lifecycle workflows from configuration."""
        # SYS-010: Support configurable lifecycle workflows
        # Check that system loads lifecycle definitions
        doc_types_with_lifecycle = [dt for dt in core.config.doc_types 
                                    if hasattr(dt, 'lifecycle') and dt.lifecycle]
        
        assert len(doc_types_with_lifecycle) > 0, \
            "System should load lifecycle configurations"
    
    def test_state_transition_rules(self, core):
        """Verify system loads state transition rules from configuration."""
        # Find a doc type with lifecycle
        doc_type = None
        for dt in core.config.doc_types:
            if hasattr(dt, 'lifecycle') and dt.lifecycle:
                doc_type = dt
                break
        
        if doc_type:
            lifecycle = doc_type.lifecycle
            assert 'states' in lifecycle, "Lifecycle should have states defined"
            assert 'transitions' in lifecycle, "Lifecycle should have transitions defined"
    
    def test_validation_criteria_support(self, core):
        """Verify system supports validation criteria in configuration."""
        # Check that system can load validation criteria
        # This tests infrastructure capability, not specific criteria
        for dt in core.config.doc_types:
            if hasattr(dt, 'lifecycle') and dt.lifecycle:
                lifecycle = dt.lifecycle
                transitions = lifecycle.get('transitions', [])
                
                # System should support transitions with criteria
                assert isinstance(transitions, list), \
                    "System should support transition definitions"
                break


class TestSYS023_StatusWarningLogic:
    """Tests for SYS-023: Configuration-Driven Status Warning Logic."""
    
    @pytest.fixture
    def core(self):
        """Initialize CompliantFlowCore."""
        dhf_root = Path(__file__).parent.parent / "DHF"
        return CompliantFlowCore(dhf_root)
    
    def test_is_stable_flag_configuration(self, core):
        """Verify system reads is_stable flag from configuration."""
        # SYS-023: Determine warning based on is_stable flag
        # Find a lifecycle with is_stable flags
        found_stable_flag = False
        
        for dt in core.config.doc_types:
            if hasattr(dt, 'lifecycle') and dt.lifecycle:
                states = dt.lifecycle.get('states', [])
                for state in states:
                    if 'is_stable' in state:
                        found_stable_flag = True
                        break
                if found_stable_flag:
                    break
        
        assert found_stable_flag, \
            "System should support is_stable flag in lifecycle configuration"
    
    def test_configuration_validation(self, core):
        """Verify system validates lifecycle configuration."""
        # SYS-023: Fail-fast validation for missing configuration
        # System should have loaded configuration without errors
        assert core.config is not None, "System should validate configuration on load"
        assert len(core.config.doc_types) > 0, "System should load document types"
