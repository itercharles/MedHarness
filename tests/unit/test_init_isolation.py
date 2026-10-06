"""Tests for scaffold isolation, gitignore scope, and coverage-pair strictness.

Most of these pin regressions introduced by the previous review round, plus one
older defect that made `medharness init` permanently corrupt the installed
package: the documented setup creates `.venv` **inside** the project, and
`replace_placeholders` walked the whole tree, so it rewrote
`site-packages/dhfkit/templates` in place. Every later project scaffolded from
that virtualenv then inherited the first project's name.
"""

from __future__ import annotations

import re

from pathlib import Path

import pytest

from dhfkit.item_store import ItemStore
from medharness.services.traceability_report import verification_evidence
from medharness.scaffold import (
    replace_placeholders,
    scaffold_dhf,
    _write_gitignore,
)


def _safe_read(path) -> str:
    try:
        return path.read_text()
    except (OSError, UnicodeDecodeError):
        return ""


class TestScaffoldIsolation:
    def test_venv_contents_are_not_rewritten(self, tmp_path: Path) -> None:
        """The documented setup puts .venv inside the project root."""
        installed = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages" / "dhfkit"
        installed.mkdir(parents=True)
        template = installed / "context.md"
        template.write_text("# AI Agent Context — {{project_name}}")

        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Trial")

        assert template.read_text() == "# AI Agent Context — {{project_name}}"

    def test_project_files_are_still_rewritten(self, tmp_path: Path) -> None:
        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Trial")
        assert "{{project_name}}" not in (tmp_path / "DHF" / "README.md").read_text()

    @pytest.mark.parametrize("outside", [".venv/x.md", "node_modules/pkg/x.yaml", "docs/x.md", "x.md", "src/lib/x.yml"])
    def test_a_file_outside_the_dhf_is_left_alone(self, tmp_path: Path, outside: str) -> None:
        """Only what `scaffold_dhf` wrote is rewritten: no list of directories to avoid."""
        stray = tmp_path / outside
        stray.parent.mkdir(parents=True, exist_ok=True)
        stray.write_text("{{project_name}}")

        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Trial")

        assert stray.read_text() == "{{project_name}}"

    def test_nested_dhf_files_are_still_rewritten(self, tmp_path: Path) -> None:
        nested = tmp_path / "DHF" / "documents" / "specs"
        nested.mkdir(parents=True)
        (nested / "x.md").write_text("{{project_name}} {{medharness_version}}")

        replace_placeholders(tmp_path, "Trial")

        assert "{{" not in (nested / "x.md").read_text() and "Trial" in (nested / "x.md").read_text()

    def test_unreadable_file_does_not_abort_the_scaffold(self, tmp_path: Path) -> None:
        scaffold_dhf(tmp_path)
        locked = tmp_path / "DHF" / "locked.md"
        locked.write_text("{{project_name}}")
        locked.chmod(0o000)
        try:
            replace_placeholders(tmp_path, "Trial")  # must not raise
        finally:
            locked.chmod(0o644)

        # "does not abort" is a claim about the files after the unreadable one.
        # Without this the test passes if replace_placeholders becomes a no-op.
        substituted = [
            f for f in (tmp_path / "DHF").rglob("*")
            if f.is_file() and f != locked and "Trial" in _safe_read(f)
        ]
        assert substituted, "no file was substituted — the walk stopped or never ran"
        assert not any("{{project_name}}" in _safe_read(f)
                       for f in (tmp_path / "DHF").rglob("*")
                       if f.is_file() and f != locked), \
            "a placeholder survived past the unreadable file"


class TestGitignoreScope:
    def test_result_store_is_not_ignored(self, tmp_path: Path) -> None:
        """DHF/test-results/ holds verification evidence and must be committed."""
        patterns = _write_gitignore(tmp_path).read_text().splitlines()
        assert "test-results/" not in patterns
        assert "/test-results/" in patterns

    def test_root_level_test_output_is_still_ignored(self, tmp_path: Path) -> None:
        assert "/test-results/" in _write_gitignore(tmp_path).read_text()


class TestTheReleaseGate:
    def test_the_release_gate_skips_a_layer_the_project_omits(self, tmp_path: Path) -> None:
        """`build release` checks the DHF with coverage gaps failing. A project
        entitled to omit the use-case layer must still be releasable."""
        from medharness.services.verify_dhf import ci_structural_gate

        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Trial")
        dhf = tmp_path / "DHF"
        config = dhf / "config" / "global.yaml"
        config.write_text(config.read_text().replace("omit_doc_types: []", "omit_doc_types: [UC]"))
        for stale in (dhf / "items" / "00_uc").glob("*.yaml"):
            stale.unlink()
        # CRS derived from UC-001; the link would now dangle for another reason.
        for crs in (dhf / "items" / "01_crs").glob("*.yaml"):
            crs.write_text(re.sub(r"derives_from:\n(  - UC-\d+\n)+", "", crs.read_text()))

        gate = ci_structural_gate(dhf, strict=True)
        assert not [e for e in gate["errors"] if "UC" in e], gate["errors"]


class TestPrefixConsistency:
    """services/traceability_report.py must agree with dhfkit's Item.prefix."""

    def test_core_resolves_multi_segment_prefixes(self, tmp_path: Path) -> None:
        scaffold_dhf(tmp_path)
        replace_placeholders(tmp_path, "Trial")
        dhf = tmp_path / "DHF"
        # The loader resolves the doc-type code from the ID's first segment, so
        # a multi-segment prefix must keep that segment as its code: code VER,
        # prefix VER-SW-. get_item_type() is keyed on the full prefix, which is
        # where split("-")[0] and rsplit("-", 1)[0] diverge.
        (dhf / "config" / "doc_types").mkdir(exist_ok=True)
        (dhf / "config" / "doc_types" / "versw.yaml").write_text(
            "code: VER\nname: Software Verification\nprefix: VER-SW-\n"
            "directory: 14_versw\nhas_verification: true\n"
            "properties:\n- id\n- name: title\n  format: short_text\n"
            "  label: Title\n"
        )
        items = dhf / "items" / "14_versw"
        items.mkdir(parents=True)
        (items / "VER-SW-001.yaml").write_text("id: VER-SW-001\ntitle: Verify something\n")

        junit = tmp_path / "ver.xml"
        junit.write_text(
            "<testsuites><testsuite name='s' tests='1'>"
            "<testcase classname='t' name='test_x'><properties>"
            "<property name='medharness.links' value='VER-SW-001'/>"
            "</properties></testcase></testsuite></testsuites>"
        )
        adapter = ItemStore(dhf)
        evidence = verification_evidence(adapter.list_items(), adapter.list_item_types(), [junit])

        assert evidence["VER-SW-001"]["verification_status"] == "verified"
