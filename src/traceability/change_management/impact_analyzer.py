"""Impact analyzer for change requests."""

from typing import Set, List
from ..models.change_request import ChangeRequest, ChangeImpact
from ..graph.engine import GraphEngine


class ImpactAnalyzer:
    """
    Analyzes the impact of change requests on the project.
    
    Uses the graph engine to identify all downstream dependencies
    and assess significance per MDCG 2020-3 criteria.
    """
    
    # MDCG 2020-3 significance criteria
    SIGNIFICANCE_CRITERIA = [
        "Affects safety-critical requirements",
        "Changes intended use or indications for use",
        "Modifies risk control measures",
        "Changes clinical benefits or performance",
        "Affects user interface in safety-critical way"
    ]
    
    def __init__(self, graph: GraphEngine):
        """
        Initialize impact analyzer.
        
        Args:
            graph: GraphEngine instance for traceability analysis
        """
        self.graph = graph
    
    def analyze_impact(self, change_request: ChangeRequest) -> ChangeImpact:
        """
        Analyze the impact of a change request.
        
        Args:
            change_request: ChangeRequest to analyze
            
        Returns:
            ChangeImpact object with analysis results
        """
        # Collect all affected items (direct + downstream)
        all_affected: Set[str] = set(change_request.affected_items)
        
        # For each directly affected item, get all downstream dependencies
        for item_uid in change_request.affected_items:
            if self.graph.graph.has_node(item_uid):
                downstream = self.graph.get_downstream(item_uid)
                all_affected.update(downstream)
        
        # Categorize affected items by type
        affected_requirements = []
        affected_tests = []
        affected_risks = []
        affected_other = []
        
        for uid in all_affected:
            if not self.graph.graph.has_node(uid):
                continue
            
            # Get item type from UID prefix
            if uid.startswith('CRS-') or uid.startswith('SYS-') or uid.startswith('SDS-'):
                affected_requirements.append(uid)
            elif uid.startswith('TC-'):
                affected_tests.append(uid)
            elif uid.startswith('RISK-') or uid.startswith('RCM-'):
                affected_risks.append(uid)
            else:
                affected_other.append(uid)
        
        # Assess significance
        is_significant, rationale = self._assess_significance(
            change_request,
            affected_requirements,
            affected_risks
        )
        
        # Generate impact summary
        impact_summary = self._generate_impact_summary(
            change_request,
            affected_requirements,
            affected_tests,
            affected_risks
        )
        
        return ChangeImpact(
            change_id=change_request.id,
            affected_requirements=affected_requirements,
            affected_tests=affected_tests,
            affected_risks=affected_risks,
            affected_other=affected_other,
            downstream_count=len(all_affected) - len(change_request.affected_items),
            is_significant=is_significant,
            significance_rationale=rationale,
            impact_summary=impact_summary
        )
    
    def _assess_significance(
        self,
        change_request: ChangeRequest,
        affected_requirements: List[str],
        affected_risks: List[str]
    ) -> tuple[bool, str]:
        """
        Assess if change is significant per MDCG 2020-3.
        
        Args:
            change_request: The change request
            affected_requirements: List of affected requirement UIDs
            affected_risks: List of affected risk UIDs
            
        Returns:
            Tuple of (is_significant, rationale)
        """
        reasons = []
        
        # Check if affects safety-critical requirements
        for req_uid in affected_requirements:
            if self.graph.graph.has_node(req_uid):
                item = self.graph.graph.nodes[req_uid].get('item')
                if item and hasattr(item, 'critical_safety') and item.critical_safety:
                    reasons.append("Affects safety-critical requirements")
                    break
        
        # Check if affects risk control measures
        if any(uid.startswith('RCM-') for uid in affected_risks):
            reasons.append("Modifies risk control measures")
        
        # Check change type - new features are often significant
        if change_request.type == "new_feature":
            reasons.append("Introduces new functionality")
        
        # Check priority - critical changes are often significant
        if change_request.priority == "critical":
            reasons.append("Critical priority change")
        
        # Check risk assessment content for keywords
        if change_request.risk_assessment:
            risk_text = change_request.risk_assessment.lower()
            if any(keyword in risk_text for keyword in ['safety', 'hazard', 'harm', 'clinical']):
                reasons.append("Risk assessment mentions safety/clinical concerns")
        
        is_significant = len(reasons) > 0
        rationale = "; ".join(reasons) if reasons else "No significance criteria met"
        
        return is_significant, rationale
    
    def _generate_impact_summary(
        self,
        change_request: ChangeRequest,
        affected_requirements: List[str],
        affected_tests: List[str],
        affected_risks: List[str]
    ) -> str:
        """
        Generate human-readable impact summary.
        
        Args:
            change_request: The change request
            affected_requirements: List of affected requirement UIDs
            affected_tests: List of affected test UIDs
            affected_risks: List of affected risk UIDs
            
        Returns:
            Impact summary string
        """
        lines = []
        lines.append(f"Change Request: {change_request.id} - {change_request.title}")
        lines.append(f"Type: {change_request.type}, Priority: {change_request.priority}")
        lines.append("")
        lines.append("Impact Analysis:")
        lines.append(f"- Directly affected items: {len(change_request.affected_items)}")
        lines.append(f"- Affected requirements: {len(affected_requirements)}")
        lines.append(f"- Affected tests: {len(affected_tests)}")
        lines.append(f"- Affected risks: {len(affected_risks)}")
        
        if affected_requirements:
            lines.append("")
            lines.append("Affected Requirements:")
            for uid in sorted(affected_requirements)[:10]:  # Show max 10
                lines.append(f"  - {uid}")
            if len(affected_requirements) > 10:
                lines.append(f"  ... and {len(affected_requirements) - 10} more")
        
        if affected_tests:
            lines.append("")
            lines.append("Tests Requiring Update:")
            for uid in sorted(affected_tests)[:10]:
                lines.append(f"  - {uid}")
            if len(affected_tests) > 10:
                lines.append(f"  ... and {len(affected_tests) - 10} more")
        
        return "\n".join(lines)
    
    def get_significance_criteria(self) -> List[str]:
        """
        Get list of MDCG 2020-3 significance criteria.
        
        Returns:
            List of criteria strings
        """
        return self.SIGNIFICANCE_CRITERIA.copy()
