"""NetworkX-based graph engine for traceability analysis."""

import networkx as nx
from typing import List, Set, Dict, Any, Optional, Tuple
from ..models.item import Item
from ..models.config import ProjectConfig


class GraphEngine:
    """
    NetworkX-based traceability graph.
    
    Provides graph analysis capabilities including:
    - Orphan detection
    - Coverage calculation
    - Dependency tracking
    - Impact analysis
    """
    
    def __init__(self, config: Optional[ProjectConfig] = None):
        """Initialize graph engine."""
        self.graph = nx.DiGraph()
        self.config = config
    
    def build_from_items(self, items: List[Item]):
        """
        Build graph from items.
        
        Args:
            items: List of items to build graph from
        """
        self.graph.clear()
        
        # Add nodes
        for item in items:
            self.graph.add_node(item.uid, item=item)
        
        # Add edges (child -> parent) using ALL typed relationships
        for item in items:
            # Use all_linked_uids to include all relationship types (design, derives_from, implements, etc.)
            for parent_uid in item.all_linked_uids:
                if self.graph.has_node(parent_uid):
                    # Determine relation label
                    relation_label = "traces"
                    
                    if self.config:
                        # Get source and target doc types to find specific relation
                        source_type = self.config.get_doc_type_by_prefix(item.prefix)
                        target_item = self.graph.nodes[parent_uid]['item']
                        target_type = self.config.get_doc_type_by_prefix(target_item.prefix)
                        
                        if source_type and source_type.relations and target_type:
                            for relation in source_type.relations:
                                if relation.target == target_type.code:
                                    relation_label = relation.label
                                    break

                    self.graph.add_edge(item.uid, parent_uid, type=relation_label)
                else:
                    print(f"Warning: Link target {parent_uid} not found for item {item.uid}")
    
    def find_orphans(self) -> List[Dict[str, Any]]:
        """
        Find items missing required parent links.
        
        Returns:
            List of orphan items with details
        """
        if not self.config:
            return []
        
        orphans = []
        
        for node_id in self.graph.nodes:
            item: Item = self.graph.nodes[node_id]['item']
            prefix = item.prefix
            
            # Get doc type config
            doc_type = self.config.get_doc_type_by_prefix(prefix)
            if not doc_type or not doc_type.allowed_parents:
                continue
            
            # Check if has any parent of required type
            parents = list(self.graph.successors(node_id))
            
            if not parents:
                orphans.append({
                    "uid": node_id,
                    "type": doc_type.code,
                    "issue": f"Missing parent of type {doc_type.allowed_parents}",
                    "required_parents": doc_type.allowed_parents
                })
                continue
            
            # Check if any parent is of allowed type
            has_valid_parent = False
            for parent_uid in parents:
                parent_item: Item = self.graph.nodes[parent_uid]['item']
                parent_prefix = parent_item.prefix
                parent_type = self.config.get_doc_type_by_prefix(parent_prefix)
                
                if parent_type and parent_type.code in doc_type.allowed_parents:
                    has_valid_parent = True
                    break
            
            if not has_valid_parent:
                orphans.append({
                    "uid": node_id,
                    "type": doc_type.code,
                    "issue": f"No valid parent of type {doc_type.allowed_parents}",
                    "required_parents": doc_type.allowed_parents
                })
        
        return orphans
    
    def calculate_coverage(self, req_type_code: str) -> Dict[str, Any]:
        """
        Calculate test coverage for a requirement type.
        
        Args:
            req_type_code: Document type code (e.g., 'SYS')
            
        Returns:
            Coverage statistics
        """
        if not self.config:
            return {"coverage": 0.0, "total": 0, "covered": 0}
        
        # Find requirement prefix
        req_type = self.config.get_doc_type(req_type_code)
        if not req_type:
            return {"coverage": 0.0, "total": 0, "covered": 0}
        
        req_prefix = req_type.prefix
        
        # Find all requirements of this type
        reqs = [n for n in self.graph.nodes if n.startswith(req_prefix)]
        total = len(reqs)
        
        if total == 0:
            return {"coverage": 0.0, "total": 0, "covered": 0}
        
        # Count covered requirements
        covered = 0
        uncovered_items = []
        
        for req_uid in reqs:
            # Check if any test links to this requirement
            # Tests are predecessors (incoming edges)
            predecessors = list(self.graph.predecessors(req_uid))
            
            is_covered = False
            for pred_uid in predecessors:
                pred_item: Item = self.graph.nodes[pred_uid]['item']
                pred_prefix = pred_item.prefix
                pred_type = self.config.get_doc_type_by_prefix(pred_prefix)
                
                # Check if predecessor is a test
                if pred_type and pred_type.type == 'test':
                    # Optionally check if it verifies this type
                    if pred_type.verifies and req_type_code in pred_type.verifies:
                        is_covered = True
                        break
            
            if is_covered:
                covered += 1
            else:
                uncovered_items.append(req_uid)
        
        coverage_pct = (covered / total) * 100
        
        return {
            "coverage": round(coverage_pct, 2),
            "total": total,
            "covered": covered,
            "uncovered": uncovered_items
        }
    
    def get_downstream(self, uid: str) -> Set[str]:
        """
        Get all downstream dependencies (children).
        
        Args:
            uid: Item UID
            
        Returns:
            Set of downstream UIDs
        """
        if not self.graph.has_node(uid):
            return set()
        
        # Predecessors are children (items that link to this one)
        return set(nx.ancestors(self.graph, uid))
    
    def get_upstream(self, uid: str) -> Set[str]:
        """
        Get all upstream dependencies (parents).
        
        Args:
            uid: Item UID
            
        Returns:
            Set of upstream UIDs
        """
        if not self.graph.has_node(uid):
            return set()
        
        # Successors are parents (items this one links to)
        return set(nx.descendants(self.graph, uid))
    
    def get_impact_analysis(self, uid: str) -> Dict[str, Any]:
        """
        Analyze impact of changing an item.
        
        Args:
            uid: Item UID
            
        Returns:
            Impact analysis results
        """
        if not self.graph.has_node(uid):
            return {"error": "Item not found"}
        
        downstream = self.get_downstream(uid)
        upstream = self.get_upstream(uid)
        
        return {
            "uid": uid,
            "downstream_count": len(downstream),
            "upstream_count": len(upstream),
            "downstream_items": list(downstream),
            "upstream_items": list(upstream),
            "total_impact": len(downstream) + len(upstream)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.
        
        Returns:
            Graph statistics
        """
        stats = {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "orphans_count": len(self.find_orphans()),
        }
        

        return stats
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate the graph for issues.
        
        Returns:
            Validation results
        """
        issues = []
        
        # Check for orphans
        orphans = self.find_orphans()
        if orphans:
            issues.append({
                "type": "orphans",
                "count": len(orphans),
                "items": orphans
            })
        
        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                issues.append({
                    "type": "cycles",
                    "count": len(cycles),
                    "cycles": cycles
                })
        except:
            pass
        
        # Check for isolated nodes
        isolated = list(nx.isolates(self.graph))
        if isolated:
            issues.append({
                "type": "isolated",
                "count": len(isolated),
                "items": isolated
            })
        
        return {
            "valid": len(issues) == 0,
            "issue_count": len(issues),
            "issues": issues
        }
