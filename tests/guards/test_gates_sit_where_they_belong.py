"""A verify command answers from what is on the machine: the DHF and the working tree.

The old rules drew the line at "does it need a CR", then at "does it read Git".
Both put `verify changes` — a diff of the working tree, which a developer runs
before committing — in a CI-only group. The line that matters is GitHub: a
`verify` command runs on a laptop with no remote and no PR, so it may read the
local repository but never the pull request.

Checked by reachability rather than by name, so a `verify` command that grows a
`gh` call three calls down is caught. `build plan --pr` legitimately reads PR
reviews, which is why the ban is on `verify` alone.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

from medharness.cli import main
from medharness.services.gates import GATES

#: Reaching any of these means the command cannot answer without GitHub.
GITHUB_MODULES = {
    "medharness.services.pr_feedback",
    "medharness.services.gh",
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
    `cli/build.py` imports what one command needs, and charging
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
    for verb in ("verify", "build"):
        assert main.commands[verb].commands, f"`{verb}` has no commands"


def test_no_verify_command_reaches_github() -> None:
    offenders = {
        name: sorted(_reaches(cmd) & GITHUB_MODULES)
        for name, cmd in main.commands["verify"].commands.items()
        if _reaches(cmd) & GITHUB_MODULES
    }
    assert not offenders, (
        f"`verify` must answer from the machine it runs on, so it works on a "
        f"laptop with no remote and no PR. These reach GitHub: {offenders}"
    )


def test_the_check_can_see_a_github_module() -> None:
    """Falsifier: if the walk resolved nothing, the test above passes silently."""
    assert _reaches(main.commands["build"].commands["plan"]) & GITHUB_MODULES


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
