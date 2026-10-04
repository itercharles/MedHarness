"""Commands a run must pass, run by the harness and not left to the model."""

from __future__ import annotations

import subprocess
from pathlib import Path

TIMEOUT_SECONDS = 1800
_OUTPUT_TAIL = 4000


def run_checks(repo_root: Path, commands: tuple[str, ...]) -> list[dict]:
    """Run each command from ``repo_root``; ``exit_code`` is 124 on a timeout."""
    results = []
    for command in commands:
        try:
            done = subprocess.run(command, shell=True, cwd=str(repo_root), check=False, capture_output=True,
                                  text=True, timeout=TIMEOUT_SECONDS)
            code, output = done.returncode, (done.stdout or "") + (done.stderr or "")
        except subprocess.TimeoutExpired:
            code, output = 124, f"Timed out after {TIMEOUT_SECONDS} s."
        results.append({"command": command, "exit_code": code, "passed": code == 0,
                        "output": output.strip()[-_OUTPUT_TAIL:]})
    return results
