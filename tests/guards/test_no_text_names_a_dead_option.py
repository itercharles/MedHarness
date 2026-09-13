"""An option named in a prompt, a doc, or a shipped workflow must exist.

`--author` and `--cr` on `dhfkit item create/update`, `--by` on `item
transition`, and `--author` on `release baseline` and `soup-sync` all ended at
an auto-commit path no entry point enabled, so the attribution was dropped on
the floor. Thirteen places across the prompts, `docs/adopting.md`, and the
scaffold's own workflow told the agent to pass one anyway.

`test_no_source_names_a_dead_command` checks command paths, and skips over
options on the way. This checks the options, and reads the files that one
excludes: prompts, docs, and templates.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

SEARCH = ("medharness/prompts/**/*.md", "docs/**/*.md",
          "dhfkit/templates/**/*.yml", "dhfkit/templates/**/*.md", "README.md")

#: Placeholders a template expands before anything runs.
PLACEHOLDER = re.compile(r"\{\{.*?\}\}|<[^>\s]*>")


def _invocations() -> list[tuple[str, str, tuple[str, ...], tuple[str, ...]]]:
    """(source, module, command path, long options) for each invocation found."""
    found: dict[tuple[str, tuple[str, ...], tuple[str, ...]], str] = {}
    for pattern in SEARCH:
        for path in sorted(ROOT.glob(pattern)):
            text = PLACEHOLDER.sub("X", path.read_text(encoding="utf-8"))
            # Shell continuations make one command out of several lines.
            text = re.sub(r"\\\n\s*", " ", text)
            for raw in text.splitlines():
                m = re.search(r"(?:python -m )?\b(dhfkit|medharness)\s+(.+)", raw)
                if not m:
                    continue
                module, rest = m.group(1), m.group(2)
                # Stop at a shell operator; what follows is a different command.
                rest = re.split(r"[|;>&]", rest)[0]
                tokens = rest.split()
                cmd: list[str] = []
                opts: list[str] = []
                i = 0
                while i < len(tokens):
                    tok = tokens[i].strip("`\"'.,")
                    if tok == "--dhf":
                        i += 2
                        continue
                    if tok.startswith("--"):
                        opt = tok.split("=")[0]
                        if re.fullmatch(r"--[a-z][a-z0-9-]*", opt):
                            opts.append(opt)
                    elif not tok.startswith("-"):
                        if not opts and re.fullmatch(r"[a-z][a-z0-9-]*", tok):
                            cmd.append(tok)
                    i += 1
                if cmd and opts:
                    key = (module, tuple(cmd[:2]), tuple(sorted(set(opts))))
                    found.setdefault(key, str(path.relative_to(ROOT)))
    return [(src, m, c, o) for (m, c, o), src in sorted(found.items(), key=lambda x: x[0])]


CALLS = _invocations()


def test_the_scan_found_invocations() -> None:
    assert len(CALLS) >= 10, (
        f"only {len(CALLS)} invocations with options found — the scan is broken, "
        f"so every assertion below passes vacuously"
    )


@pytest.mark.parametrize(
    "source,module,cmd,opts", CALLS,
    ids=[f"{m} {' '.join(c)}" for _s, m, c, _o in CALLS],
)
def test_every_named_option_exists(source: str, module: str,
                                   cmd: tuple[str, ...], opts: tuple[str, ...]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", module, "--dhf", str(ROOT / "DHF"), *cmd, "--help"],
        capture_output=True, text=True, cwd=ROOT,
    )
    output = result.stdout + result.stderr
    if "No such command" in output or "Usage:" not in output:
        pytest.skip(f"{module} {' '.join(cmd)} is not a command — that is the "
                    f"other guard's business")
    for opt in opts:
        assert opt in output, (
            f"{source} runs `{module} {' '.join(cmd)} {opt}`, "
            f"but that command has no {opt}"
        )
