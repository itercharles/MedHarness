"""Tests for scaffold isolation, gitignore scope, and coverage-pair strictness.

Most of these pin regressions introduced by the previous review round, plus one
older defect that made `medharness init` permanently corrupt the installed
package: the documented setup creates `.venv` **inside** the project, and
`_replace_placeholders` walked the whole tree, so it rewrote
`site-packages/dhfkit/templates` in place. Every later project scaffolded from
that virtualenv then inherited the first project's name.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dhfkit.local_adapter import LocalDHFAdapter
from medharness.core import MedHarnessCore
from medharness.workflows.init import (
    _NON_SCAFFOLD_DIRS,
    _replace_placeholders,
    _scaffold_dhf,
    _substitutable_files,
    _write_gitignore,
)


class TestScaffoldIsolation:
    def test_venv_contents_are_not_rewritten(self, tmp_path: Path) -> None:
        """The documented setup puts .venv inside the project root."""
        installed = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages" / "dhfkit"
        installed.mkdir(parents=True)
        template = installed / "context.md"
        template.write_text("# AI Agent Context — {{project_name}}")

        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Trial")

        assert template.read_text() == "# AI Agent Context — {{project_name}}"

    def test_project_files_are_still_rewritten(self, tmp_path: Path) -> None:
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Trial")
        assert "{{project_name}}" not in (tmp_path / "AI-harness" / "context.md").read_text()

    @pytest.mark.parametrize("pruned", sorted(_NON_SCAFFOLD_DIRS))
    def test_every_pruned_dir_is_skipped(self, tmp_path: Path, pruned: str) -> None:
        nested = tmp_path / pruned / "deep"
        nested.mkdir(parents=True)
        (nested / "x.md").write_text("{{project_name}}")

        assert not [p for p in _substitutable_files(tmp_path) if pruned in p.parts]

    def test_walk_still_reaches_nested_project_files(self, tmp_path: Path) -> None:
        nested = tmp_path / "DHF" / "documents" / "specs"
        nested.mkdir(parents=True)
        (nested / "x.md").write_text("{{project_name}}")

        found = {p.name for p in _substitutable_files(tmp_path)}
        assert "x.md" in found

    def test_unreadable_file_does_not_abort_the_scaffold(self, tmp_path: Path) -> None:
        _scaffold_dhf(tmp_path)
        locked = tmp_path / "DHF" / "locked.md"
        locked.write_text("{{project_name}}")
        locked.chmod(0o000)
        try:
            _replace_placeholders(tmp_path, "Trial")  # must not raise
        finally:
            locked.chmod(0o644)


class TestGitignoreScope:
    def test_result_store_is_not_ignored(self, tmp_path: Path) -> None:
        """DHF/test-results/ holds verification evidence and must be committed."""
        patterns = _write_gitignore(tmp_path).read_text().splitlines()
        assert "test-results/" not in patterns
        assert "/test-results/" in patterns

    def test_root_level_test_output_is_still_ignored(self, tmp_path: Path) -> None:
        assert "/test-results/" in _write_gitignore(tmp_path).read_text()


class TestCoveragePairStrictness:
    """User-supplied pairs are strict; the implicit V-model defaults are not."""

    @pytest.fixture
    def core(self, tmp_path: Path) -> MedHarnessCore:
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Trial")
        return MedHarnessCore(LocalDHFAdapter(tmp_path / "DHF"))

    def test_strict_reports_an_unknown_type_as_an_error(self, core: MedHarnessCore) -> None:
        result = core.check_coverage([("NOPE", "CRS")], strict=True)
        assert result["passed"] is False
        assert "unknown document type" in result["results"][0]["error"]

    def test_lenient_skips_a_layer_the_project_omits(self, core: MedHarnessCore) -> None:
        """A DHF entitled to omit a V-model layer must not fail the gate for it."""
        result = core.check_coverage([("NOPE", "CRS")], strict=False)
        assert result["passed"] is True
        assert "not configured" in result["results"][0]["skipped"]

    def test_configured_pairs_evaluate_the_same_either_way(self, core: MedHarnessCore) -> None:
        strict = core.check_coverage([("SYS", "SRS")], strict=True)
        lenient = core.check_coverage([("SYS", "SRS")], strict=False)
        assert strict["results"][0]["total"] == lenient["results"][0]["total"] > 0

    def test_acceptance_gate_uses_lenient_defaults(self, tmp_path: Path) -> None:
        from medharness._helpers import _run_acceptance_gate

        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Trial")
        dhf = tmp_path / "DHF"
        # A project that does not model the use-case layer at all.
        (dhf / "config" / "doc_types" / "uc.yaml").unlink()
        for stale in (dhf / "items" / "00_uc").glob("*.yaml"):
            stale.unlink()

        core = MedHarnessCore(LocalDHFAdapter(dhf))
        result = _run_acceptance_gate(core, [], ())

        uc_rows = [
            r for r in result["coverage"]["results"] if r["parent_type"] == "UC"
        ]
        assert uc_rows and uc_rows[0]["passed"] is True
        assert "not configured" in uc_rows[0]["skipped"]


class TestPrefixConsistency:
    """core.py and _helpers.py must agree with dhfkit's Item.prefix."""

    def test_core_resolves_multi_segment_prefixes(self, tmp_path: Path) -> None:
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Trial")
        dhf = tmp_path / "DHF"
        # The loader resolves the doc-type code from the ID's first segment, so
        # a multi-segment prefix must keep that segment as its code: code VER,
        # prefix VER-SW-. get_item_type() is keyed on the full prefix, which is
        # where split("-")[0] and rsplit("-", 1)[0] diverge.
        (dhf / "config" / "doc_types" / "versw.yaml").write_text(
            "code: VER\nname: Software Verification\nprefix: VER-SW-\n"
            "directory: 14_versw\nhas_verification: true\n"
            "properties:\n- id\n- name: title\n  format: short_text\n"
            "  label: Title\n"
        )
        items = dhf / "items" / "14_versw"
        items.mkdir(parents=True)
        (items / "VER-SW-001.yaml").write_text("id: VER-SW-001\ntitle: Verify something\n")

        adapter = LocalDHFAdapter(dhf)
        adapter._result_store.record_executions(
            [{"tc_id": "TC-VER-001", "testing_status": "PASS", "links": ["VER-SW-001"]}]
        )
        core = MedHarnessCore(LocalDHFAdapter(dhf))

        assert core.get_item("VER-SW-001")["verification_status"] == "verified"
