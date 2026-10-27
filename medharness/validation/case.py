"""A validation case, and how a set of them runs."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from click.testing import CliRunner

from medharness.cli import main


class CaseFailed(Exception):
    """A case found the tool behaving otherwise than its requirement says."""


def check(condition: object, message: str) -> None:
    """Fail the case unless *condition* holds. Never `assert`: `python -O` removes it."""
    if not condition:
        raise CaseFailed(message)


@dataclass(frozen=True)
class Case:
    name: str
    requirement: str
    points: tuple[str, ...]
    #: Builds the scratch project in an empty directory. Cases that share it share one build.
    project: Callable[[Path], None]
    #: Changes the copy of the project it is given, runs the CLI, and checks the answers.
    run: Callable[[Path], None]
    #: External programs the case needs; without one it is `not_run`, never passed.
    tools: tuple[str, ...] = ("git",)


@dataclass(frozen=True)
class Outcome:
    case: Case
    status: Literal["passed", "failed", "not_run"]
    message: str


def invoke(root: Path, *args: str) -> tuple[int, dict, str]:
    """Run the CLI in-process on the DHF of *root*: the exit code, the JSON answer, stderr."""
    result = CliRunner().invoke(main, ["--dhf", str(root / "DHF"), *args])
    if result.exception is not None and not isinstance(result.exception, SystemExit):
        raise CaseFailed(f"`{' '.join(args)}` crashed: {result.exception!r}")
    lines = result.stdout.splitlines()
    try:
        answer = json.loads(lines[0]) if lines else {}
    except json.JSONDecodeError as exc:
        raise CaseFailed(f"`{' '.join(args)}` printed no JSON: {result.stdout[:200]!r}") from exc
    return result.exit_code, answer, result.stderr


def run_cases(cases: list[Case], workdir: Path) -> list[Outcome]:
    """Run each case in its own copy of its project, under *workdir*."""
    built: dict[Callable, Path | CaseFailed] = {}
    outcomes = []
    for index, case in enumerate(cases):
        missing = [tool for tool in case.tools if shutil.which(tool) is None]
        if missing:
            outcomes.append(Outcome(case, "not_run", f"{', '.join(missing)} not found on PATH"))
            continue
        if case.project not in built:
            template = workdir / "projects" / str(len(built))
            template.mkdir(parents=True)
            try:
                case.project(template)
                built[case.project] = template
            except Exception as exc:  # noqa: BLE001  (a project that cannot be built fails its cases)
                built[case.project] = CaseFailed(f"the scratch project could not be built: {exc!r}")
        template = built[case.project]
        if isinstance(template, CaseFailed):
            outcomes.append(Outcome(case, "failed", str(template)))
            continue
        root = workdir / "cases" / str(index)
        shutil.copytree(template, root, symlinks=True)
        try:
            case.run(root)
        except CaseFailed as exc:
            outcomes.append(Outcome(case, "failed", str(exc)))
        except Exception as exc:  # noqa: BLE001  (a crash is a failure of the tool, not of the run)
            outcomes.append(Outcome(case, "failed", f"{type(exc).__name__}: {exc}"))
        else:
            outcomes.append(Outcome(case, "passed", ""))
    return outcomes
