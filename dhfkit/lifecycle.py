"""Lifecycle engine for DHF items.

Pure functions that operate on ProjectConfig and item dicts.
No dependency on MedHarness.
"""

from typing import Any, Dict, List, Optional, Tuple

from dhfkit.models.config import ProjectConfig


def get_state_info(config: ProjectConfig, state_id: str) -> Dict[str, Any]:
    """Return metadata for a global lifecycle state.

    Raises ValueError if the state is not found.
    """
    if config.global_lifecycle:
        for state in config.global_lifecycle.states:
            if state.id == state_id:
                return {
                    "id": state.id,
                    "label": state.label,
                    "action_label": state.action_label or state.label,
                    "icon": state.icon,
                    "color": state.color,
                    "is_stable": state.is_stable,
                }
    raise ValueError(f"State '{state_id}' not found in global lifecycle configuration.")


def get_initial_state(config: ProjectConfig, doc_type_code: str) -> Optional[str]:
    """Return the initial lifecycle state for a doc type code, or None."""
    dt = config.get_doc_type(doc_type_code)
    if not dt or not dt.lifecycle:
        return None
    for t in dt.lifecycle.get("transitions", []):
        if None in t.get("from_states", []) or "null" in t.get("from_states", []):
            return t["to_state"]
    return None


def is_stable(config: ProjectConfig, status: str) -> bool:
    """Return True if *status* is a stable (locked) state."""
    try:
        return get_state_info(config, status).get("is_stable", False)
    except ValueError:
        return False


def _validate_criteria(
    item: Dict[str, Any],
    criteria: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """Check transition criteria against an item dict.

    Returns (can_transition, list_of_blocking_criterion_ids).
    """
    blocking = []
    for criterion in criteria:
        if not criterion.get("required", False):
            continue
        check_type = criterion.get("check_type")
        field = criterion.get("field")
        if check_type == "field_not_empty":
            if not item.get(field):
                blocking.append(criterion["id"])
        elif check_type == "relationship_field":
            if not item.get(field):
                blocking.append(criterion["id"])
    return (len(blocking) == 0, blocking)


def get_available_transitions(
    config: ProjectConfig,
    item: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Return the list of allowed transitions from the item's current state."""
    doc_type_code = item["id"].split("-")[0]
    dt = config.get_doc_type_by_prefix(doc_type_code + "-")
    if not dt or not dt.lifecycle:
        return []

    current_status = item.get("status")
    available = []
    for transition in dt.lifecycle.get("transitions", []):
        from_states = transition.get("from_states", [])
        if current_status not in from_states and not (
            current_status is None and None in from_states
        ):
            continue

        to_state = transition["to_state"]
        try:
            state_info = get_state_info(config, to_state)
        except ValueError:
            continue

        can_transition, blocking = _validate_criteria(
            item, transition.get("criteria", [])
        )
        available.append({
            "to_state": to_state,
            "action_label": state_info.get("action_label", to_state.title()),
            "icon": state_info.get("icon"),
            "color": state_info.get("color"),
            "criteria": transition.get("criteria", []),
            "can_transition": can_transition,
            "blocking_criteria": blocking,
        })
    return available


def execute_transition(
    config: ProjectConfig,
    get_item_fn,
    update_item_fn,
    item_id: str,
    to_state: str,
    performed_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a lifecycle transition.

    Args:
        config:         ProjectConfig instance.
        get_item_fn:    Callable(uid) -> Optional[dict] — load item from store.
        update_item_fn: Callable(uid, data) -> dict — persist item.
        item_id:        UID of the item to transition.
        to_state:       Target state ID.
        performed_by:   User performing the transition (for audit trail).

    Raises:
        ValueError: if item not found, transition not allowed, or criteria unmet.
    """
    item = get_item_fn(item_id)
    if item is None:
        raise ValueError(f"Item '{item_id}' not found.")

    available = get_available_transitions(config, item)
    transition = next((t for t in available if t["to_state"] == to_state), None)
    if transition is None:
        raise ValueError(
            f"Transition to '{to_state}' is not allowed from state '{item.get('status')}'."
        )
    if not transition["can_transition"]:
        blocking = ", ".join(transition["blocking_criteria"])
        raise ValueError(f"Blocking criteria not met: {blocking}")

    item["status"] = to_state
    return update_item_fn(item_id, item)
