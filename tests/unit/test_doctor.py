"""`medharness doctor` — each check, without depending on the machine it runs on."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from medharness.commands.doctor import _auth_detail, run_doctor


def _by_name(report: dict) -> dict:
    return {c["check"]: c for c in report["checks"]}


def test_missing_clis_fail_their_checks() -> None:
    with patch("shutil.which", return_value=None):
        checks = _by_name(run_doctor())
    assert checks["claude_cli"] == {"check": "claude_cli", "passed": False,
                                    "detail": "claude not found on PATH"}
    assert checks["gh_cli_auth"]["passed"] is False


def test_gh_auth_goes_through_the_gh_helper() -> None:
    with patch("shutil.which", return_value="/usr/bin/x"), \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="claude 2.0", stderr="")), \
         patch("medharness.commands.doctor.gh",
               return_value=(0, "github.com\n  ✓ Logged in to github.com account octo")) as gh:
        checks = _by_name(run_doctor())
    gh.assert_called_once_with(["auth", "status"], timeout=5)
    assert checks["gh_cli_auth"] == {"check": "gh_cli_auth", "passed": True,
                                     "detail": "Logged in to github.com account octo"}


def test_auth_detail_prefers_the_account_line() -> None:
    assert _auth_detail("github.com\n  ✓ Logged in to github.com as octo\n  - Token: x", True) \
        == "Logged in to github.com as octo"
    assert _auth_detail("You are not logged into any GitHub hosts.", False) \
        == "You are not logged into any GitHub hosts."
    assert _auth_detail("", False) == "not authenticated"


def test_a_dhf_that_loads_is_healthy_and_one_that_does_not_is_named(tmp_path: Path) -> None:
    from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Trial")
    with patch("shutil.which", return_value=None):
        good = _by_name(run_doctor(tmp_path / "DHF"))
        bad = _by_name(run_doctor(tmp_path / "missing"))
    assert good["dhf_config"]["passed"] and good["dhf_adapter_init"]["passed"]
    assert not bad["dhf_config"]["passed"] and "failed" in bad["dhf_config"]["detail"]


def test_the_report_counts_what_failed() -> None:
    with patch("shutil.which", return_value=None):
        report = run_doctor()
    assert report["healthy"] is False
    assert report["summary"].endswith("2 failed")
