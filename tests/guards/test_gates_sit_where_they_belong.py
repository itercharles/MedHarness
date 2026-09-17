"""A verify command answers from the DHF. Git and GitHub belong to workflow.

The old rule was "does it need a CR", which split the gates across `verify` and
`change` for a reason no reader could recover from the names: a project not
running the CR workflow could not tell which four of the six applied to it.

The rule now is what a command reads. `verify *` answers from the DHF and runs
anywhere the DHF is — including a developer's laptop with no remote, no branch
and no PR. `workflow *` cannot answer without the repository. `build *` writes,
and may talk to either.

Checked by reachability rather than by name, so a `verify` command that grows a
`git diff` three calls down is caught. `build plan --pr` legitimately reads PR
comments, which is why the ban is on `verify` alone and not on "anything outside
workflow".
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

from medharness.cli import main
from medharness.services.gates import GATES

#: Reaching any of these means the command cannot answer without Git or GitHub.
VCS_MODULES = {
    "medharness.services.git",
    "medharness.services.pr_approval",
    "medharness.services.github_event",
    "medharness.services.github_session",
    "medharness.services.github_pr",
}


def _imports_in(tree: ast.AST) -> set[str]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
    return found


def _module_imports(name: str) -> set[str]:
    try:
        source = Path(importlib.import_module(name).__file__).read_text(encoding="utf-8")
    except (ImportError, OSError, TypeError):
        return set()
    return _imports_in(ast.parse(source))


def _seed(command) -> set[str]:
    """Modules the callback itself pulls in, by either import style.

    Module-level imports of its *defining* module do not count on their own:
    `cli/ci.py` imports the GitHub event parser for one command, and charging
    every command in the file with it would make the check meaningless. Only
    names the callback actually mentions are followed.
    """
    # click's @pass_context wraps the callback: getsource follows __wrapped__
    # but getfile does not, so the defining module has to be unwrapped by hand.
    target = inspect.unwrap(command.callback)
    source = inspect.getsource(target)
    source = "\n".join(
        line[4:] if line.startswith("    ") else line for line in source.splitlines()
    )
    body = ast.parse(source)
    seed = _imports_in(body)

    mentioned = {n.id for n in ast.walk(body) if isinstance(n, ast.Name)}
    defining = ast.parse(Path(inspect.getfile(target)).read_text(encoding="utf-8"))
    for node in ast.walk(defining):
        if isinstance(node, ast.ImportFrom) and node.module:
            if any((a.asname or a.name) in mentioned for a in node.names):
                seed.add(node.module)
    return seed


def _reaches(command) -> set[str]:
    seen: set[str] = set()
    queue = [m for m in _seed(command) if m.startswith(("medharness", "dhfkit"))]
    while queue:
        module = queue.pop()
        if module in seen:
            continue
        seen.add(module)
        queue += [
            m for m in _module_imports(module)
            if m.startswith(("medharness", "dhfkit")) and m not in seen
        ]
    return seen


def test_the_groups_are_not_empty() -> None:
    """Every assertion below is vacuous if a group failed to register."""
    for verb in ("verify", "build", "workflow"):
        assert main.commands[verb].commands, f"`{verb}` has no commands"


def test_no_verify_command_reaches_git_or_github() -> None:
    offenders = {
        name: sorted(_reaches(cmd) & VCS_MODULES)
        for name, cmd in main.commands["verify"].commands.items()
        if _reaches(cmd) & VCS_MODULES
    }
    assert not offenders, (
        f"`verify` must answer from the DHF alone, so it runs on a laptop with "
        f"no remote and no PR. These reach the repository: {offenders}"
    )


def test_every_workflow_command_reaches_git_or_github() -> None:
    """The converse. A workflow command that reads only the DHF is a verify one."""
    idle = [
        name for name, cmd in main.commands["workflow"].commands.items()
        if not _reaches(cmd) & VCS_MODULES
    ]
    assert not idle, (
        f"these sit under `workflow` but never read the repository, which is the "
        f"only thing that puts a command there: {idle}"
    )


def test_the_check_can_see_a_vcs_module() -> None:
    """Falsifier: if the walk resolved nothing, both tests above pass silently."""
    assert _reaches(main.commands["workflow"].commands["branch"]) & VCS_MODULES


def test_every_manifest_command_resolves() -> None:
    """The manifest names a path; the path must exist wherever it points."""
    for gate in GATES:
        group, _, name = gate["command"].partition(" ")
        assert group in main.commands, f"{gate['command']}: no group {group!r}"
        assert name in main.commands[group].commands, (
            f"{gate['command']} is in the manifest but not in the CLI"
        )


def test_the_manifest_is_not_empty() -> None:
    assert len(GATES) >= 5, f"only {len(GATES)} gates — the import is wrong"
