"""The SBOM is a claim about a standard, so it is checked against the standard.

`dhfkit/tests/schema/bom-1.6.schema.json` is the official CycloneDX schema,
vendored so the check runs offline and in CI. A document that says
`"bomFormat": "CycloneDX"` and does not validate is a false claim in a file
someone will submit to a regulator.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.cli import main
from dhfkit.sbom import build_sbom, purl_for, write_sbom

SCHEMA_DIR = Path(__file__).parent / "schema"


def _soup(dhf: Path, soup_id: str, body: str) -> None:
    d = dhf / "items" / "09_soup"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{soup_id}.yaml").write_text(f"id: {soup_id}\n{body}")


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    CliRunner().invoke(main, ["--dhf", str(dhf), "init"])
    import importlib.resources as resources

    src = resources.files("dhfkit").joinpath("templates/config/doc_types/soup.yaml")
    (dhf / "config" / "doc_types" / "soup.yaml").write_bytes(src.read_bytes())
    return dhf


class TestPurl:
    """A wrong purl resolves against a real registry, so absence beats a guess."""

    @pytest.mark.parametrize("name,version,ecosystem,expected", [
        ("requests", "2.31.0", "PyPI", "pkg:pypi/requests@2.31.0"),
        ("lodash", "4.17.21", "npm", "pkg:npm/lodash@4.17.21"),
        ("@types/node", "20.11.0", "npm", "pkg:npm/@types/node@20.11.0"),
        ("org.apache.commons:commons-lang3", "3.14.0", "Maven",
         "pkg:maven/org.apache.commons/commons-lang3@3.14.0"),
        ("serde", "1.0.0", "crates.io", "pkg:cargo/serde@1.0.0"),
        ("github.com/pkg/errors", "0.9.1", "Go", "pkg:golang/github.com%2Fpkg%2Ferrors@0.9.1"),
    ])
    def test_known_ecosystems(self, name, version, ecosystem, expected) -> None:
        assert purl_for(name, version, ecosystem) == expected

    def test_an_unmapped_ecosystem_gets_no_purl(self) -> None:
        assert purl_for("internal-lib", "1.0.0", "Conan") is None

    def test_a_nameless_component_gets_no_purl(self) -> None:
        assert purl_for("", "1.0.0", "PyPI") is None

    def test_a_slash_without_a_scope_is_not_an_npm_namespace(self) -> None:
        """Only a leading '@' makes a '/' a scope."""
        assert purl_for("a/b", "1.0", "npm") == "pkg:npm/a%2Fb@1.0"


class TestDocumentValidatesAgainstTheSpec:
    @pytest.fixture(scope="class")
    def validator(self):
        # A hard import, not importorskip: this is the check that backs the
        # claim `"bomFormat": "CycloneDX"`, and a check that disappears when a
        # dependency is absent is not one. jsonschema is in [dev] and CI
        # installs it.
        import jsonschema
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7

        schema = json.loads((SCHEMA_DIR / "bom-1.6.schema.json").read_text())
        registry = Registry().with_resources([
            (f"http://cyclonedx.org/schema/{n}",
             Resource(contents=json.loads((SCHEMA_DIR / n).read_text()),
                      specification=DRAFT7))
            for n in ("jsf-0.82.schema.json", "spdx.schema.json")
        ])
        return jsonschema.Draft7Validator(schema, registry=registry)

    def _validate(self, validator, document) -> None:
        errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
        assert not errors, "\n".join(
            f"{list(e.path)}: {e.message}" for e in errors[:5]
        )

    def test_a_full_component_validates(self, validator) -> None:
        document = build_sbom([{
            "id": "SOUP-001", "name": "requests", "version": "2.31.0",
            "ecosystem": "PyPI", "license": "Apache-2.0",
            "manufacturer": "PSF", "homepage": "https://example.org",
            "purpose": "HTTP client.",
            "accepted_vulns": [{"id": "GHSA-x", "rationale": "not reachable"}],
        }], project_name="Trial", tool_version="1.0.0")
        self._validate(validator, document)

    def test_a_bare_component_validates(self, validator) -> None:
        """Only name and version are guaranteed present on a SOUP item."""
        document = build_sbom(
            [{"id": "SOUP-002", "name": "x", "version": "1.0"}],
            project_name="Trial", tool_version="1.0.0",
        )
        self._validate(validator, document)

    def test_an_empty_register_validates(self, validator) -> None:
        document = build_sbom([], project_name="Trial", tool_version="1.0.0")
        self._validate(validator, document)


class TestRegenerationIsNotADiff:
    """A DHF repository exists to show what changed.

    Document generation had this exact defect: a regeneration on a later day
    looked like a content change. An SBOM carries both a timestamp and a serial
    number, so it can churn twice over.
    """

    def test_the_serial_number_is_derived_from_content(self) -> None:
        items = [{"id": "SOUP-001", "name": "a", "version": "1.0"}]
        first = build_sbom(items, project_name="P", tool_version="1.0.0")
        second = build_sbom(items, project_name="P", tool_version="1.0.0")
        assert first["serialNumber"] == second["serialNumber"]

    def test_the_serial_number_changes_when_components_do(self) -> None:
        base = build_sbom([{"id": "S1", "name": "a", "version": "1.0"}],
                          project_name="P", tool_version="1.0.0")
        bumped = build_sbom([{"id": "S1", "name": "a", "version": "1.1"}],
                            project_name="P", tool_version="1.0.0")
        assert base["serialNumber"] != bumped["serialNumber"]

    def test_an_unchanged_sbom_keeps_its_timestamp(self, tmp_path: Path) -> None:
        items = [{"id": "SOUP-001", "name": "a", "version": "1.0"}]
        out = tmp_path / "sbom.cdx.json"

        first = build_sbom(items, project_name="P", tool_version="1.0.0",
                           timestamp="2026-01-01T00:00:00Z")
        write_sbom(first, out)

        later = build_sbom(items, project_name="P", tool_version="1.0.0",
                           timestamp="2026-09-04T00:00:00Z")
        _path, changed = write_sbom(later, out)

        assert changed is False, "regenerating an identical SBOM rewrote the file"
        assert json.loads(out.read_text())["metadata"]["timestamp"] == \
            "2026-01-01T00:00:00Z"

    def test_a_changed_sbom_is_written(self, tmp_path: Path) -> None:
        out = tmp_path / "sbom.cdx.json"
        write_sbom(build_sbom([{"id": "S1", "name": "a", "version": "1.0"}],
                              project_name="P", tool_version="1.0.0"), out)
        _path, changed = write_sbom(
            build_sbom([{"id": "S1", "name": "a", "version": "1.1"}],
                       project_name="P", tool_version="1.0.0"), out)
        assert changed is True
        assert json.loads(out.read_text())["components"][0]["version"] == "1.1"


class TestCLI:
    def test_it_reads_the_soup_register(self, dhf: Path) -> None:
        _soup(dhf, "SOUP-001",
              "title: requests\nname: requests\nversion: '2.31.0'\necosystem: PyPI\n")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "sbom"])
        assert r.exit_code == 0, r.output

        payload = json.loads(r.stdout.splitlines()[0])
        assert payload["components"] == 1
        document = json.loads(Path(payload["path"]).read_text())
        assert document["components"][0]["purl"] == "pkg:pypi/requests@2.31.0"

    def test_only_soup_items_become_components(self, dhf: Path) -> None:
        """The register is SOUP; a requirement is not a supplied component."""
        _soup(dhf, "SOUP-001", "title: a\nname: a\nversion: '1'\necosystem: PyPI\n")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "sbom"])
        document = json.loads(Path(json.loads(r.stdout.splitlines()[0])["path"]).read_text())
        assert {c["bom-ref"] for c in document["components"]} == {"SOUP-001"}

    def test_unmapped_ecosystems_are_warned_about(self, dhf: Path) -> None:
        """A component with no purl is the one a consumer cannot resolve."""
        _soup(dhf, "SOUP-001", "title: x\nname: x\nversion: '1'\necosystem: Conan\n")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "sbom"])
        assert json.loads(r.stdout.splitlines()[0])["without_purl"] == 1
        assert "no purl" in r.stderr

    def test_stdout_mode_writes_no_file(self, dhf: Path) -> None:
        _soup(dhf, "SOUP-001", "title: a\nname: a\nversion: '1'\necosystem: PyPI\n")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "sbom", "--stdout"])
        assert r.exit_code == 0
        assert json.loads(r.stdout)["bomFormat"] == "CycloneDX"
        assert not (dhf / "sbom.cdx.json").exists()
