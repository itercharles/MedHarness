"""Unit tests for the CLI _format_summary helper used by ci generate-* commands."""

from __future__ import annotations

from medharness.cli.ci import _format_summary


def _result(**overrides) -> dict:
    base = {
        "cr_id": "CR-001",
        "stage": "design",
        "outcome": "ok",
        "diagnostics": {"fix_attempted": False},
        "errors": [],
        "timing": {"started_at": "2026-05-10T00:00:00+00:00", "elapsed_ms": 1234},
        "artifacts": {},
    }
    base.update(overrides)
    return base


class TestFormatSummary:
    def test_happy_path(self):
        out = _format_summary("Design", "generated", "CR-001", _result())
        assert out.startswith("OK Design generated for CR-001 (")
        assert "outcome: ok" in out
        assert "1234 ms" in out
        assert "errors:" not in out

    def test_residual_errors_surface_count(self):
        result = _result(
            outcome="completed_with_errors",
            errors=[
                {"field": "schema", "issue": "x"},
                {"field": "traceability.orphan", "issue": "y"},
            ],
        )
        out = _format_summary("Design", "generated", "CR-001", result)
        assert "errors: 2" in out

    def test_items_changed_counts_surface(self):
        result = _result(artifacts={"items_changed": {
            "created": ["SYS-001"],
            "updated": ["SRS-002", "SRS-003"],
            "deleted": [],
        }})
        out = _format_summary("Design", "generated", "CR-001", result)
        assert "DHF: +1 ~2 -0" in out

    def test_files_changed_counts_surface(self):
        result = _result(stage="develop", artifacts={"files_changed": {
            "created": ["a.ts"],
            "updated": [],
            "deleted": ["b.ts"],
        }})
        out = _format_summary("Implementation", "generated", "CR-001", result)
        assert "files: +1 ~0 -1" in out

    def test_empty_change_buckets_omitted(self):
        result = _result(artifacts={"items_changed": {"created": [], "updated": [], "deleted": []}})
        out = _format_summary("Design", "generated", "CR-001", result)
        assert "DHF:" not in out

    def test_tool_error_uses_error_prefix(self):
        out = _format_summary("Spec", "generated", "CR-001", _result(outcome="tool_error"))
        assert out.startswith("ERROR Spec generated for CR-001 (")
