"""Graph analysis utilities."""

from typing import List, Dict, Any, Set
from .engine import GraphEngine


def generate_traceability_matrix(
    engine: GraphEngine,
    source_prefix: str,
    target_prefix: str
) -> List[Dict[str, Any]]:
    """
    Generate a traceability matrix between two document types.
    
    Args:
        engine: Graph engine instance
        source_prefix: Source document prefix (e.g., 'TC-VER-')
        target_prefix: Target document prefix (e.g., 'SYS-')
        
    Returns:
        List of traceability relationships
    """
    matrix = []
    
    # Find all source items
    source_items = [
        n for n in engine.graph.nodes 
        if n.startswith(source_prefix)
    ]
    
    for source_uid in source_items:
        # Get all upstream items
        upstream = engine.get_upstream(source_uid)
        
        # Filter for target type
        targets = [u for u in upstream if u.startswith(target_prefix)]
        
        if targets:
            for target_uid in targets:
                matrix.append({
                    "source": source_uid,
                    "target": target_uid,
                    "relationship": "verifies"
                })
        else:
            # No target found
            matrix.append({
                "source": source_uid,
                "target": None,
                "relationship": "orphan"
            })
    
    return matrix


def find_gaps(engine: GraphEngine) -> Dict[str, List[str]]:
    """
    Find gaps in traceability.
    
    Args:
        engine: Graph engine instance
        
    Returns:
        Dictionary of gap types and affected items
    """
    gaps = {
        "orphans": [],
        "untested": [],
        "isolated": []
    }
    
    # Find orphans
    orphans = engine.find_orphans()
    gaps["orphans"] = [o["uid"] for o in orphans]
    
    # Find untested requirements (if config available)
    if engine.config:
        for type_code in engine.config.policies.require_test_coverage:
            coverage = engine.calculate_coverage(type_code)
            gaps["untested"].extend(coverage.get("uncovered", []))
    
    # Find isolated nodes
    import networkx as nx
    gaps["isolated"] = list(nx.isolates(engine.graph))
    
    return gaps


__all__ = ["generate_traceability_matrix", "find_gaps"]
