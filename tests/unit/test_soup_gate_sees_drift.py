"""The SOUP gate checks the register against the manifests, not only CVEs.

Asking the two separately gives a dangerous answer. A package added to a
lockfile with no SOUP item is never queried for vulnerabilities at all — it does
not come back clean, it comes back absent. Scanning a stale register yields
stale conclusions, so §8.1.2's two halves are one gate.

Drift warns by default: a project backfilling its register should not be blocked
on day one, the same call `verify dhf` makes for coverage gaps.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.services.verify_soup import soup_gate


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
    @pytest.mark.dhf_links("SRS-053")
    @pytest.mark.dhf_testing("T1")
    def test_a_package_with_no_soup_item_is_reported(self, dhf: Path) -> None:
        drift = _gate(dhf)["details"]["drift"]
        assert "flask" in drift["undocumented"]

    def test_the_manifests_were_actually_read(self, dhf: Path) -> None:
        assert _gate(dhf)["details"]["drift"]["manifests_read"] >= 2

    @pytest.mark.dhf_links("SRS-053")
    @pytest.mark.dhf_testing("T1")
    def test_drift_does_not_block_by_default(self, dhf: Path) -> None:
        result = _gate(dhf)
        assert result["details"]["drift"]["undocumented"]
        assert result["passed"] is True, (
            "drift blocked without --strict; a project backfilling its "
            "register would be stopped on day one"
        )

    @pytest.mark.dhf_links("SRS-053")
    @pytest.mark.dhf_testing("T2")
    def test_fail_on_drift_blocks(self, dhf: Path) -> None:
        assert _gate(dhf, strict=True)["passed"] is False

    @pytest.mark.dhf_links("SRS-053")
    @pytest.mark.dhf_testing("T3")
    def test_a_component_at_another_version_fails_under_strict_naming_both(self, dhf: Path) -> None:
        manifest = dhf.parent / "requirements.txt"
        manifest.write_text("example-library==2.0.0\n")
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            result = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "soup", "--strict",
                                               "--manifest", str(manifest), "--offline-mode", "warn"])
        answer = json.loads(result.stdout.splitlines()[0])
        assert result.exit_code == 1
        assert "SOUP-001 records 1.0.0, manifests resolve 2.0.0" in answer["errors"], answer["errors"]


class TestTheDriftHalfIsLocal:
    @pytest.mark.dhf_links("SRS-053")
    @pytest.mark.dhf_testing("T4")
    def test_it_reports_drift_even_when_osv_is_unreachable(self, dhf: Path) -> None:
        """The register check needs no network; only the CVE half does."""
        result = _gate(dhf)
        assert result["details"]["drift"]["undocumented"], (
            "an osv.dev outage must not hide the fact that a component ships "
            "undocumented"
        )


class TestTheGateDoesNotWrite:
    @pytest.mark.dhf_links("SRS-054")
    @pytest.mark.dhf_testing("T4")
    def test_no_soup_item_is_created(self, dhf: Path) -> None:
        before = sorted(p.name for p in (dhf / "items").rglob("SOUP-*.yaml"))
        _gate(dhf, strict=True)
        after = sorted(p.name for p in (dhf / "items").rglob("SOUP-*.yaml"))
        assert before == after, (
            "the gate wrote to the DHF it is judging; writing back is the "
            "`build soup` action's job"
        )


class TestAnEntryWithNoPurposeIsNotDocumented:
    """§8.1.2 asks why a component is used, not merely that it is listed.

    build soup used to write `purpose: "Dependency from PyPI"` into every item it
    created. That satisfied "is it in the register" and answered nothing — the
    register looked complete while saying nothing a reviewer could use. It now
    leaves the field empty, and the gate says so.
    """

    @pytest.mark.dhf_links("SRS-053")
    @pytest.mark.dhf_testing("T5")
    def test_an_empty_purpose_is_reported(self, dhf: Path) -> None:
        (dhf / "items" / "09_soup").mkdir(parents=True, exist_ok=True)
        (dhf / "items" / "09_soup" / "SOUP-900.yaml").write_text(
            "id: SOUP-900\ntype: SOUP\ntitle: bare\nname: bare\n"
            "version: 1.0.0\npurpose: ''\n"
        )
        assert "SOUP-900" in _gate(dhf)["details"]["drift"]["undescribed"]

    def test_a_described_entry_is_not_reported(self, dhf: Path) -> None:
        undescribed = _gate(dhf)["details"]["drift"]["undescribed"]
        described = [
            it.stem for it in (dhf / "items").rglob("SOUP-*.yaml")
            if "purpose:" in it.read_text() and "purpose: ''" not in it.read_text()
        ]
        for soup_id in described:
            assert soup_id not in undescribed


def test_soup_sync_does_not_invent_a_purpose() -> None:
    """The regression, read from the source rather than trusted."""
    import inspect

    from medharness.services import soup_sync

    import ast

    # Reads the string literals, not the text: the comment above the field
    # quotes the old placeholder as the thing not to do, and a word search
    # trips on its own explanation.
    tree = ast.parse(inspect.getsource(soup_sync.sync_soup_items))
    literals = [
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    joined = [n for n in ast.walk(tree) if isinstance(n, ast.JoinedStr)]
    for node in joined:
        literals += [
            v.value for v in node.values
            if isinstance(v, ast.Constant) and isinstance(v.value, str)
        ]
    assert not any("Dependency from" in lit for lit in literals), (
        "build soup fills in a purpose again; an invented answer to 'why is this "
        "component used' is worse than a visible gap"
    )
