"""medharness doctor — environment and DHF health checks."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _check(name: str, passed: bool, detail: str) -> dict:
    return {"check": name, "passed": passed, "detail": detail}


def run_doctor(dhf_path: Optional[Path] = None) -> dict:
    """Run all health checks and return a structured report."""
    checks = []

    # Python version
    major, minor = sys.version_info[:2]
    checks.append(_check(
        "python_version",
        major == 3 and minor >= 11,
        f"Python {major}.{minor} (need >=3.11)",
    ))

    # medharness importable
    try:
        import importlib.metadata
        version = importlib.metadata.version("medharness")
        checks.append(_check("medharness_package", True, f"medharness=={version}"))
    except Exception as exc:
        checks.append(_check("medharness_package", False, f"import failed: {exc}"))

    # dhfkit importable (ships inside medharness; verify the import works)
    try:
        import dhfkit  # noqa: F401
        checks.append(_check("dhfkit_package", True, "dhfkit importable"))
    except Exception as exc:
        checks.append(_check("dhfkit_package", False, f"import failed: {exc}"))

    # Claude CLI
    if shutil.which("claude"):
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            detail = result.stdout.strip() or result.stderr.strip() or "ok"
            checks.append(_check("claude_cli", result.returncode == 0, detail))
        except Exception as exc:
            checks.append(_check("claude_cli", False, str(exc)))
    else:
        checks.append(_check("claude_cli", False, "claude not found on PATH"))

    # gh CLI
    if shutil.which("gh"):
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True, text=True, timeout=5,
            )
            passed = result.returncode == 0
            detail = (result.stdout + result.stderr).strip() or ("authenticated" if passed else "not authenticated")
            checks.append(_check("gh_cli_auth", passed, detail[:120]))
        except Exception as exc:
            checks.append(_check("gh_cli_auth", False, str(exc)))
    else:
        checks.append(_check("gh_cli_auth", False, "gh not found on PATH"))

    # DHF config (only if a DHF path was provided)
    if dhf_path is not None:
        try:
            from dhfkit.models.config import ProjectConfig
            config = ProjectConfig.load(dhf_path / "config")
            n_types = len(config.doc_types)
            checks.append(_check("dhf_config", True, f"{n_types} doc type(s) loaded from {dhf_path}"))
        except Exception as exc:
            checks.append(_check("dhf_config", False, f"config load failed: {exc}"))

        try:
            from dhfkit.local_adapter import LocalDHFAdapter
            adapter = LocalDHFAdapter(dhf_path)
            item_count = len(adapter.list_items())
            checks.append(_check("dhf_adapter_init", True, f"{item_count} item(s) loaded"))
        except Exception as exc:
            checks.append(_check("dhf_adapter_init", False, f"adapter init failed: {exc}"))

    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    failed = total - passed
    return {
        "checks": checks,
        "summary": f"{passed}/{total} checks passed" + (f", {failed} failed" if failed else ""),
        "healthy": failed == 0,
    }
