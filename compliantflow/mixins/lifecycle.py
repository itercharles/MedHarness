"""Lifecycle mixin — delegates to traceability/lifecycle_methods.py."""

from compliantflow.traceability.lifecycle_methods import (
    get_available_transitions,
    get_state_info,
    _validate_criteria,
    execute_transition,
    is_item_editable,
    get_initial_state,
)


class _LifecycleMixin:
    get_available_transitions = get_available_transitions
    get_state_info            = get_state_info
    _validate_criteria        = _validate_criteria
    execute_transition        = execute_transition
    is_item_editable          = is_item_editable
    get_initial_state         = get_initial_state
