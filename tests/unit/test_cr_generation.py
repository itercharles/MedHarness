"""Unit tests for medharness.services.cr_generation."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from medharness.services.cr_generation import (
    _get_pr_feedback,
    _run_claude,
    generate_code,
    generate_dhf,
)
from medharness.services.cr_impact import _record_design_impact_in_cr
from medharness.services.prompt_assembly import (
    MAX_DIFF_CHARS,
    _append_skills,
    _assemble_develop_prompt,
    _build_dhf_context_block,
    _load_prompt,
    _load_skill,
)


# ── Prompt loading ────────────────────────────────────────────────────────────

class TestLoadPrompt:
    def test_load_cr_develop(self):
        text = _load_prompt("cr_develop.md")
        assert "{{cr_id}}" in text

    def test_load_cr_generate_dhf(self):
        text = _load_prompt("cr_generate_dhf.md")
        assert "{{cr_id}}" in text
        assert "verification_criteria" in text
        assert "V-model" in text or "V-Model" in text
        assert "dhf item create" in text
        assert "dhf validate traceability" in text

    def test_missing_prompt_raises(self):
        import importlib.resources
        with pytest.raises(FileNotFoundError):
            ref = importlib.resources.files("medharness.prompts").joinpath("nonexistent.md")
            ref.read_text(encoding="utf-8")


class TestLoadSkill:
    @pytest.mark.parametrize("name", [
        "product_impact.md",
        "req_manage.md",
        "architecture_impact.md",
        "risk_impact.md",
        "soup_impact.md",
        "test_impact.md",
        "regulatory_impact.md",
        "security_impact.md",
        "usability_impact.md",
    ])
    def test_all_skills_loadable(self, name):
        text = _load_skill(name)
        assert len(text) > 100, f"{name} looks empty"

    def test_req_manage_has_quality_rules(self):
        text = _load_skill("req_manage.md")
        assert "No conflict" in text
        assert "Atomicity" in text
        assert "Verifiability" in text

    def test_req_manage_has_cli_syntax(self):
        text = _load_skill("req_manage.md")
        assert "dhf item create" in text
        assert "--cr" in text

    def test_architecture_impact_has_output_template(self):
        text = _load_skill("architecture_impact.md")
        assert "architecture" in text.lower()
        assert "Required" in text

    def test_risk_impact_has_output_template(self):
        text = _load_skill("risk_impact.md")
        assert "risk" in text.lower()
        assert "Required" in text


class TestAppendSkills:
    def test_appends_separator(self):
        result = _append_skills("base prompt")
        assert "---" in result

    def test_all_nine_skill_sections_present(self):
        result = _append_skills("base")
        for title in ["Product Impact", "Requirements Management", "Architecture Impact",
                      "Risk Impact", "SOUP Impact", "Test Impact",
                      "Regulatory Impact", "Security Impact", "Usability / HFE Impact"]:
            assert title in result, f"Missing skill section: {title}"

    def test_base_prompt_preserved(self):
        result = _append_skills("UNIQUE_BASE_CONTENT")
        assert "UNIQUE_BASE_CONTENT" in result


# ── Prompt assembly ───────────────────────────────────────────────────────────

class TestAssemblePrompts:
    def test_develop_substitutes_cr_id(self):
        prompt = _assemble_develop_prompt("CR-099")
        assert "CR-099" in prompt
        assert "{{cr_id}}" not in prompt

    def test_develop_does_not_include_dhf_skills(self):
        # develop prompt is for code; it should not include all 6 DHF impact skills
        prompt = _assemble_develop_prompt("CR-099")
        assert "Risk Impact" not in prompt
        assert "SOUP Impact" not in prompt

    def test_generate_dhf_substitutes_cr_id(self):
        from medharness.services.prompt_assembly import _assemble_generate_dhf_prompt
        prompt = _assemble_generate_dhf_prompt("CR-077")
        assert "CR-077" in prompt
        assert "{{cr_id}}" not in prompt

    def test_generate_dhf_includes_skills(self):
        from medharness.services.prompt_assembly import _assemble_generate_dhf_prompt
        prompt = _assemble_generate_dhf_prompt("CR-001")
        assert "Product Impact" in prompt or "product_impact" in prompt

    def test_generate_dhf_includes_verification_criteria_instructions(self):
        from medharness.services.prompt_assembly import _assemble_generate_dhf_prompt
        prompt = _assemble_generate_dhf_prompt("CR-001")
        assert "verification_criteria" in prompt


# ── PR feedback ───────────────────────────────────────────────────────────────

class TestGetPrFeedback:
    def test_returns_unavailable_when_no_env(self, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        result = _get_pr_feedback(42)
        assert "unavailable" in result["prompt_text"]
        assert result["diagnostics"]["comments_status"] == "skipped"
        assert result["warnings"][0]["code"] == "github_feedback_env_missing"

    def test_uses_github_token_fallback(self, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "tok")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.read.return_value = b"[]"
            mock_open.return_value = mock_resp
            result = _get_pr_feedback(1)
        data = json.loads(result["prompt_text"])
        assert "comments" in data
        assert "reviews" in data
        assert result["warnings"] == []

    def test_http_error_returns_error_payload(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs=None, fp=None
        )):
            result = _get_pr_feedback(99)
        assert result["diagnostics"]["comments_status"] == "http_error"
        assert any(w["code"] == "github_comments_http_error" for w in result["warnings"])

    def test_url_error_returns_error_payload(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            result = _get_pr_feedback(99)
        assert result["diagnostics"]["comments_status"] == "transport_error"
        assert any("offline" in w["message"] for w in result["warnings"])

    def test_invalid_json_returns_error_payload(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.read.return_value = b"{not-json"
            mock_open.return_value = mock_resp
            result = _get_pr_feedback(1)
        assert result["diagnostics"]["comments_status"] == "decode_error"
        assert any("decoded" in w["message"] for w in result["warnings"])


# ── Claude invocation ─────────────────────────────────────────────────────────

class TestRunClaude:
    def test_passes_prompt_to_claude(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")
            rc, output = _run_claude("my prompt")
        assert rc == 0
        args = mock_run.call_args[0][0]
        assert "claude" in args
        assert "my prompt" in args
        assert "--dangerously-skip-permissions" in args

    def test_includes_model_flag_when_env_set(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-7")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            _run_claude("prompt")
        args = mock_run.call_args[0][0]
        assert "--model" in args
        assert "claude-opus-4-7" in args

    def test_omits_model_flag_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            _run_claude("prompt")
        args = mock_run.call_args[0][0]
        assert "--model" not in args

    def test_combines_stdout_and_stderr(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="out", stderr="err")
            rc, output = _run_claude("x")
        assert rc == 1
        assert "out" in output
        assert "err" in output


# ── generate_dhf ──────────────────────────────────────────────────────────────

class TestGenerateDhf:
    def test_returns_dict_with_required_keys(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]):
            mock_claude.return_value = (0, "")
            result = generate_dhf("CR-050", dhf)
        assert result["cr_id"] == "CR-050"
        assert result["stage"] == "generate_dhf"
        assert result["outcome"] == "ok"
        assert result["errors"] == []
        for key in ("summary", "timing", "inputs", "steps", "artifacts", "diagnostics", "warnings"):
            assert key in result

    def test_happy_path_calls_claude_once(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]):
            mock_claude.return_value = (0, "")
            result = generate_dhf("CR-051", dhf)
        assert mock_claude.call_count == 1
        assert result["diagnostics"]["fix_attempted"] is False

    def test_fix_pass_triggered_when_validation_fails(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        first_errors = [{"field": "schema", "issue": "x", "fix": "y"}]
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   side_effect=[first_errors, []]):
            mock_claude.return_value = (0, "")
            result = generate_dhf("CR-052", dhf)
        assert mock_claude.call_count == 2
        fix_prompt = mock_claude.call_args_list[1][0][0]
        assert "deterministic validation" in fix_prompt
        assert result["outcome"] == "corrected"
        assert result["diagnostics"]["fix_attempted"] is True

    def test_residual_errors_yield_completed_with_errors(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        errors = [{"field": "schema", "issue": "x", "fix": "y"}]
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   side_effect=[errors, errors]):
            mock_claude.return_value = (0, "")
            result = generate_dhf("CR-053", dhf)
        assert result["outcome"] == "completed_with_errors"

    def test_generation_prompt_contains_cr_id_and_key_phrases(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]):
            mock_claude.return_value = (0, "")
            generate_dhf("CR-055", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "CR-055" in prompt
        assert "verification_criteria" in prompt
        assert "V-model" in prompt or "V-Model" in prompt

    def test_no_spec_path_validates_changed_items_not_spec(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        items_changed = {"created": ["SYS-001"], "updated": ["SRS-001"], "deleted": []}
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "")), \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes", return_value=items_changed), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]) as mock_validate:
            generate_dhf("CR-054", dhf)
        mock_validate.assert_called_once_with("CR-054", dhf, items_changed)

    def test_revision_mode_uses_pr_feedback(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation._get_pr_feedback") as mock_fb, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]):
            mock_claude.return_value = (0, "")
            mock_fb.return_value = {
                "prompt_text": "some review feedback",
                "diagnostics": {"attempted": True, "comments_status": "ok"},
                "warnings": [],
            }
            generate_dhf("CR-056", dhf, pr_number=12)
        mock_fb.assert_called_once_with(12)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "review feedback" in prompt.lower()
        assert "Product Impact" in prompt

    def test_design_impact_not_recorded_on_residual_errors(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        errors = [{"field": "schema", "issue": "x", "fix": "y"}]
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "")), \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   side_effect=[errors, errors]), \
             patch("medharness.services.cr_generation._record_design_impact_in_cr") as mock_impact:
            generate_dhf("CR-058", dhf)
        mock_impact.assert_not_called()


# ── generate_code ─────────────────────────────────────────────────────────────

class TestGenerateCode:
    """Pipeline: develop pass → deterministic check → fix-only on errors → soft review."""

    def test_returns_dict_with_required_keys(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]):
            mock_claude.return_value = (0, "")
            result = generate_code("CR-020", dhf)
        assert result["cr_id"] == "CR-020"
        assert result["stage"] == "develop"
        assert result["outcome"] == "ok"
        assert result["errors"] == []
        for key in ("summary", "timing", "inputs", "progress", "steps", "artifacts", "diagnostics", "warnings"):
            assert key in result, f"missing key: {key}"
        assert set(result["artifacts"]["files_changed"]) == {"created", "updated", "deleted"}

    def test_happy_path_runs_develop_then_review(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]):
            mock_claude.return_value = (0, "")
            result = generate_code("CR-021", dhf)
        assert mock_claude.call_count == 2
        assert result["outcome"] == "ok"
        review_prompt = mock_claude.call_args_list[1][0][0]
        assert "already passed" in review_prompt.lower()

    def test_fix_pass_triggered_when_validation_fails(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        first_errors = [{
            "field": "test_plan.needs_new_tc",
            "issue": "No newly added `@links:SRS-001` annotation found.",
            "fix": "Add a colocated test with @links:SRS-001",
        }]
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                   side_effect=[first_errors, []]):
            mock_claude.return_value = (0, "")
            result = generate_code("CR-024", dhf)
        assert mock_claude.call_count == 3
        fix_prompt = mock_claude.call_args_list[1][0][0]
        assert "@links:SRS-001" in fix_prompt
        assert "test annotations" in fix_prompt
        assert result["outcome"] == "corrected"
        assert result["errors"] == []

    def test_files_changed_populated_from_git(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        diff_output = (
            "A\tapps/client/src/foo.ts\n"
            "M\tapps/client/src/bar.tsx\n"
            "D\tpackages/shared-types/src/old.ts\n"
        )
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run",
                   return_value=MagicMock(stdout=diff_output, returncode=0)):
            mock_claude.return_value = (0, "")
            result = generate_code("CR-025", dhf)
        assert result["artifacts"]["files_changed"] == {
            "created": ["apps/client/src/foo.ts"],
            "updated": ["apps/client/src/bar.tsx"],
            "deleted": ["packages/shared-types/src/old.ts"],
        }

    def test_develop_prompt_passed_to_claude(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]):
            mock_claude.return_value = (0, "")
            generate_code("CR-022", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "CR-022" in prompt
        assert "CLAUDE.md" in prompt

    def test_revision_mode_uses_pr_feedback(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation._get_pr_feedback") as mock_fb, \
             patch("medharness.services.code_validation.validate_code",
                    return_value=[]):
            mock_claude.return_value = (0, "")
            mock_fb.return_value = {
                "prompt_text": '{"comments": [], "reviews": []}',
                "diagnostics": {"attempted": True, "comments_status": "ok", "reviews_status": "ok"},
                "warnings": [],
            }
            generate_code("CR-023", dhf, pr_number=7)
        mock_fb.assert_called_once_with(7)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "review feedback" in prompt.lower()

    def test_diff_injected_when_changes_exist(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        diff_output = "+console.log('new code')\n"
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                    return_value=[]), \
             patch("medharness.services.git.compute_diff",
                    return_value=diff_output):
            mock_claude.return_value = (0, "")
            generate_code("CR-026", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "Existing Implementation" in prompt
        assert "do not rewrite existing work" in prompt
        assert diff_output in prompt

    def test_diff_not_injected_when_no_changes(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                    return_value=[]), \
             patch("medharness.services.git.compute_diff",
                    return_value=""):
            mock_claude.return_value = (0, "")
            generate_code("CR-027", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "Existing Implementation" not in prompt

    def test_diff_not_injected_on_git_failure(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                    return_value=[]), \
             patch("medharness.services.git.compute_diff",
                    return_value=None):
            mock_claude.return_value = (0, "")
            generate_code("CR-028", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "Existing Implementation" not in prompt

    def test_diff_truncated_when_too_large(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        large_diff = "+" + "x" * (MAX_DIFF_CHARS + 1000)
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                    return_value=[]), \
             patch("medharness.services.git.compute_diff",
                    return_value=large_diff):
            mock_claude.return_value = (0, "")
            generate_code("CR-029", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "Existing Implementation" in prompt
        assert "truncated" in prompt
        assert large_diff not in prompt  # full diff not present


# ── DHF context block ──────────────────────────────────────────────────────────

class TestBuildDhfContextBlock:
    def test_returns_empty_on_adapter_failure(self, tmp_path):
        dhf = tmp_path / "nonexistent"
        result = _build_dhf_context_block(dhf)
        assert result == ""

    def test_includes_item_type_summary(self, tmp_path):
        from tests.fixtures.stub_adapter import StubDHFAdapter

        dhf = tmp_path / "DHF"
        dhf.mkdir()
        adapter = StubDHFAdapter()
        adapter.create_item({"id": "SYS-001", "title": "System req"})
        adapter.create_item({"id": "SRS-001", "title": "Software req"})
        with patch(
            "dhfkit.local_adapter.LocalDHFAdapter",
            return_value=adapter,
        ):
            result = _build_dhf_context_block(dhf)
        assert "Pre-computed DHF Context" in result
        assert "SYS:" in result or "SYS-" in result
        assert "SRS:" in result or "SRS-" in result

    def test_includes_all_dhf_items(self, tmp_path):
        from tests.fixtures.stub_adapter import StubDHFAdapter

        dhf = tmp_path / "DHF"
        dhf.mkdir()
        adapter = StubDHFAdapter()
        adapter.create_item({"id": "SYS-001", "title": "System requirement 1"})
        with patch(
            "dhfkit.local_adapter.LocalDHFAdapter",
            return_value=adapter,
        ):
            result = _build_dhf_context_block(dhf)
        assert "All DHF Items" in result
        assert "SYS-001 — System requirement 1" in result

    def test_caps_items_at_max(self, tmp_path):
        from tests.fixtures.stub_adapter import StubDHFAdapter

        dhf = tmp_path / "DHF"
        dhf.mkdir()
        adapter = StubDHFAdapter()
        for i in range(250):
            adapter.create_item({"id": f"SYS-{i+1:03d}", "title": f"Req {i}"})
        with patch(
            "dhfkit.local_adapter.LocalDHFAdapter",
            return_value=adapter,
        ):
            result = _build_dhf_context_block(dhf)
        assert "truncated" in result.lower()
        assert "200 of 250" in result
        # SYS-001 through SYS-200 should appear; SYS-250 should not.
        assert "SYS-001 —" in result
        assert "SYS-200 —" in result
        assert "SYS-250 —" not in result

    def test_includes_coverage_gaps_when_uncovered(self, tmp_path):
        from tests.fixtures.stub_adapter import StubDHFAdapter

        dhf = tmp_path / "DHF"
        dhf.mkdir()
        adapter = StubDHFAdapter()
        adapter.create_item({"id": "SYS-001", "title": "Uncovered req"})
        with patch(
            "dhfkit.local_adapter.LocalDHFAdapter",
            return_value=adapter,
        ):
            result = _build_dhf_context_block(dhf)
        assert "manual_verification_candidates" in result
        assert "SYS-001" in result

    def test_no_coverage_warning_when_all_covered(self, tmp_path):
        from tests.fixtures.stub_adapter import StubDHFAdapter

        dhf = tmp_path / "DHF"
        dhf.mkdir()
        adapter = StubDHFAdapter()
        adapter.create_item({"id": "SYS-001", "title": "Covered req"})
        adapter.create_item({"id": "TC-SYS-001", "title": "Test case",
                             "verifies": ["SYS-001"]})
        with patch(
            "dhfkit.local_adapter.LocalDHFAdapter",
            return_value=adapter,
        ):
            result = _build_dhf_context_block(dhf)
        assert "manual_verification_candidates" not in result

    def test_coverage_uses_system_requirement_role_code(self, tmp_path):
        from tests.fixtures.stub_adapter import StubDHFAdapter

        dhf = tmp_path / "DHF"
        dhf.mkdir()
        adapter = StubDHFAdapter()
        adapter.create_item({"id": "SYSREQ-001", "title": "Custom-prefix req"})
        adapter._item_types.append({
            "display_name": "System Requirement", "code": "SYSREQ",
            "prefix": "SYSREQ-", "role": "system_requirement",
            "parent_types": [], "has_verification": True,
            "lifecycle": None, "fields": [],
        })
        with patch(
            "dhfkit.local_adapter.LocalDHFAdapter",
            return_value=adapter,
        ):
            result = _build_dhf_context_block(dhf)
        assert "System requirements (tier 2): SYSREQ" in result


