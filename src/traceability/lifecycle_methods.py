"""Lifecycle management methods for CompliantFlowCore."""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


def get_available_transitions(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get available transitions for an item based on its current status.
    
    Args:
        item: Item dictionary with 'id' and 'status' fields
        
    Returns:
        List of available transitions with format:
        [
            {
                'to_state': 'approved',
                'action_label': 'Approve',
                'criteria': [...],
                'can_transition': True/False,
                'blocking_criteria': [...]
            }
        ]
    """
    doc_type_code = item['id'].split('-')[0]
    doc_type = self.config.get_doc_type(doc_type_code)
    
    if not doc_type or not doc_type.lifecycle:
        return []
    
    current_status = item.get('status')
    transitions = doc_type.lifecycle.get('transitions', [])
    available = []
    
    for transition in transitions:
        from_states = transition.get('from_states', [])
        
        # Check if current status matches from_states
        if current_status in from_states or (current_status is None and None in from_states):
            to_state = transition['to_state']
            
            # Get state info from global lifecycle
            try:
                state_info = self.get_state_info(to_state)
            except ValueError as e:
                # State not found in global lifecycle - skip this transition
                print(f"Warning: {e}")
                continue
            
            # Validate criteria
            can_transition, blocking = self._validate_criteria(
                item, 
                transition.get('criteria', [])
            )
            
            available.append({
                'to_state': to_state,
                'action_label': state_info.get('action_label', to_state.title()),
                'icon': state_info.get('icon'),
                'color': state_info.get('color'),
                'criteria': transition.get('criteria', []),
                'can_transition': can_transition,
                'blocking_criteria': blocking
            })
    
    return available


def get_state_info(self, state_id: str) -> Dict[str, Any]:
    """Get information about a specific state from global lifecycle."""
    if self.config.global_lifecycle:
        for state in self.config.global_lifecycle.states:
            if state.id == state_id:
                return {
                    'id': state.id,
                    'label': state.label,
                    'action_label': state.action_label or state.label,
                    'icon': state.icon,
                    'color': state.color,
                    'is_stable': state.is_stable
                }
    
    # Valid state not found
    raise ValueError(f"State '{state_id}' not found in global lifecycle configuration.")


def _validate_criteria(
    self, 
    item: Dict[str, Any], 
    criteria: List[Dict[str, Any]]
) -> Tuple[bool, List[str]]:
    """
    Validate transition criteria.
    
    Returns:
        (can_transition, blocking_criteria_ids)
    """
    blocking = []
    
    for criterion in criteria:
        if not criterion.get('required', False):
            continue
        
        check_type = criterion.get('check_type')
        
        if check_type == 'field_not_empty':
            field = criterion.get('field')
            if not item.get(field):
                blocking.append(criterion['id'])
        
        elif check_type == 'relationship_field':
            field = criterion.get('field')
            if not item.get(field) or len(item.get(field, [])) == 0:
                blocking.append(criterion['id'])
    
    return (len(blocking) == 0, blocking)


def execute_transition(
    self,
    item_id: str,
    to_state: str,
    performed_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a state transition with automatic audit trail.
    
    Args:
        item_id: Item ID
        to_state: Target state
        performed_by: User performing the transition
        
    Returns:
        Updated item dictionary
        
    Raises:
        ValueError: If transition is not allowed or validation fails
    """
    # Load item
    item = self.get_item(item_id)
    if not item:
        raise ValueError(f"Item {item_id} not found")
    
    # Get available transitions
    available = self.get_available_transitions(item)
    
    # Find the requested transition
    transition = None
    for t in available:
        if t['to_state'] == to_state:
            transition = t
            break
    
    if not transition:
        raise ValueError(
            f"Transition to {to_state} not allowed from current state {item.get('status')}"
        )
    
    # Check if transition is valid
    if not transition['can_transition']:
        blocking = ', '.join(transition['blocking_criteria'])
        raise ValueError(
            f"Cannot transition: blocking criteria not met: {blocking}"
        )
    
    # Get state info
    state_info = self.get_state_info(to_state)
    
    # Update status
    item['status'] = to_state
    
    # Save item
    self.update_item(item_id, item)
    
    return item


def is_item_editable(self, item: Dict[str, Any]) -> bool:
    """
    Check if an item is editable based on its status.
    
    Args:
        item: Item dictionary
        
    Returns:
        True if item can be edited, False if in stable state
    """
    status = item.get('status')
    if not status:
        return True
    
    state_info = self.get_state_info(status)
    return not state_info.get('is_stable', False)


def get_initial_state(self, doc_type_code: str) -> Optional[str]:
    """
    Get the initial state for a document type.
    
    Args:
        doc_type_code: Document type code (e.g., 'SRS')
        
    Returns:
        Initial state ID or None
    """
    doc_type = self.config.get_doc_type(doc_type_code)
    
    if not doc_type or not doc_type.lifecycle:
        return None
    
    transitions = doc_type.lifecycle.get('transitions', [])
    
    # Find transition from null
    for transition in transitions:
        from_states = transition.get('from_states', [])
        if None in from_states or 'null' in from_states:
            return transition['to_state']
    
    return None
