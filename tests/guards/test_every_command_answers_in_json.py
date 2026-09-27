"""stdout is JSON, from every command; prose goes to stderr.

The README promised it. `doctor` printed a checklist to stdout unless given
`--json`, and `init` printed a banner and a walkthrough — whose "next steps"
named a removed command and an option the command no longer took. A caller
redirecting stdout to a file got text it could not parse.

Each command runs here as a person would run it, from a scaffolded project
root, so this also catches a command that cannot run from there at all.
Commands that call a model or GitHub are left out: they cannot run offline.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

#: (module, args). Each must exit 0 or 1 and put JSON on stdout.
COMMANDS = [
    ("medharness", ["verify", "dhf"]),
    ("medharness", ["verify", "tests", "--junit-dir", "test-results"]),
    ("medharness", ["verify", "completion", "--cr", "CR-001"]),
    ("medharness", ["workflow", "check-changes", "--cr", "CR-001", "--since-ref", "HEAD"]),
    ("medharness", ["workflow", "github-event", "--event", "event.json"]),
    ("medharness", ["context", "--cr", "CR-001"]),
    ("medharness", ["build", "dhf"]),
    ("medharness", ["build", "release", "--version", "0.1.0", "--out-dir", "release"]),
    ("medharness", ["doctor"]),
    ("dhfkit", ["item", "list"]),
    ("dhfkit", ["item", "get", "SRS-001"]),
    ("dhfkit", ["validate"]),
    ("dhfkit", ["doc", "SRS"]),
    ("dhfkit", ["sbom", "--stdout"]),
]


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("project")
    _scaffold_dhf(root)
    _replace_placeholders(root, "Json")
    (root / "test-results").mkdir()
    (root / "event.json").write_text(json.dumps({"inputs": {"cr_id": "CR-001"}}))
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "base"]):
        subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)
    return root


def _answer(module: str, args: list[str], cwd: Path):
    proc = subprocess.run([sys.executable, "-m", module, *args],
                          capture_output=True, text=True, cwd=cwd)
    assert "Traceback" not in proc.stderr, proc.stderr[-500:]
    assert proc.returncode in (0, 1), f"exit {proc.returncode}:\n{proc.stderr[-400:]}"
    assert proc.stdout.strip(), f"nothing on stdout:\n{proc.stderr[-400:]}"
    try:
        json.loads(proc.stdout)                 # one document, e.g. the SBOM
    except json.JSONDecodeError:
        for line in proc.stdout.splitlines():   # or one object per line: `item list`
            json.loads(line)
    return proc


@pytest.mark.parametrize("module,args", COMMANDS, ids=[f"{m} {' '.join(a[:2])}" for m, a in COMMANDS])
def test_stdout_is_json(module: str, args: list[str], project: Path) -> None:
    _answer(module, args, project)


def test_init_answers_in_json(tmp_path: Path) -> None:
    proc = _answer("medharness", ["init"], tmp_path)
    assert "DHF/config/global.yaml" in json.loads(proc.stdout)["created"]
