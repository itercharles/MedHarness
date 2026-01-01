"""
Change Request Manager

Utilities for managing change request-based stable item protection.
This module is configuration-driven and can be enabled/disabled via project_config.yaml.
"""

from typing import Optional, Dict, List
from pathlib import Path


def is_change_control_enabled(core) -> bool:
    """
    Check if change control is enabled in configuration.
    
    Args:
        core: CompliantFlowCore instance
        
    Returns:
        True if change control is enabled, False otherwise
    """
    if not hasattr(core.config, 'change_control'):
        return False
    return core.config.change_control.get('enabled', False)


def get_cr_doc_type(core) -> str:
    """
    Get the document type code used for change requests.
    
    Args:
        core: CompliantFlowCore instance
        
    Returns:
        Document type code (default: 'CR')
    """
    if not hasattr(core.config, 'change_control'):
        return 'CR'
    return core.config.change_control.get('change_request_type', 'CR')


def get_affected_items_field(core) -> str:
    """
    Get the field name used for tracking affected items in CRs.
    
    Args:
        core: CompliantFlowCore instance
        
    Returns:
        Field name (default: 'affected_items')
    """
    if not hasattr(core.config, 'change_control'):
        return 'affected_items'
    return core.config.change_control.get('affected_items_field', 'affected_items')


def get_non_stable_cr(core) -> Optional[Dict]:
    """
    Get the first non-stable CR (if any).
    Non-stable CRs are those without is_stable=true in their workflow state.
    
    Args:
        core: CompliantFlowCore instance
        
    Returns:
        CR dict if found, None otherwise
    """
    if not is_change_control_enabled(core):
        return None
    
    cr_type = get_cr_doc_type(core)
    
    # Get all items and filter by CR type
    all_items = core.get_all_items()
    all_crs = [item for item in all_items if item['id'].startswith(f"{cr_type}-")]
    
    # Get CR workflow config
    cr_config = core.config.get_doc_type(cr_type)
    if not cr_config:
        return None
    
    workflow = DynamicWorkflowEngine(cr_config.model_dump(), core)
    
    for cr in all_crs:
        state_info = workflow.get_state_info(cr.get('status', ''))
        if not state_info.get('is_stable', False):
            return cr
    
    return None


def get_cr_for_item(item_id: str, core) -> Optional[Dict]:
    """
    Get the CR that includes this item in its affected_items list.
    
    Args:
        item_id: Item ID to search for
        core: CompliantFlowCore instance
        
    Returns:
        CR dict if found, None otherwise
    """
    if not is_change_control_enabled(core):
        return None
    
    cr_type = get_cr_doc_type(core)
    affected_field = get_affected_items_field(core)
    
    # Get all items and filter by CR type
    all_items = core.get_all_items()
    all_crs = [item for item in all_items if item['id'].startswith(f"{cr_type}-")]
    
    for cr in all_crs:
        affected = cr.get(affected_field, [])
        if item_id in affected:
            return cr
    
    return None


def add_item_to_cr(cr_id: str, item_id: str, core) -> bool:
    """
    Add an item to CR's affected_items list.
    Only allowed if CR is not in a stable state.
    
    Args:
        cr_id: CR ID to add item to
        item_id: Item ID to add
        core: CompliantFlowCore instance
        
    Returns:
        True if successful, False otherwise
    """
    if not is_change_control_enabled(core):
        return False
    
    cr = core.get_item(cr_id)
    if not cr:
        return False
    
    # Check if CR is stable
    cr_type = get_cr_doc_type(core)
    cr_config = core.config.get_doc_type(cr_type)
    if not cr_config:
        return False
    
    workflow = DynamicWorkflowEngine(cr_config.model_dump(), core)
    state_info = workflow.get_state_info(cr.get('status', ''))
    
    if state_info.get('is_stable', False):
        return False  # Can't modify stable CRs
    
    # Add item if not already present
    affected_field = get_affected_items_field(core)
    affected = cr.get(affected_field, [])
    
    if item_id not in affected:
        affected.append(item_id)
        cr[affected_field] = affected
        core.update_item(cr_id, cr)
    
    return True


def is_cr_stable(cr: Dict, core) -> bool:
    """
    Check if a CR is in a stable state.
    
    Args:
        cr: CR dict
        core: CompliantFlowCore instance
        
    Returns:
        True if CR is stable, False otherwise
    """
    if not cr:
        return True  # Treat missing CR as stable (locked)
    
    cr_type = get_cr_doc_type(core)
    cr_config = core.config.get_doc_type(cr_type)
    if not cr_config:
        return True
    
    workflow = DynamicWorkflowEngine(cr_config.model_dump(), core)
    state_info = workflow.get_state_info(cr.get('status', ''))
    
    return state_info.get('is_stable', False)
