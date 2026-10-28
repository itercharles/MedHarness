"""A validation case, and how a set of them runs."""

from __future__ import annotations

import json
import multiprocessing
import shutil
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
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


def _shipped() -> dict[str, Case]:
    from medharness.validation import CASES  # noqa: PLC0415  (the package imports this module)

    return {case.name: case for case in CASES}


def _execute(case: Case, template: Path, root: Path) -> tuple[str, str]:
    """Run *case* in a copy of *template* at *root*: its status and, unless it passed, why."""
    try:
        shutil.copytree(template, root, symlinks=True)
        case.run(root)
    except CaseFailed as exc:
        return "failed", str(exc)
    except Exception as exc:  # noqa: BLE001  (a crash is a failure of the tool, not of the run)
        return "failed", f"{type(exc).__name__}: {exc}"
    return "passed", ""


def _execute_shipped(name: str, template: str, root: str) -> tuple[str, str]:
    """`_execute` in a worker process, which finds its case by name: a closure cannot be sent to one."""
    return _execute(_shipped()[name], Path(template), Path(root))


def _in_workers(ready: list[tuple[int, Case, Path]], workdir: Path, jobs: int) -> dict[int, tuple[str, str]]:
    shipped = _shipped()
    strangers = [case.name for _, case, _ in ready if shipped.get(case.name) is not case]
    if strangers:
        raise ValueError(f"cases outside the shipped set cannot run in worker processes (use one job): {strangers}")
    results: dict[int, tuple[str, str]] = {}
    # spawn, not fork: a cheap start would copy the parent's threads, and the cases patch process-wide state.
    with ProcessPoolExecutor(max_workers=min(jobs, len(ready)), mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = [(index, pool.submit(_execute_shipped, case.name, str(template), str(workdir / "cases" / str(index))))
                   for index, case, template in ready]
        for index, future in futures:
            try:
                results[index] = future.result()
            except BrokenProcessPool:
                results[index] = ("failed", "a worker process died while the cases were running, so this one did not finish")
    return results


def run_cases(cases: list[Case], workdir: Path, jobs: int = 1) -> list[Outcome]:
    """Run each case in its own copy of its project, under *workdir*, *jobs* at a time.

    Each case runs alone in its process either way. The cases patch process-wide state and the CLI's
    in-process runner swaps `sys.stdout`, so they run in worker processes and never in threads.
    """
    outcomes: dict[int, Outcome] = {}
    templates: dict[Callable, Path | str] = {}
    ready: list[tuple[int, Case, Path]] = []
    for index, case in enumerate(cases):
        missing = [tool for tool in case.tools if shutil.which(tool) is None]
        if missing:
            outcomes[index] = Outcome(case, "not_run", f"{', '.join(missing)} not found on PATH")
            continue
        if case.project not in templates:
            template = workdir / "projects" / str(len(templates))
            template.mkdir(parents=True)
            try:
                case.project(template)
                templates[case.project] = template
            except Exception as exc:  # noqa: BLE001  (a project that cannot be built fails its cases)
                templates[case.project] = f"the scratch project could not be built: {exc!r}"
        template = templates[case.project]
        if isinstance(template, str):
            outcomes[index] = Outcome(case, "failed", template)
        else:
            ready.append((index, case, template))

    if jobs > 1 and len(ready) > 1:
        results = _in_workers(ready, workdir, jobs)
    else:
        results = {index: _execute(case, template, workdir / "cases" / str(index)) for index, case, template in ready}
    for index, case, _ in ready:
        status, message = results[index]
        outcomes[index] = Outcome(case, status, message)
    return [outcomes[index] for index in range(len(cases))]
