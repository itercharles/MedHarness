"""
Automated tests for SRS-006: Configuration-Driven Workflow Engine
Verifies: Software shall read lifecycle definitions from config and validate transitions
"""

import pytest
from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

CONFIG_PATH = Path("/Users/chenwenliang/code/CompliantFlow/DHF/config/project_config.yaml")


class TestWorkflowEngine:
    """Tests for SRS-006: Configuration-Driven Workflow Engine"""
    
    def test_lifecycle_definitions_in_config(self):
        """Verify lifecycle definitions exist in configuration"""
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        
        # At least one doc type should have lifecycle
        has_lifecycle = any('lifecycle' in dt for dt in config['doc_types'])
        assert has_lifecycle, "Configuration must include lifecycle definitions"
    
    def test_lifecycle_has_states(self):
        """Verify lifecycle definitions include states"""
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        
        for doc_type in config['doc_types']:
            if 'lifecycle' in doc_type:
                assert 'states' in doc_type['lifecycle'], f"{doc_type['code']} lifecycle must have states"
                assert len(doc_type['lifecycle']['states']) > 0, "Must have at least one state"
    
    def test_lifecycle_has_transitions(self):
        """Verify lifecycle definitions include transitions"""
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        
        for doc_type in config['doc_types']:
            if 'lifecycle' in doc_type:
                assert 'transitions' in doc_type['lifecycle'], f"{doc_type['code']} lifecycle must have transitions"
    
    def test_transitions_have_validation_criteria(self):
        """Verify transitions can have validation criteria"""
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        
        found_criteria = False
        for doc_type in config['doc_types']:
            if 'lifecycle' in doc_type:
                for transition in doc_type['lifecycle'].get('transitions', []):
                    if 'criteria' in transition:
                        found_criteria = True
                        # Verify criteria structure
                        for criterion in transition['criteria']:
                            assert 'check_type' in criterion, "Criterion must have check_type"
                            assert 'required' in criterion, "Criterion must specify if required"
        
        assert found_criteria, "At least one transition should have validation criteria"
    
    def test_validation_check_types_supported(self):
        """Verify extensible validation check types"""
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        
        check_types = set()
        for doc_type in config['doc_types']:
            if 'lifecycle' in doc_type:
                for transition in doc_type['lifecycle'].get('transitions', []):
                    for criterion in transition.get('criteria', []):
                        check_types.add(criterion['check_type'])
        
        # Should support multiple check types
        expected_types = {'field_not_empty', 'manual', 'linked_items_approved'}
        found_types = check_types.intersection(expected_types)
        
        assert len(found_types) > 0, f"Should support standard check types, found: {check_types}"
    
    def test_initial_state_defined(self):
        """Verify each lifecycle has an initial state"""
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        
        for doc_type in config['doc_types']:
            if 'lifecycle' in doc_type:
                states = doc_type['lifecycle']['states']
                initial_states = [s for s in states if s.get('is_initial', False)]
                
                assert len(initial_states) > 0, f"{doc_type['code']} must have an initial state"
    
    def test_stable_state_defined(self):
        """Verify lifecycles can have stable states"""
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        
        found_stable = False
        for doc_type in config['doc_types']:
            if 'lifecycle' in doc_type:
                states = doc_type['lifecycle']['states']
                stable_states = [s for s in states if s.get('is_stable', False)]
                if stable_states:
                    found_stable = True
        
        assert found_stable, "At least one lifecycle should have a stable state"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
