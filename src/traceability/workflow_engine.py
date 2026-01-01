"""Dynamic workflow engine - reads lifecycle and criteria from project_config.yaml"""

from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path


class DynamicWorkflowEngine:
    """
    Universal workflow engine that reads lifecycle states and transition criteria
    from project configuration instead of hardcoded logic.
    """
    
    def __init__(self, doc_type_config: Dict[str, Any], core: Any):
        """
        Initialize workflow engine for a specific doc type.
        
        Args:
            doc_type_config: Doc type configuration from project_config.yaml
            core: CompliantFlowCore instance
        """
        self.doc_type_config = doc_type_config
        self.core = core
        self.lifecycle = doc_type_config.get('lifecycle', {})
        # States now come from global_lifecycle, not per-doc-type
        self.transitions = self._build_transition_map()
    
    def _build_transition_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build a map of from_state -> list of possible transitions."""
        transition_map = {}
        
        for transition in self.lifecycle.get('transitions', []):
            from_states = transition.get('from_states', [])
            to_state = transition.get('to_state')
            
            # Handle each from_state
            for from_state in from_states:
                if from_state not in transition_map:
                    transition_map[from_state] = []
                
                # Add transition with backward-compatible format
                transition_map[from_state].append({
                    'from': from_state,  # Backward compat
                    'to': to_state,      # Backward compat
                    'to_state': to_state,
                    'label': self._get_action_label(to_state),
                    'criteria': transition.get('criteria', [])
                })
        
        return transition_map
    
    def _get_action_label(self, to_state: str) -> str:
        """Get action label from global lifecycle."""
        if not self.core.config.global_lifecycle:
            return to_state.title()
        
        for state in self.core.config.global_lifecycle.states:
            if state.id == to_state:
                return state.action_label or state.label
        
        return to_state.title()
    
    def get_initial_state(self) -> str:
        """Get the initial state for new items."""
        # Find transition from null
        for transition in self.lifecycle.get('transitions', []):
            from_states = transition.get('from_states', [])
            if None in from_states or 'null' in from_states:
                return transition['to_state']
        
        # No initial state found - configuration error
        raise ValueError(
            f"No initial state defined in lifecycle for {self.doc_type_config.get('name', 'document type')}. "
            "Please add a transition with 'from_states: [null]'."
        )
    
    def get_available_transitions(self, current_state: str) -> List[Dict[str, Any]]:
        """Get all possible transitions from the current state."""
        return self.transitions.get(current_state, [])
    
    def get_state_info(self, state_id: str) -> Dict[str, Any]:
        """Get information about a specific state from global lifecycle."""
        if not self.core.config.global_lifecycle:
            return {
                'id': state_id,
                'label': state_id.capitalize(),
                'color': 'secondary',
                'icon': '📄'
            }
        
        for state in self.core.config.global_lifecycle.states:
            if state.id == state_id:
                return {
                    'id': state.id,
                    'label': state.label,
                    'color': state.color,
                    'icon': state.icon,
                    'is_stable': state.is_stable
                }
        
        # State not found in global lifecycle
        return {
            'id': state_id,
            'label': state_id.capitalize(),
            'color': 'secondary',
            'icon': '📄'
        }
