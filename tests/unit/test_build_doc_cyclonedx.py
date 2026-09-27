"""`build doc SOUP --format cyclonedx`: the SOUP register as an SBOM."""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.tests.fixtures import bare_dhf
from medharness.cli import main


def _soup(dhf: Path, soup_id: str, body: str) -> None:
    d = dhf / "items" / "09_soup"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{soup_id}.yaml").write_text(f"id: {soup_id}\n{body}")


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    return bare_dhf(tmp_path / "DHF")


def _sbom(dhf: Path, *extra: str):
    r = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "doc", "SOUP",
                                  "--format", "cyclonedx", *extra])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.stdout.splitlines()[0])
    return r, payload, json.loads(Path(payload["cyclonedx_path"]).read_text())


def test_it_reads_the_soup_register(dhf: Path) -> None:
    _soup(dhf, "SOUP-001", "title: requests\nname: requests\nversion: '2.31.0'\necosystem: PyPI\n")
    _, payload, document = _sbom(dhf)
    assert payload["components"] == 1
    assert document["components"][0]["purl"] == "pkg:pypi/requests@2.31.0"


def test_it_lands_beside_the_other_exports(dhf: Path, tmp_path: Path) -> None:
    _, payload, _ = _sbom(dhf)
    assert Path(payload["cyclonedx_path"]) == dhf / "documents" / "exports" / "sbom.cdx.json"
    _, payload, _ = _sbom(dhf, "--out-dir", str(tmp_path / "out"))
    assert Path(payload["cyclonedx_path"]) == tmp_path / "out" / "sbom.cdx.json"


def test_only_soup_items_become_components(dhf: Path) -> None:
    """The register is SOUP; a requirement is not a supplied component."""
    _soup(dhf, "SOUP-001", "title: a\nname: a\nversion: '1'\necosystem: PyPI\n")
    _, _, document = _sbom(dhf)
    assert {c["bom-ref"] for c in document["components"]} == {"SOUP-001"}


def test_unmapped_ecosystems_are_warned_about(dhf: Path) -> None:
    """A component with no purl is the one a consumer cannot resolve."""
    _soup(dhf, "SOUP-001", "title: x\nname: x\nversion: '1'\necosystem: Conan\n")
    r, payload, _ = _sbom(dhf)
    assert payload["without_purl"] == 1
    assert "no purl" in r.stderr


def test_the_tool_version_is_the_installed_package(dhf: Path) -> None:
    _, _, document = _sbom(dhf)
    assert document["metadata"]["tools"]["components"][0]["version"] == version("medharness")


def test_only_soup_has_an_sbom(dhf: Path) -> None:
    r = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "doc", "SRS", "--format", "cyclonedx"])
    assert r.exit_code == 2
    assert "only SOUP" in r.output
