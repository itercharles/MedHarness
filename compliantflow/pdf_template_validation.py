"""Template-driven validation for regulatory submission PDF inputs.

This module defines a small, explicit interface that CR-032 can build on.
It validates report payload structure before PDF rendering and returns
structured findings suitable for CI or manual review workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class ValidationIssue:
    """Single validation finding."""

    code: str
    message: str
    path: str


@dataclass(frozen=True)
class ValidationResult:
    """Result of template validation."""

    template_id: str
    report_kind: str
    passed: bool
    issues: List[ValidationIssue]


@dataclass(frozen=True)
class SubmissionTemplate:
    """Template profile with structural requirements."""

    template_id: str
    report_kind: str
    required_keys: List[str]
    required_non_empty_keys: List[str]


DEFAULT_TEMPLATES: Dict[str, SubmissionTemplate] = {
    # US FDA 510(k)-style evidence package checks.
    "fda_510k_traceability": SubmissionTemplate(
        template_id="fda_510k_traceability",
        report_kind="traceability",
        required_keys=["columns", "rows"],
        required_non_empty_keys=["columns", "rows"],
    ),
    "fda_510k_compliance": SubmissionTemplate(
        template_id="fda_510k_compliance",
        report_kind="compliance",
        required_keys=["source_id", "results", "total_policies", "passed_policies", "score"],
        required_non_empty_keys=["results"],
    ),
    # EU CE technical file style checks.
    "ce_marking_traceability": SubmissionTemplate(
        template_id="ce_marking_traceability",
        report_kind="traceability",
        required_keys=["columns", "rows", "test_results"],
        required_non_empty_keys=["columns", "rows"],
    ),
    # Internal quality management review pack.
    "internal_qms_compliance": SubmissionTemplate(
        template_id="internal_qms_compliance",
        report_kind="compliance",
        required_keys=["source_id", "results", "score"],
        required_non_empty_keys=["results"],
    ),
}


def validate_submission_payload(
    payload: Dict[str, Any],
    *,
    template_id: str,
    report_kind: str,
    templates: Dict[str, SubmissionTemplate] | None = None,
) -> ValidationResult:
    """Validate a PDF report payload against a configured template.

    Args:
        payload: In-memory report payload used to render PDF output.
        template_id: Selected validation template profile ID.
        report_kind: One of ``traceability`` or ``compliance``.
        templates: Optional template registry override for testing/customization.

    Returns:
        ValidationResult with pass/fail and structured issues.
    """
    template_registry = DEFAULT_TEMPLATES if templates is None else templates
    issues: List[ValidationIssue] = []

    template = template_registry.get(template_id)
    if template is None:
        return ValidationResult(
            template_id=template_id,
            report_kind=report_kind,
            passed=False,
            issues=[
                ValidationIssue(
                    code="template_not_found",
                    message=f"Unknown template_id: {template_id}",
                    path="template_id",
                )
            ],
        )

    if template.report_kind != report_kind:
        issues.append(
            ValidationIssue(
                code="report_kind_mismatch",
                message=(
                    f"Template {template_id} expects report_kind={template.report_kind}, "
                    f"got {report_kind}"
                ),
                path="report_kind",
            )
        )

    for key in template.required_keys:
        if key not in payload:
            issues.append(
                ValidationIssue(
                    code="missing_required_key",
                    message=f"Missing required key: {key}",
                    path=key,
                )
            )

    for key in template.required_non_empty_keys:
        value = payload.get(key)
        is_empty = value in (None, "", [], {})
        if is_empty:
            issues.append(
                ValidationIssue(
                    code="required_key_empty",
                    message=f"Required key is empty: {key}",
                    path=key,
                )
            )

    if report_kind == "compliance" and isinstance(payload.get("results"), list):
        for idx, row in enumerate(payload["results"]):
            if not isinstance(row, Mapping):
                issues.append(
                    ValidationIssue(
                        code="invalid_result_row",
                        message="Compliance result row must be an object",
                        path=f"results[{idx}]",
                    )
                )
                continue
            if "policy_id" not in row:
                issues.append(
                    ValidationIssue(
                        code="missing_policy_id",
                        message="Compliance result row missing policy_id",
                        path=f"results[{idx}].policy_id",
                    )
                )
            if "passed" not in row:
                issues.append(
                    ValidationIssue(
                        code="missing_passed_flag",
                        message="Compliance result row missing passed",
                        path=f"results[{idx}].passed",
                    )
                )

    return ValidationResult(
        template_id=template_id,
        report_kind=report_kind,
        passed=not issues,
        issues=issues,
    )


__all__ = [
    "SubmissionTemplate",
    "ValidationIssue",
    "ValidationResult",
    "DEFAULT_TEMPLATES",
    "validate_submission_payload",
]
