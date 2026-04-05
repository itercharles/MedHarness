"""Submission payload template validation for PDF report workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple


@dataclass(frozen=True)
class SubmissionTemplate:
    """Template profile used to validate a report payload before rendering."""

    key: str
    label: str
    report_kind: str
    required_keys: Tuple[str, ...]
    required_result_fields: Tuple[str, ...]


@dataclass(frozen=True)
class ValidationIssue:
    """Represents a single validation issue discovered in a payload."""

    code: str
    message: str
    path: str


@dataclass(frozen=True)
class ValidationResult:
    """Validation outcome for a given payload and template profile."""

    template_key: str
    report_kind: str
    is_valid: bool
    issues: Tuple[ValidationIssue, ...]


_TEMPLATE_PROFILES: Dict[str, SubmissionTemplate] = {
    "fda_510k_compliance": SubmissionTemplate(
        key="fda_510k_compliance",
        label="FDA 510(k) Compliance Submission",
        report_kind="compliance",
        required_keys=("source_id", "score", "total_policies", "passed_policies", "results"),
        required_result_fields=("policy_id", "passed"),
    ),
    "ce_marking_compliance": SubmissionTemplate(
        key="ce_marking_compliance",
        label="CE Marking Compliance Submission",
        report_kind="compliance",
        required_keys=("source_id", "score", "total_policies", "passed_policies", "results"),
        required_result_fields=("policy_id", "passed"),
    ),
    "internal_qms_traceability": SubmissionTemplate(
        key="internal_qms_traceability",
        label="Internal QMS Traceability Evidence",
        report_kind="traceability",
        required_keys=("columns", "rows"),
        required_result_fields=(),
    ),
}


def get_submission_template(template_key: str) -> SubmissionTemplate | None:
    """Return a built-in template profile by key."""
    return _TEMPLATE_PROFILES.get(template_key)


def list_submission_templates() -> Sequence[SubmissionTemplate]:
    """Return all built-in template profiles."""
    return tuple(_TEMPLATE_PROFILES.values())


def validate_submission_payload(
    payload: Mapping[str, Any], *, report_kind: str, template_key: str
) -> ValidationResult:
    """Validate report payload structure against a built-in submission template."""
    issues: list[ValidationIssue] = []
    template = get_submission_template(template_key)

    if template is None:
        issues.append(
            ValidationIssue(
                code="unknown_template",
                message=f"Unknown submission template: {template_key}",
                path="template_key",
            )
        )
        return ValidationResult(
            template_key=template_key,
            report_kind=report_kind,
            is_valid=False,
            issues=tuple(issues),
        )

    if template.report_kind != report_kind:
        issues.append(
            ValidationIssue(
                code="report_kind_mismatch",
                message=(
                    f"Template '{template.key}' expects report kind '{template.report_kind}' "
                    f"but received '{report_kind}'"
                ),
                path="report_kind",
            )
        )

    _validate_required_keys(payload, template.required_keys, issues)

    if template.report_kind == "compliance":
        _validate_compliance_summary_fields(payload, issues)
        _validate_compliance_results(payload.get("results"), template.required_result_fields, issues)

    return ValidationResult(
        template_key=template.key,
        report_kind=report_kind,
        is_valid=not issues,
        issues=tuple(issues),
    )


def _validate_required_keys(
    payload: Mapping[str, Any],
    required_keys: Sequence[str],
    issues: list[ValidationIssue],
) -> None:
    for key in required_keys:
        if key not in payload:
            issues.append(
                ValidationIssue(
                    code="missing_required_key",
                    message=f"Missing required key: {key}",
                    path=key,
                )
            )
            continue

        if _is_empty(payload[key]):
            issues.append(
                ValidationIssue(
                    code="empty_required_key",
                    message=f"Required key has empty value: {key}",
                    path=key,
                )
            )


def _validate_compliance_results(
    results: Any,
    required_fields: Sequence[str],
    issues: list[ValidationIssue],
) -> None:
    if results is None:
        # Missing/empty handling already covered in _validate_required_keys.
        return

    if not isinstance(results, list):
        issues.append(
            ValidationIssue(
                code="invalid_results_type",
                message="Compliance results must be a list",
                path="results",
            )
        )
        return

    for idx, row in enumerate(results):
        if not isinstance(row, Mapping):
            issues.append(
                ValidationIssue(
                    code="invalid_results_row",
                    message="Each compliance result row must be an object",
                    path=f"results[{idx}]",
                )
            )
            continue

        for field in required_fields:
            if field not in row:
                issues.append(
                    ValidationIssue(
                        code="missing_required_result_field",
                        message=f"Missing required result field: {field}",
                        path=f"results[{idx}].{field}",
                    )
                )
            elif _is_empty(row[field]):
                issues.append(
                    ValidationIssue(
                        code="empty_required_result_field",
                        message=f"Required result field has empty value: {field}",
                        path=f"results[{idx}].{field}",
                    )
                )

        if "passed" in row and not isinstance(row["passed"], bool):
            issues.append(
                ValidationIssue(
                    code="invalid_passed_type",
                    message="Compliance result field 'passed' must be a boolean",
                    path=f"results[{idx}].passed",
                )
            )


def _validate_compliance_summary_fields(
    payload: Mapping[str, Any],
    issues: list[ValidationIssue],
) -> None:
    _require_type(payload, "score", (int, float), "invalid_score_type", "score must be numeric", issues)
    _require_type(
        payload,
        "total_policies",
        int,
        "invalid_total_policies_type",
        "total_policies must be an integer",
        issues,
    )
    _require_type(
        payload,
        "passed_policies",
        int,
        "invalid_passed_policies_type",
        "passed_policies must be an integer",
        issues,
    )


def _require_type(
    payload: Mapping[str, Any],
    key: str,
    expected_type: type[Any] | tuple[type[Any], ...],
    code: str,
    message: str,
    issues: list[ValidationIssue],
) -> None:
    if key not in payload or _is_empty(payload[key]):
        return

    value = payload[key]
    if not isinstance(value, expected_type) or isinstance(value, bool):
        issues.append(
            ValidationIssue(
                code=code,
                message=message,
                path=key,
            )
        )


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False
