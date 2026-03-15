"""Compliance mixin — policy group loading and compliance checking."""

from typing import Optional, Dict, Any


class _ComplianceMixin:

    def get_policy_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a policy group without running checks.

        Args:
            group_id: ID of the policy group

        Returns:
            PolicyGroup dictionary or None
        """
        from compliantflow.policy import PolicyEngine

        engine = PolicyEngine(self)
        path = self.repo_root.parent / "governance" / f"{group_id}.yaml"

        group = engine.load_policy_group(path)
        if not group:
            return None

        return group.model_dump()

    def check_compliance(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Check compliance against a specific policy group.

        Args:
            group_id: ID of the policy group

        Returns:
            Compliance report dictionary or None
        """
        from compliantflow.policy import PolicyEngine

        engine = PolicyEngine(self)
        path = self.repo_root.parent / "governance" / f"{group_id}.yaml"

        group = engine.load_policy_group(path)
        if not group:
            return None

        report = engine.check_compliance(group)
        return report.model_dump()
