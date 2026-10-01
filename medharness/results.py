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


class Timing(Shape):
    started_at: str = Field(description="When the run started, ISO 8601 UTC")
    elapsed_ms: int = Field(description="How long it took")


class Inputs(Shape):
    dhf_path: str = Field(description="The `--dhf` the run used")
    repo_root: str = Field(description="The repository the DHF is in")
    pr_number: int | None = Field(description="The `--pr` it was given, or null")
    revision_mode: bool = Field(description="True when it revised from a reviewer's changes instead of generating")
    since_ref: str = Field(description="What the branch is compared against")


class Progress(Shape):
    current_step: str | None = Field(description="The step running when the report was written, or null")
    completed_steps: int = Field(description="Steps finished")
    total_steps: int = Field(description="Steps in the run")


class Step(Shape):
    name: str = Field(description="The step, e.g. `run_initial_generation`, `validate_initial`, `run_review`")
    started_at: str = Field(description="When it started, ISO 8601 UTC")
    elapsed_ms: int = Field(description="How long it took")
    outcome: str = Field(description="`ok`, `warning` or `error`")
    details: dict[str, Any] = Field(description="Facts about the step; the keys vary by step")


class ChangeSet(Shape):
    created: list[str] = Field(description="Created since `since_ref`, committed or not")
    updated: list[str] = Field(description="Modified since `since_ref`")
    deleted: list[str] = Field(description="Deleted since `since_ref`")


class DesignImpact(Shape):
    recorded: bool = Field(description="Whether the CR's `affected_items` was written")
    reason: str = Field(description="Why or why not, e.g. `updated`")
    affected_items: list[str] | None = Field(default=None, description="The items recorded, when they were")


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
    design_impact: DesignImpact | None = Field(default=None, description="The CR's `affected_items` write-back")


class CodeArtifacts(Shape):
    files_changed: ChangeSet | None = Field(
        description="The code changed on the branch; null when the diff could not be read")


class StageReport(Shape):
    cr_id: str = Field(description="The CR the run was for")
    outcome: Literal["ok", "corrected", "completed_with_errors", "tool_error"] = Field(
        description="`ok`; `corrected` after a fix pass; `completed_with_errors` when errors remain; "
                    "`tool_error` when a critical step failed. The last two exit 1")
    summary: str = Field(description="The outcome in a sentence")
    timing: Timing = Field(description="When it started and how long it took")
    inputs: Inputs = Field(description="What the run was given")
    progress: Progress = Field(description="How far it got")
    steps: list[Step] = Field(description="Every step, in order")
    diagnostics: dict[str, Any] = Field(
        description="Models used, the session id, fix and review counts, PR feedback; the keys vary by stage")
    warnings: list[RunWarning] = Field(description="What the run noticed without failing")
    errors: list[RunError] = Field(description="Empty unless the run ended with errors")
    pr_comments: list[str] | None = Field(
        default=None, description="With `--pr`: the URLs of the comments it posted on the PR to report warnings or errors")


class PlanReport(StageReport):
    """`build plan`."""

    stage: Literal["generate_dhf"] = Field(description="Always `generate_dhf` for `build plan`")
    artifacts: PlanArtifacts = Field(description="What the run changed")
    design_review: Review | None = Field(default=None, description="The design review rounds, when one ran")


class CodeReport(StageReport):
    """`build code`."""

    stage: Literal["develop"] = Field(description="Always `develop` for `build code`")
    artifacts: CodeArtifacts = Field(description="What the run changed")
    code_review: Review | None = Field(default=None, description="The code review rounds, when one ran")


# ── build soup / build release / init ────────────────────────────────────────

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

    outcome: Literal["completed", "completed_with_errors"] = Field(
        description="`completed_with_errors` exits 1")
    manifests_parsed: list[str] = Field(description="The manifests it read")
    packages_found: int = Field(description="Packages across them")
    to_create: list[str] = Field(description="Packages with no SOUP item")
    to_update: list[SoupDrift] = Field(description="SOUP items whose version has drifted")
    orphans: list[SoupOrphan] = Field(description="SOUP items no manifest resolves")
    matched_count: int = Field(description="Packages that already have a matching SOUP item")
    items_created: list[str] = Field(description="SOUP items it wrote, in the working tree")
    items_updated: list[str] = Field(description="SOUP items it changed, in the working tree")
    errors: list[str] = Field(description="Manifests or commands that could not be read")


class ReleaseReport(Shape):
    """`build release`."""

    outcome: Literal["completed", "completed_with_errors"] = Field(
        description="`completed_with_errors` exits 1; a failing release still writes its evidence")
    version: str = Field(description="The version released")
    cr_ids: list[str] = Field(description="The completed CRs it includes")
    rel_uid: str | None = Field(description="The REL item recorded; null without `--write` or when a check failed")
    soup_count: int = Field(description="SOUP items in the BOM")
    artifacts: list[str] = Field(description="Files written under `--out-dir`, relative to it")
    errors: list[str] = Field(description="What blocked the release")
    warnings: list[str] = Field(description="What it noticed without blocking, such as a component with no purl")


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
    ("`init`", (InitReport,)),
)
