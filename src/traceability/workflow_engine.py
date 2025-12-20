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
        self.states = {s['id']: s for s in self.lifecycle.get('states', [])}
        self.transitions = self._build_transition_map()
    
    def _build_transition_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build a map of from_state -> list of possible transitions."""
        transition_map = {}
        
        for transition in self.lifecycle.get('transitions', []):
            from_state = transition['from']
            if from_state not in transition_map:
                transition_map[from_state] = []
            transition_map[from_state].append(transition)
        
        return transition_map
    
    def get_initial_state(self) -> str:
        """Get the initial state for new items."""
        for state in self.lifecycle.get('states', []):
            if state.get('is_initial', False):
                return state['id']
        
        # No initial state found - this is a configuration error
        raise ValueError(
            f"No initial state defined in lifecycle for {self.doc_type_config.get('name', 'document type')}. "
            "Please add 'is_initial: true' to one of the states."
        )
    
    def get_available_transitions(self, current_state: str) -> List[Dict[str, Any]]:
        """Get all possible transitions from the current state."""
        return self.transitions.get(current_state, [])
    
    def check_transition_criteria(
        self,
        item: Dict[str, Any],
        transition: Dict[str, Any]
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Check if all criteria for a transition are met.
        
        Returns:
            Tuple of (all_criteria_met, list_of_criterion_results)
        """
        criteria = transition.get('criteria', [])
        results = []
        all_required_pass = True
        
        for criterion in criteria:
            passed, message = self._check_single_criterion(item, criterion)
            
            result = {
                'id': criterion['id'],
                'name': criterion['name'],
                'description': criterion.get('description', ''),
                'passed': passed,
                'message': message,
                'check_type': criterion['check_type'],
                'required': criterion.get('required', True)
            }
            results.append(result)
            
            if criterion.get('required', True) and not passed:
                all_required_pass = False
        
        return all_required_pass, results
    
    def _check_single_criterion(
        self,
        item: Dict[str, Any],
        criterion: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Check a single criterion against the item.
        
        Returns:
            Tuple of (passed, message)
        """
        check_type = criterion['check_type']
        
        if check_type == 'field_not_empty':
            field = criterion['field']
            value = item.get(field)
            if value:
                return True, f"{field} is set"
            return False, f"{field} is not set"
        
        elif check_type == 'linked_items_approved':
            linked_type = criterion['linked_type']
            required_status = criterion.get('required_status')
            
            if not required_status:
                raise ValueError(
                    f"Criterion '{criterion.get('id')}' with check_type 'linked_items_approved' "
                    "must specify 'required_status' field"
                )
            
            links = item.get('links', [])
            
            if not links:
                return False, f"No linked {linked_type} items found"
            
            # Filter links to only the specified type
            type_links = [link for link in links if link.startswith(linked_type)]
            
            if not type_links:
                return False, f"No linked {linked_type} items found"
            
            # Check each linked item has the required status
            not_matching = []
            for link_id in type_links:
                linked_item = self.core.get_item(link_id)
                if not linked_item:
                    not_matching.append(f"{link_id} (not found)")
                elif linked_item.get('status') != required_status:
                    status = linked_item.get('status', 'unknown')
                    not_matching.append(f"{link_id} ({status})")
            
            if not_matching:
                return False, f"Linked {linked_type} not in '{required_status}' status: {', '.join(not_matching)}"
            
            return True, f"All {len(type_links)} linked {linked_type} items are '{required_status}'"
        
        elif check_type == 'manual':
            criterion_id = criterion['id']
            manual_verifications = item.get('manual_verifications', {})
            
            if criterion_id in manual_verifications:
                verification = manual_verifications[criterion_id]
                verified_by = verification.get('verified_by', 'Unknown')
                return True, f"Verified by {verified_by}"
            else:
                return False, "Manual verification required"
        
        # Unknown check type
        return True, f"Check type '{check_type}' not implemented"
    
    def perform_transition(
        self,
        item: Dict[str, Any],
        transition: Dict[str, Any],
        transition_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform a state transition on an item.
        
        Args:
            item: The item to transition
            transition: The transition configuration
            transition_metadata: Optional metadata (e.g., approved_by, approved_date)
        
        Returns:
            Updated item
        """
        # Update status
        item['status'] = transition['to']
        
        # Add transition metadata if provided
        if transition_metadata:
            for key, value in transition_metadata.items():
                item[key] = value
        
        # History tracking removed - using Git history instead
        # if 'history' not in item:
        #     item['history'] = []
        # 
        # item['history'].append({
        #     'from': transition['from'],
        #     'to': transition['to'],
        #     'timestamp': transition_metadata.get('timestamp') if transition_metadata else None,
        #     'metadata': transition_metadata or {}
        # })
        
        return item
    
    def get_state_info(self, state_id: str) -> Dict[str, Any]:
        """Get information about a specific state."""
        return self.states.get(state_id, {
            'id': state_id,
            'label': state_id.capitalize(),
            'color': 'secondary',
            'icon': '📄'
        })
