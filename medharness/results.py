"""What each command answers with, declared once.

`docs/interface.md` renders its field tables from these models
(`scripts/generate_interface.py`), and tests validate real command output against
them, so an undeclared key, a missing one or a changed type fails the build. A
field description is documentation a caller reads: say what it means, not how it
is computed.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Shape(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── verify ───────────────────────────────────────────────────────────────────

class GateResult(Shape):
    """What every `verify` command writes to stdout: one line of JSON."""

    gate: str = Field(description="The command that produced this, e.g. `verify tests`")
    passed: bool = Field(description="Whether the check is satisfied. Always agrees with the exit code")
    summary: str = Field(description="One line, never empty")
    errors: list[str] = Field(description="What made the check fail. Empty when `passed` is true")
    warnings: list[str] = Field(description="What the check noticed without failing")


# ── build plan / build code ──────────────────────────────────────────────────

class RunError(Shape):
    field: str = Field(description="What was wrong, as a dotted path such as `traceability.dangling.satisfies`")
    issue: str = Field(description="The problem, phrased for a reader")
    fix: str = Field(description="What to do about it")
    code: str = Field(description="A stable identifier derived from `field`")


class RunWarning(Shape):
    code: str = Field(description="A stable identifier, e.g. `agent_commits_undone`")
    message: str = Field(description="The warning, phrased for a reader")
    details: dict[str, Any] | None = Field(default=None, description="Extra facts, when the warning has any")


class Step(Shape):
    name: str = Field(description="The step, e.g. `run_initial_generation`, `validate_initial`, `run_review`")
    started_at: str = Field(description="When it started, ISO 8601 UTC")
    elapsed_ms: int = Field(description="How long it took")
    outcome: str = Field(description="`ok`, `warning` or `failed`")


class ChangeSet(Shape):
    created: list[str] = Field(description="Created since `since_ref`, committed or not")
    updated: list[str] = Field(description="Modified since `since_ref`")
    deleted: list[str] = Field(description="Deleted since `since_ref`")


class ReviewCycle(Shape):
    cycle: int = Field(description="1 for the first review, up to 3")
    verdict: Literal["approved", "needs_revision", "unknown"] = Field(description="What the reviewer concluded")
    issues: list[str] = Field(description="What it asked to change")


class Review(Shape):
    cycles: list[ReviewCycle] = Field(description="One entry per review round")
    narrative: list[str] = Field(description="The rounds as sentences, for a log")


class PlanArtifacts(Shape):
    items_changed: ChangeSet | None = Field(
        description="The DHF items changed on the branch, the CR's whole change set; null when the diff could not be read")


class CodeArtifacts(Shape):
    files_changed: ChangeSet | None = Field(
        description="The code changed on the branch; null when the diff could not be read")


class StageReport(Shape):
    cr_id: str = Field(description="The CR the run was for")
    outcome: Literal["ok", "corrected", "completed_with_errors", "tool_error", "rejected"] = Field(
        description="`ok`; `corrected` after a fix pass; `completed_with_errors` when errors remain; "
                    "`tool_error` when a critical step failed; `rejected` when triage turned the CR down "
                    "(the reason is in `errors`, no design was generated). The last three exit 1")
    summary: str = Field(description="The outcome in a sentence")
    steps: list[Step] = Field(description="Every step, in order")
    warnings: list[RunWarning] = Field(description="What the run noticed without failing")
    errors: list[RunError] = Field(description="Empty unless the run ended with errors")
    pr_comments: list[str] | None = Field(
        default=None, description="With `--pr`: the URLs of the comments it posted on the PR to report warnings or errors")


class PlanReport(StageReport):
    """`build plan`."""

    stage: Literal["generate_dhf"] = Field(description="Always `generate_dhf` for `build plan`")
    artifacts: PlanArtifacts = Field(description="What the run changed")
    design_review: Review | None = Field(default=None, description="The design review rounds, when one ran")


class CheckResult(Shape):
    command: str = Field(description="The `--check` command, as given")
    exit_code: int = Field(description="What it exited with in the last run; 124 when it timed out")
    passed: bool = Field(description="Whether it exited 0")


class CodeReport(StageReport):
    """`build code`."""

    stage: Literal["develop"] = Field(description="Always `develop` for `build code`")
    artifacts: CodeArtifacts = Field(description="What the run changed")
    code_review: Review | None = Field(default=None, description="The code review rounds, when one ran")
    checks: list[CheckResult] | None = Field(default=None, description="Each `--check` as the harness last ran it; absent without `--check`")


# ── build soup / build release / build approvals / build validation / init ────────────────────────────────────────

class SoupDrift(Shape):
    uid: str = Field(description="The SOUP item")
    name: str = Field(description="The package")
    old_version: str = Field(description="What the register says")
    new_version: str = Field(description="What the manifest says")


class SoupOrphan(Shape):
    uid: str = Field(description="The SOUP item no manifest resolves")
    name: str = Field(description="The package")


class SoupReport(Shape):
    """`build soup`."""

    manifests_parsed: list[str] = Field(description="The manifests it read")
    packages_found: int = Field(description="Packages across them")
    to_update: list[SoupDrift] = Field(description="SOUP items whose version has drifted")
    orphans: list[SoupOrphan] = Field(description="SOUP items no manifest resolves")
    items_created: list[str] = Field(description="SOUP items it wrote, in the working tree")
    errors: list[str] = Field(description="Manifests or commands that could not be read; any exits 1")


class ReleaseReport(Shape):
    """`build release`."""

    version: str = Field(description="The version released")
    cr_ids: list[str] = Field(description="The completed CRs it includes")
    rel_uid: str | None = Field(description="The REL item recorded; null without `--write` or when a check failed")
    artifacts: list[str] = Field(description="Files written under `--out-dir`, relative to it")
    errors: list[str] = Field(description="What blocked the release; any exits 1, and a failing release still writes its evidence")
    warnings: list[str] = Field(description="What it noticed without blocking, such as a component with no purl")


class ApprovalSheetReport(Shape):
    """`build approvals`."""

    version: str = Field(description="The release the sheet is for")
    path: str | None = Field(description="The sheet written; null when the release is not fully signed")
    errors: list[str] = Field(description="Why no sheet was written, as `verify approval --release` reports it; any exits 1")
    warnings: list[str] = Field(description="What `verify approval --release` noticed, such as a signature made without proven presence")


class ValidationReport(Shape):
    """`build validation`. The rest of what it found is in the report it writes."""

    result: Literal["passed", "failed", "incomplete"] = Field(
        description="`failed` when a point failed or an installed file differs; `incomplete` when a point did not run, "
                    "the build has no release record or the install cannot be checked. Only `passed` exits 0")
    path: str | None = Field(description="The report written; null when it could not be rendered")
    errors: list[str] = Field(description="Why the result is not `passed`")


class InitReport(Shape):
    """`init`."""

    project_name: str = Field(description="The name written into `global.yaml`")
    project_dir: str = Field(description="Where the project was scaffolded")
    created: list[str] = Field(description="Files created, relative to `project_dir`")


# What the generator renders, in this order, and which command each one is.
SHAPES: tuple[tuple[str, tuple[type[Shape], ...]], ...] = (
    ("`build plan`", (PlanReport,)),
    ("`build code`", (CodeReport,)),
    ("`build soup`", (SoupReport,)),
    ("`build release`", (ReleaseReport,)),
    ("`build approvals`", (ApprovalSheetReport,)),
    ("`build validation`", (ValidationReport,)),
    ("`init`", (InitReport,)),
)
