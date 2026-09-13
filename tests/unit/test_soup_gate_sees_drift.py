"""The SOUP gate checks the register against the manifests, not only CVEs.

Asking the two separately gives a dangerous answer. A package added to a
lockfile with no SOUP item is never queried for vulnerabilities at all — it does
not come back clean, it comes back absent. Scanning a stale register yields
stale conclusions, so §8.1.2's two halves are one gate.

Drift warns by default: a project backfilling its register should not be blocked
on day one, the same call `verify dhf` makes for coverage gaps.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from medharness.services.ci import soup_gate


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    import shutil

    templates = Path(__file__).resolve().parents[2] / "dhfkit" / "templates"
    root = tmp_path / "DHF"
    for src in ("config", "items"):
        if (templates / src).is_dir():
            shutil.copytree(templates / src, root / src, dirs_exist_ok=True)
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\nflask==3.0.0\n")
    return root


def _gate(dhf: Path, **kw):
    """No network: the drift half must work with osv.dev unreachable."""
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        return soup_gate(dhf, offline_mode="warn",
                         manifest_paths=[dhf.parent / "requirements.txt"], **kw)


class TestItSeesTheRegisterDrift:
    def test_a_package_with_no_soup_item_is_reported(self, dhf: Path) -> None:
        drift = _gate(dhf)["details"]["drift"]
        assert "flask" in drift["undocumented"]

    def test_the_manifests_were_actually_read(self, dhf: Path) -> None:
        assert _gate(dhf)["details"]["drift"]["manifests_read"] >= 2

    def test_drift_does_not_block_by_default(self, dhf: Path) -> None:
        result = _gate(dhf)
        assert result["details"]["drift"]["undocumented"]
        assert result["passed"] is True, (
            "drift blocked without --fail-on-drift; a project backfilling its "
            "register would be stopped on day one"
        )

    def test_fail_on_drift_blocks(self, dhf: Path) -> None:
        assert _gate(dhf, fail_on_drift=True)["passed"] is False


class TestTheDriftHalfIsLocal:
    def test_it_reports_drift_even_when_osv_is_unreachable(self, dhf: Path) -> None:
        """The register check needs no network; only the CVE half does."""
        result = _gate(dhf)
        assert result["details"]["drift"]["undocumented"], (
            "an osv.dev outage must not hide the fact that a component ships "
            "undocumented"
        )


class TestTheGateDoesNotWrite:
    def test_no_soup_item_is_created(self, dhf: Path) -> None:
        before = sorted(p.name for p in (dhf / "items").rglob("SOUP-*.yaml"))
        _gate(dhf, fail_on_drift=True)
        after = sorted(p.name for p in (dhf / "items").rglob("SOUP-*.yaml"))
        assert before == after, (
            "the gate wrote to the DHF it is judging; writing back is the "
            "`soup-sync` action's job"
        )
