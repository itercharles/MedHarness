"""Source strings must not tell anyone to run a command that does not exist.

`validate traceability` was removed in 0.20.0 and five places still named it —
`dhfkit init --help`, a `design_validation` fix hint, and three strings in
`cr_generation` that go into the prompt. The AI was being told to run a command
that had not existed for four releases.

`test_documented_commands_exist` covers README and docs/. Nothing covered the
strings the product itself prints.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Options that take a value, so the token after them is not a subcommand.
VALUE_FLAGS = {"--dhf", "--cr", "--type", "--version", "--out-dir", "--junit-dir",
               "--manifest", "--since-ref", "--data", "--stage", "--pr", "--author"}


def _quoted_invocations() -> list[tuple[str, str, tuple[str, ...]]]:
    """Invocations, not prose.

    A line saying "medharness owns the process" is not a command. Requiring
    `--dhf` or `python -m` keeps the scan to text that is telling someone what
    to run — the first version matched English and reported eighteen commands
    that were never commands.
    """
    found: dict[tuple[str, tuple[str, ...]], str] = {}
    pattern = re.compile(
        r"(?:python -m )(dhfkit|medharness)\s+([^\"'`\n]+)"
        r"|\b(dhfkit|medharness)\s+(--dhf\s+\S+\s+[^\"'`\n]+)"
    )
    for path in sorted(ROOT.glob("medharness/**/*.py")) + sorted(ROOT.glob("dhfkit/**/*.py")):
        if "tests" in path.parts or "templates" in path.parts:
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            for m in pattern.finditer(raw):
                module = m.group(1) or m.group(3)
                rest = m.group(2) or m.group(4) or ""
                tokens, skip = [], False
                for arg in rest.split():
                    if skip:
                        skip = False
                        continue
                    if arg in VALUE_FLAGS:
                        skip = True
                        continue
                    if arg.startswith(("-", "<", "{", "\\")):
                        continue
                    # `f"... verify dhf\n"` ends the token with an escape the
                    # source carries but the shell never sees.
                    arg = arg.rstrip("\\n").rstrip("\\").strip("`\"'.,")
                    if not arg or arg == "...":
                        tokens = []  # `item ...` stands for the group, not a command
                        break
                    if not re.fullmatch(r"[a-z][\w-]*", arg):
                        break
                    tokens.append(arg)
                # A bare group name ("dhfkit validate") proves nothing: the group
                # exists whatever the subcommand was. Only a full path counts,
                # and a trailing English word is not one.
                tokens = [t for t in tokens if t not in {"then", "and", "or", "to"}]
                if tokens:
                    found.setdefault((module, tuple(tokens[:2])), path.name)
    return [(src, mod, toks) for (mod, toks), src in sorted(found.items(), key=lambda x: x[0])]


CALLS = _quoted_invocations()


def test_the_scan_found_invocations() -> None:
    assert len(CALLS) >= 5, f"only {len(CALLS)} found — the scan is broken"


@pytest.mark.parametrize(
    "source,module,tokens", CALLS,
    ids=[f"{m} {' '.join(t)}" for _s, m, t in CALLS],
)
def test_a_named_command_exists(source: str, module: str, tokens: tuple[str, ...]) -> None:
    # dhfkit exits on a missing --dhf before it parses the subcommand, so
    # without this the check never reaches "No such command" at all.
    result = subprocess.run(
        [sys.executable, "-m", module, "--dhf", str(ROOT / "DHF"), *tokens, "--help"],
        capture_output=True, text=True, cwd=ROOT,
    )
    output = result.stderr + result.stdout
    # A group's --help lists its subcommands and exits 0, so "No such command"
    # alone would let `dhfkit validate` stand in for a removed
    # `validate traceability`. Require the path to be a leaf.
    # A group's --help lists subcommands and exits 0, so "No such command"
    # alone would let `dhfkit validate` stand in for a removed
    # `validate traceability`. `dhfkit init` is a leaf and says so.
    is_group = "Commands:" in output
    if is_group:
        pytest.skip(
            f"{module} {' '.join(tokens)} is a group, not an invocation — prose "
            f"naming a group ('DHF mutations go through `dhfkit item` commands') "
            f"is not telling anyone to run it"
        )
    assert "No such command" not in output, (
        f"{source} tells a reader to run `{module} {' '.join(tokens)}`, "
        f"which does not exist"
    )
