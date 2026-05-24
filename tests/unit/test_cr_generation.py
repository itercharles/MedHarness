"""Unit tests for medharness.services.cr_generation."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from medharness.services.cr_generation import (
    LLMConfig,
    _auto_post_pr_feedback,
    _build_review_result,
    _get_pr_feedback,
    _model_label,
    _parse_review_data,
    _read_design_review_data,
    _resolve_stage_llm,
    _run_claude,
    _run_claude_step,
    _run_openai_compatible,
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
        assert "python -m dhfkit" in text
        assert "validate traceability" in text

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
        assert "item create" in text
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

    def test_review_design_substitutes_cr_id(self):
        from medharness.services.prompt_assembly import _assemble_review_design_prompt
        prompt = _assemble_review_design_prompt("CR-042")
        assert "CR-042" in prompt
        assert "{{cr_id}}" not in prompt

    def test_review_design_covers_three_criteria(self):
        from medharness.services.prompt_assembly import _assemble_review_design_prompt
        prompt = _assemble_review_design_prompt("CR-001")
        assert "Necessity" in prompt
        assert "Strategy" in prompt or "strategy" in prompt
        assert "SWDD" in prompt

    def test_review_design_does_not_write_files(self):
        from medharness.services.prompt_assembly import _assemble_review_design_prompt
        prompt = _assemble_review_design_prompt("CR-001")
        assert "do not modify any dhf item files" in prompt.lower()


# ── _parse_review_data ────────────────────────────────────────────────────────

class TestParseReviewData:
    def test_approved_verdict(self):
        text = "**Verdict:** Approved"
        assert _parse_review_data(text)["verdict"] == "approved"

    def test_needs_revision_verdict(self):
        text = "**Verdict:** Needs Revision"
        assert _parse_review_data(text)["verdict"] == "needs_revision"

    def test_unknown_when_no_verdict_line(self):
        assert _parse_review_data("Some review text without a verdict")["verdict"] == "unknown"

    def test_verdict_case_insensitive(self):
        assert _parse_review_data("**Verdict:** APPROVED")["verdict"] == "approved"
        assert _parse_review_data("**Verdict:** needs revision")["verdict"] == "needs_revision"

    def test_extracts_issue_lines(self):
        text = (
            "**Verdict:** Needs Revision\n\n"
            "## Issues\n"
            "- [ ] `src/foo.ts:12`: missing null check\n"
            "- [ ] `src/bar.ts:5`: wrong return type\n"
        )
        result = _parse_review_data(text)
        assert result["issues"] == [
            "`src/foo.ts:12`: missing null check",
            "`src/bar.ts:5`: wrong return type",
        ]

    def test_no_issues_returns_empty_list(self):
        text = "**Verdict:** Approved\n\nNo issues found."
        assert _parse_review_data(text)["issues"] == []

    def test_empty_string_returns_unknown_no_issues(self):
        result = _parse_review_data("")
        assert result == {"verdict": "unknown", "issues": []}

    def test_returns_both_verdict_and_issues(self):
        text = "**Verdict:** Needs Revision\n- [ ] item-1: problem"
        result = _parse_review_data(text)
        assert result["verdict"] == "needs_revision"
        assert len(result["issues"]) == 1


# ── _read_design_review_data ──────────────────────────────────────────────────

class TestReadDesignReviewData:
    def test_missing_file_returns_unknown(self, tmp_path):
        result = _read_design_review_data(tmp_path, "CR-999")
        assert result == {"verdict": "unknown", "issues": []}

    def test_reads_approved_verdict(self, tmp_path):
        review_dir = tmp_path / "docs" / "reviews"
        review_dir.mkdir(parents=True)
        (review_dir / "CR-001-Design-Review.md").write_text(
            "# Design Review: CR-001\n\n**Verdict:** Approved\n\nNo issues found.\n"
        )
        result = _read_design_review_data(tmp_path, "CR-001")
        assert result["verdict"] == "approved"
        assert result["issues"] == []

    def test_reads_needs_revision_with_issues(self, tmp_path):
        review_dir = tmp_path / "docs" / "reviews"
        review_dir.mkdir(parents=True)
        (review_dir / "CR-002-Design-Review.md").write_text(
            "**Verdict:** Needs Revision\n\n"
            "## Issues\n"
            "- [ ] `SWDD-003`: implementation_notes incomplete\n"
            "- [ ] `SRS-005`: out of scope for this CR\n"
        )
        result = _read_design_review_data(tmp_path, "CR-002")
        assert result["verdict"] == "needs_revision"
        assert len(result["issues"]) == 2
        assert "`SWDD-003`: implementation_notes incomplete" in result["issues"]


# ── _build_review_result ──────────────────────────────────────────────────────

class TestBuildReviewResult:
    def test_approved_on_first_pass(self):
        log = [{"cycle": 1, "verdict": "approved", "issues": []}]
        result = _build_review_result("Design", log)
        assert result["cycles"] == [{"cycle": 1, "verdict": "approved", "issues": []}]
        assert result["narrative"][0] == "Design completed."
        assert "Review: approved." in result["narrative"][1]

    def test_needs_revision_then_approved(self):
        log = [
            {"cycle": 1, "verdict": "needs_revision", "issues": ["item-1: bad", "item-2: wrong"]},
            {"cycle": 2, "verdict": "approved", "issues": []},
        ]
        result = _build_review_result("Implementation", log)
        assert "2 issues found" in result["narrative"][1]
        assert "fix pass triggered" in result["narrative"][1]
        assert "all issues resolved" in result["narrative"][2]

    def test_singular_issue_label(self):
        log = [{"cycle": 1, "verdict": "needs_revision", "issues": ["file.ts:1: error"]}]
        result = _build_review_result("Design", log)
        assert "1 issue found" in result["narrative"][1]
        assert "issues found" not in result["narrative"][1].replace("1 issue found", "")

    def test_unknown_verdict(self):
        log = [{"cycle": 1, "verdict": "unknown", "issues": []}]
        result = _build_review_result("Design", log)
        assert "unknown" in result["narrative"][1]

    def test_cycles_list_matches_log(self):
        log = [
            {"cycle": 1, "verdict": "needs_revision", "issues": ["x"]},
            {"cycle": 2, "verdict": "approved", "issues": []},
        ]
        result = _build_review_result("Design", log)
        assert len(result["cycles"]) == 2
        assert result["cycles"][0]["cycle"] == 1
        assert result["cycles"][1]["cycle"] == 2

    def test_empty_log_produces_only_stage_line(self):
        result = _build_review_result("Design", [])
        assert result["narrative"] == ["Design completed."]
        assert result["cycles"] == []


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
        json_out = '{"result": "done", "session_id": "sid-1"}'
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=json_out, stderr="")
            rc, output, session_id = _run_claude("my prompt")
        assert rc == 0
        assert output == "done"
        assert session_id == "sid-1"
        args = mock_run.call_args[0][0]
        assert "claude" in args
        assert "my prompt" in args
        assert "--dangerously-skip-permissions" in args
        assert "--output-format" in args
        assert "json" in args

    def test_includes_model_flag_when_env_set(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-7")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"result":"","session_id":""}', stderr="")
            _run_claude("prompt")
        args = mock_run.call_args[0][0]
        assert "--model" in args
        assert "claude-opus-4-7" in args

    def test_omits_model_flag_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"result":"","session_id":""}', stderr="")
            _run_claude("prompt")
        args = mock_run.call_args[0][0]
        assert "--model" not in args

    def test_resume_session_flag_passed(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"result":"ok","session_id":"sid-2"}', stderr="")
            _run_claude("prompt", resume_session="sid-prior")
        args = mock_run.call_args[0][0]
        assert "--resume" in args
        assert "sid-prior" in args

    def test_no_resume_flag_when_empty(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"result":"ok","session_id":""}', stderr="")
            _run_claude("prompt")
        args = mock_run.call_args[0][0]
        assert "--resume" not in args

    def test_fallback_on_invalid_json(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
            rc, output, session_id = _run_claude("prompt")
        assert rc == 0
        assert output == "not json"
        assert session_id == ""

    def test_combines_stdout_and_stderr(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="out", stderr="err")
            rc, output, session_id = _run_claude("x")
        assert rc == 1
        assert "out" in output
        assert "err" in output
        assert session_id == ""


# ── _run_claude_step ──────────────────────────────────────────────────────────

class TestRunClaudeStep:
    def test_tool_label_is_claude_for_anthropic(self):
        steps: list[dict] = []
        with patch("medharness.services.cr_generation._run_llm", return_value=(0, "", "")):
            _run_claude_step(
                name="test_step",
                prompt="p",
                steps=steps,
                warnings=[],
                critical=False,
                llm_config=LLMConfig(provider="anthropic", model="claude-opus-4-7"),
            )
        assert steps[0]["details"]["tool"] == "claude"

    def test_tool_label_is_model_label_for_non_anthropic(self):
        steps: list[dict] = []
        with patch("medharness.services.cr_generation._run_llm", return_value=(0, "", "")):
            _run_claude_step(
                name="test_step",
                prompt="p",
                steps=steps,
                warnings=[],
                critical=False,
                llm_config=LLMConfig(provider="openai", model="gpt-4o"),
            )
        assert steps[0]["details"]["tool"] == "openai:gpt-4o"

    def test_warning_code_is_not_cli_missing_for_non_anthropic(self):
        """Non-anthropic provider failure must not emit claude_cli_missing warning."""
        warnings: list[dict] = []
        with patch("medharness.services.cr_generation._run_llm", return_value=(1, "api error", "")):
            _run_claude_step(
                name="test_step",
                prompt="p",
                steps=[],
                warnings=warnings,
                critical=False,
                llm_config=LLMConfig(provider="openai", model="gpt-4o", api_key="sk"),
            )
        assert warnings
        assert all(w["code"] != "claude_cli_missing" for w in warnings)
        assert warnings[0]["code"] == "claude_step_failed"


# ── generate_dhf ──────────────────────────────────────────────────────────────

class TestGenerateDhf:
    @pytest.fixture(autouse=True)
    def stub_session(self, monkeypatch):
        monkeypatch.setattr("medharness.services.cr_generation.get_session", lambda pr: "")
        monkeypatch.setattr("medharness.services.cr_generation.put_session", lambda pr, sid: None)

    def test_returns_dict_with_required_keys(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]):
            mock_claude.return_value = (0, "", "")
            result = generate_dhf("CR-050", dhf)
        assert result["cr_id"] == "CR-050"
        assert result["stage"] == "generate_dhf"
        assert result["outcome"] == "ok"
        assert result["errors"] == []
        for key in ("summary", "timing", "inputs", "steps", "artifacts", "diagnostics", "warnings"):
            assert key in result

    def test_happy_path_calls_claude_twice(self, tmp_path):
        # generation + design review; no fix pass on happy path
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]):
            mock_claude.return_value = (0, "", "")
            result = generate_dhf("CR-051", dhf)
        assert mock_claude.call_count == 2
        assert result["diagnostics"]["fix_attempted"] is False

    def test_fix_pass_triggered_when_validation_fails(self, tmp_path):
        # generation + fix + design review = 3 Claude calls
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        first_errors = [{"field": "schema", "issue": "x", "fix": "y"}]
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   side_effect=[first_errors, []]):
            mock_claude.return_value = (0, "", "")
            result = generate_dhf("CR-052", dhf)
        assert mock_claude.call_count == 3
        fix_prompt = mock_claude.call_args_list[1][0][0]
        assert "deterministic validation" in fix_prompt
        assert result["outcome"] == "corrected"
        assert result["diagnostics"]["fix_attempted"] is True

    def test_design_review_loop_fixes_and_reruns_until_approved(self, tmp_path):
        # review_1 → needs_revision → fix_1 → review_2 → approved
        # Claude calls: generation + review_1 + fix_1 + review_2 = 4
        dhf = tmp_path / "DHF"
        dhf.mkdir()

        data_sequence = iter([
            {"verdict": "needs_revision", "issues": ["SYS-003: out of scope", "SWDD-002: notes unclear"]},
            {"verdict": "approved", "issues": []},
        ])

        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]), \
             patch("medharness.services.cr_generation._read_design_review_data",
                   side_effect=lambda repo_root, cr_id: next(data_sequence)):
            mock_claude.return_value = (0, "", "")
            result = generate_dhf("CR-060", dhf)

        assert mock_claude.call_count == 4
        step_names = [s["name"] for s in result["steps"]]
        assert "run_design_review" in step_names
        assert "run_design_fix_1" in step_names
        assert "run_design_review_2" in step_names
        assert result["diagnostics"]["design_review_verdict"] == "approved"
        assert result["diagnostics"]["design_review_cycles"] == 2

        fix_prompt = mock_claude.call_args_list[2][0][0]
        assert "Design-Review.md" in fix_prompt

        dr = result["design_review"]
        assert dr["cycles"][0] == {"cycle": 1, "verdict": "needs_revision", "issues": ["SYS-003: out of scope", "SWDD-002: notes unclear"]}
        assert dr["cycles"][1] == {"cycle": 2, "verdict": "approved", "issues": []}
        assert "2 issues found" in dr["narrative"][1]
        assert "all issues resolved" in dr["narrative"][2]

    def test_design_review_loop_stops_at_max_cycles(self, tmp_path):
        # verdict always needs_revision → loop runs _MAX_DESIGN_REVIEW_CYCLES times then stops
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]), \
             patch("medharness.services.cr_generation._read_design_review_data",
                   return_value={"verdict": "needs_revision", "issues": ["item-1: problem"]}):
            mock_claude.return_value = (0, "", "")
            result = generate_dhf("CR-061", dhf)

        # generation + (fix + review) * (MAX-1) + final_review
        from medharness.services.cr_generation import _MAX_DESIGN_REVIEW_CYCLES
        expected_claude_calls = 1 + (_MAX_DESIGN_REVIEW_CYCLES - 1) * 2 + 1
        assert mock_claude.call_count == expected_claude_calls
        assert result["diagnostics"]["design_review_cycles"] == _MAX_DESIGN_REVIEW_CYCLES
        assert len(result["design_review"]["cycles"]) == _MAX_DESIGN_REVIEW_CYCLES

    def test_dhf_validation_reruns_after_design_review_fix(self, tmp_path):
        # P1b: validate_generate_dhf must run after each review fix, not just before the loop.
        # Simulate: initial ok → review needs_revision → fix introduces a new schema error.
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        new_error = [{"field": "schema", "issue": "broken after review fix", "fix": "update item"}]
        review_data_sequence = iter([
            {"verdict": "needs_revision", "issues": ["SYS-001: out of scope"]},
            {"verdict": "approved", "issues": []},
        ])
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   side_effect=[[], new_error]) as mock_validate, \
             patch("medharness.services.cr_generation._read_design_review_data",
                   side_effect=lambda repo_root, cr_id: next(review_data_sequence)):
            mock_claude.return_value = (0, "", "")
            result = generate_dhf("CR-083", dhf)

        assert mock_validate.call_count == 2
        assert result["diagnostics"]["final_error_count"] == 1
        step_names = [s["name"] for s in result["steps"]]
        assert "validate_after_review_fix_1" in step_names

    def test_artifacts_collected_after_review_loop(self, tmp_path):
        # P2: items_changed snapshot must be taken after the review loop so that items
        # added by review-fix passes appear in artifacts.items_changed.
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        items_before = {"created": ["SYS-001"], "updated": [], "deleted": []}
        items_after = {"created": ["SYS-001", "SRS-002"], "updated": [], "deleted": []}
        collect_calls = iter([
            items_before,  # after initial generation
            items_after,   # after review fix (P1b re-validate)
            items_after,   # final collect_artifacts
        ])
        review_data_sequence = iter([
            {"verdict": "needs_revision", "issues": ["SYS-001: incomplete"]},
            {"verdict": "approved", "issues": []},
        ])
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   side_effect=lambda *_: next(collect_calls)), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]), \
             patch("medharness.services.cr_generation._read_design_review_data",
                   side_effect=lambda repo_root, cr_id: next(review_data_sequence)):
            mock_claude.return_value = (0, "", "")
            result = generate_dhf("CR-084", dhf)

        assert result["artifacts"]["items_changed"] == items_after
        assert "SRS-002" in result["artifacts"]["items_changed"]["created"]

    def test_residual_errors_yield_completed_with_errors(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        errors = [{"field": "schema", "issue": "x", "fix": "y"}]
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   side_effect=[errors, errors]):
            mock_claude.return_value = (0, "", "")
            result = generate_dhf("CR-053", dhf)
        assert result["outcome"] == "completed_with_errors"

    def test_generation_prompt_contains_cr_id_and_key_phrases(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]):
            mock_claude.return_value = (0, "", "")
            generate_dhf("CR-055", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "CR-055" in prompt
        assert "verification_criteria" in prompt
        assert "V-model" in prompt or "V-Model" in prompt

    def test_no_spec_path_validates_changed_items_not_spec(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        items_changed = {"created": ["SYS-001"], "updated": ["SRS-001"], "deleted": []}
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "", "")), \
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
            mock_claude.return_value = (0, "", "")
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
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "", "")), \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   side_effect=[errors, errors]), \
             patch("medharness.services.cr_generation._record_design_impact_in_cr") as mock_impact:
            generate_dhf("CR-058", dhf)
        mock_impact.assert_not_called()

    def test_fix_pass_resumes_from_initial_session(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        resume_sessions_captured: list[str] = []

        def _stub(prompt: str, *, resume_session: str = "", model: str = "") -> tuple[int, str, str]:
            resume_sessions_captured.append(resume_session)
            return 0, "", f"sess-{len(resume_sessions_captured)}"

        first_errors = [{"field": "f", "issue": "i", "fix": "x"}]
        with patch("medharness.services.cr_generation._run_claude", side_effect=_stub), \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   side_effect=[first_errors, []]):
            generate_dhf("CR-059", dhf)
        assert resume_sessions_captured[0] == "", "initial step must start fresh (no prior session)"
        assert resume_sessions_captured[1] == "sess-1", "fix-pass must resume from initial step session"

    def test_auto_posts_errors_on_completed_with_errors(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        posted_bodies: list[str] = []
        errors = [{"field": "crs", "issue": "no CRS item", "fix": "create CRS-001"}]
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "", "")), \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   return_value=errors), \
             patch("medharness.services.cr_generation.post_pr_comment",
                   side_effect=lambda pr, body, **kw: posted_bodies.append(body) or "https://err-url"):
            result = generate_dhf("CR-099", dhf, pr_number=55)
        assert result["outcome"] == "completed_with_errors"
        assert any("Validation errors" in b for b in posted_bodies)
        assert "https://err-url" in result["pr_comments"]

    def test_no_auto_post_without_pr_number(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        errors = [{"field": "crs", "issue": "no CRS item", "fix": "create CRS-001"}]
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "", "")), \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf",
                   return_value=errors), \
             patch("medharness.services.cr_generation.post_pr_comment") as mock_post:
            result = generate_dhf("CR-099", dhf, pr_number=None)
        mock_post.assert_not_called()
        assert "pr_comments" not in result


# ── generate_code ─────────────────────────────────────────────────────────────

class TestGenerateCode:
    """Pipeline: develop pass → deterministic check → fix-only on errors → soft review."""

    @pytest.fixture(autouse=True)
    def stub_session(self, monkeypatch):
        monkeypatch.setattr("medharness.services.cr_generation.get_session", lambda pr: "")
        monkeypatch.setattr("medharness.services.cr_generation.put_session", lambda pr, sid: None)

    def test_returns_dict_with_required_keys(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]):
            mock_claude.return_value = (0, "", "")
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
            mock_claude.return_value = (0, "", "")
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
            mock_claude.return_value = (0, "", "")
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
            mock_claude.return_value = (0, "", "")
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
            mock_claude.return_value = (0, "", "")
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
            mock_claude.return_value = (0, "", "")
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
            mock_claude.return_value = (0, "", "")
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
            mock_claude.return_value = (0, "", "")
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
            mock_claude.return_value = (0, "", "")
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
            mock_claude.return_value = (0, "", "")
            generate_code("CR-029", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "Existing Implementation" in prompt
        assert "truncated" in prompt
        assert large_diff not in prompt  # full diff not present

    def test_first_revision_with_no_stored_marker_starts_fresh(self, tmp_path, monkeypatch):
        """First --pr rerun on a PR with no stored session must not pass --resume."""
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        # Simulate get_session returning "" (no marker comment yet — including the
        # fixed case where jq previously emitted "null" and we now return "")
        monkeypatch.setattr("medharness.services.cr_generation.get_session", lambda pr: "")
        resume_sessions_captured: list[str] = []

        def _stub(prompt: str, *, resume_session: str = "", model: str = "") -> tuple[int, str, str]:
            resume_sessions_captured.append(resume_session)
            return 0, "", f"sess-{len(resume_sessions_captured)}"

        with patch("medharness.services.cr_generation._run_claude", side_effect=_stub), \
             patch("medharness.services.cr_generation._get_pr_feedback",
                   return_value={"prompt_text": "", "diagnostics": {}, "warnings": []}), \
             patch("medharness.services.code_validation.validate_code", return_value=[]):
            generate_code("CR-030", dhf, pr_number=99)
        assert all(s == "" for s in resume_sessions_captured[:1]), (
            f"initial develop step must start fresh; got resume_session={resume_sessions_captured[0]!r}"
        )

    def test_auto_posts_warnings_when_pr_number_given(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        posted_bodies: list[str] = []
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "", "")), \
             patch("medharness.services.cr_generation._get_pr_feedback",
                   return_value={"prompt_text": "", "diagnostics": {}, "warnings": []}), \
             patch("medharness.services.code_validation.validate_code", return_value=[]), \
             patch("medharness.services.cr_generation.post_pr_comment",
                   side_effect=lambda pr, body, **kw: posted_bodies.append(body) or "url") as mock_post:
            result = generate_code("CR-099", dhf, pr_number=55)
        assert mock_post.call_count == 0, "no warnings → no comment expected"
        assert result.get("pr_comments") == []

    def test_auto_posts_errors_on_completed_with_errors(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        posted_bodies: list[str] = []
        errors = [{"field": "test_links", "issue": "missing @links", "fix": "add @links"}]
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "", "")), \
             patch("medharness.services.cr_generation._get_pr_feedback",
                   return_value={"prompt_text": "", "diagnostics": {}, "warnings": []}), \
             patch("medharness.services.code_validation.validate_code", return_value=errors), \
             patch("medharness.services.cr_generation.post_pr_comment",
                   side_effect=lambda pr, body, **kw: posted_bodies.append(body) or "https://comment-url"):
            result = generate_code("CR-099", dhf, pr_number=55)
        assert result["outcome"] == "completed_with_errors"
        assert any("Validation errors" in b for b in posted_bodies), f"expected error comment; got: {posted_bodies}"
        assert "https://comment-url" in result["pr_comments"]

    def test_no_auto_post_without_pr_number(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        errors = [{"field": "test_links", "issue": "missing @links", "fix": "add @links"}]
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "", "")), \
             patch("medharness.services.code_validation.validate_code", return_value=errors), \
             patch("medharness.services.cr_generation.post_pr_comment") as mock_post:
            result = generate_code("CR-099", dhf, pr_number=None)
        mock_post.assert_not_called()
        assert "pr_comments" not in result

    def test_code_review_loop_fixes_and_reruns_until_approved(self, tmp_path):
        # review_1 → needs_revision → fix_1 → review_2 → approved
        # Claude calls: develop + review_1 + fix_1 + review_2 = 4
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        data_sequence = iter([
            {"verdict": "needs_revision", "issues": ["src/foo.ts:12: missing null check"]},
            {"verdict": "approved", "issues": []},
        ])
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code", return_value=[]), \
             patch("medharness.services.cr_generation._parse_review_data",
                   side_effect=lambda text: next(data_sequence)):
            mock_claude.return_value = (0, "", "")
            result = generate_code("CR-070", dhf)

        assert mock_claude.call_count == 4
        step_names = [s["name"] for s in result["steps"]]
        assert "run_review" in step_names
        assert "run_code_fix_1" in step_names
        assert "run_review_2" in step_names
        assert result["diagnostics"]["code_review_verdict"] == "approved"
        assert result["diagnostics"]["code_review_cycles"] == 2

        fix_prompt = mock_claude.call_args_list[2][0][0]
        assert "issues" in fix_prompt.lower()

        cr = result["code_review"]
        assert cr["cycles"][0] == {"cycle": 1, "verdict": "needs_revision", "issues": ["src/foo.ts:12: missing null check"]}
        assert cr["cycles"][1] == {"cycle": 2, "verdict": "approved", "issues": []}
        assert "1 issue found" in cr["narrative"][1]
        assert "all issues resolved" in cr["narrative"][2]

    def test_code_review_loop_stops_at_max_cycles(self, tmp_path):
        # verdict always needs_revision → loop runs _MAX_CODE_REVIEW_CYCLES times then stops
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code", return_value=[]), \
             patch("medharness.services.cr_generation._parse_review_data",
                   return_value={"verdict": "needs_revision", "issues": ["file.ts:1: problem"]}):
            mock_claude.return_value = (0, "", "")
            result = generate_code("CR-071", dhf)

        from medharness.services.cr_generation import _MAX_CODE_REVIEW_CYCLES
        # develop + (_MAX - 1) * (review + fix) + final review
        expected = 1 + (_MAX_CODE_REVIEW_CYCLES - 1) * 2 + 1
        assert mock_claude.call_count == expected
        assert result["diagnostics"]["code_review_cycles"] == _MAX_CODE_REVIEW_CYCLES
        assert len(result["code_review"]["cycles"]) == _MAX_CODE_REVIEW_CYCLES

    def test_validate_code_reruns_after_review_fix(self, tmp_path):
        # P1a: validate_code must run after each review fix so that errors introduced
        # by the fix are captured in final_error_count and outcome.
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        new_error = [{"field": "test_links", "issue": "new error after review fix", "fix": "add @links"}]
        review_data_sequence = iter([
            {"verdict": "needs_revision", "issues": ["src/foo.ts:1: bad"]},
            {"verdict": "approved", "issues": []},
        ])
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.code_validation.validate_code",
                   side_effect=[[], new_error]) as mock_validate, \
             patch("medharness.services.cr_generation._parse_review_data",
                   side_effect=lambda text: next(review_data_sequence)):
            mock_claude.return_value = (0, "", "")
            result = generate_code("CR-080", dhf)

        assert mock_validate.call_count == 2
        assert result["diagnostics"]["final_error_count"] == 1
        step_names = [s["name"] for s in result["steps"]]
        assert "validate_after_review_fix_1" in step_names


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


class TestAutoPostPrFeedback:
    MOCK_TARGET = "medharness.services.cr_generation.post_pr_comment"

    def test_warnings_only_posts_one_comment(self):
        result = {"warnings": [{"code": "W001", "message": "something odd"}], "outcome": "ok"}
        with patch(self.MOCK_TARGET, side_effect=lambda pr, body, **kw: "https://url-1") as mock_post:
            urls = _auto_post_pr_feedback(42, "CR-042", result)
        assert mock_post.call_count == 1
        assert urls == ["https://url-1"]

    def test_errors_only_posts_one_comment(self):
        result = {
            "warnings": [],
            "outcome": "completed_with_errors",
            "errors": [{"field": "crs", "issue": "missing", "fix": "add it"}],
        }
        with patch(self.MOCK_TARGET, side_effect=lambda pr, body, **kw: "https://url-2") as mock_post:
            urls = _auto_post_pr_feedback(42, "CR-042", result)
        assert mock_post.call_count == 1
        assert urls == ["https://url-2"]

    def test_warnings_and_errors_posts_two_comments(self):
        result = {
            "warnings": [{"code": "W001", "message": "watch out"}],
            "outcome": "completed_with_errors",
            "errors": [{"field": "srs", "issue": "missing SRS", "fix": "create SRS-001"}],
        }
        with patch(self.MOCK_TARGET, side_effect=["https://url-1", "https://url-2"]) as mock_post:
            urls = _auto_post_pr_feedback(42, "CR-042", result)
        assert mock_post.call_count == 2
        assert urls == ["https://url-1", "https://url-2"]

    def test_no_warnings_no_errors_returns_empty(self):
        result = {"outcome": "completed", "warnings": [], "errors": []}
        with patch(self.MOCK_TARGET) as mock_post:
            urls = _auto_post_pr_feedback(42, "CR-042", result)
        mock_post.assert_not_called()
        assert urls == []

    def test_warning_body_format(self):
        result = {"warnings": [{"code": "W-TRACE", "message": "traceability gap"}], "outcome": "ok"}
        captured: list[str] = []
        with patch(self.MOCK_TARGET, side_effect=lambda pr, body, **kw: captured.append(body) or "https://u") as mock_post:
            _auto_post_pr_feedback(42, "CR-042", result)
        assert len(captured) == 1
        assert "⚠️ **Warnings for CR-042:**" in captured[0]
        assert "- `W-TRACE`: traceability gap" in captured[0]
        assert mock_post.call_args.args[0] == 42

    def test_error_body_format(self):
        result = {
            "warnings": [],
            "outcome": "completed_with_errors",
            "errors": [{"field": "srs_link", "issue": "no link", "fix": "add @links:SRS-001"}],
        }
        captured: list[str] = []
        with patch(self.MOCK_TARGET, side_effect=lambda pr, body, **kw: captured.append(body) or "https://u"):
            _auto_post_pr_feedback(42, "CR-042", result)
        assert len(captured) == 1
        assert "⚠️ **Validation errors for CR-042:**" in captured[0]
        assert "**srs_link**" in captured[0]
        assert "no link" in captured[0]
        assert "_Fix:_ add @links:SRS-001" in captured[0]

    def test_empty_url_not_added_to_list(self):
        result = {"warnings": [{"code": "W001", "message": "warn"}], "outcome": "ok"}
        with patch(self.MOCK_TARGET, return_value=""):
            urls = _auto_post_pr_feedback(42, "CR-042", result)
        assert urls == []

    def test_token_kwarg_forwarded_on_warning_branch(self):
        result = {"warnings": [{"code": "W001", "message": "x"}], "outcome": "ok"}
        with patch(self.MOCK_TARGET, side_effect=lambda pr, body, **kw: "https://u") as mock_post:
            _auto_post_pr_feedback(42, "CR-042", result, token="my-token")
        assert mock_post.call_args.kwargs.get("token") == "my-token"

    def test_token_kwarg_forwarded_on_error_branch(self):
        result = {
            "warnings": [],
            "outcome": "completed_with_errors",
            "errors": [{"field": "f", "issue": "i", "fix": "x"}],
        }
        with patch(self.MOCK_TARGET, side_effect=lambda pr, body, **kw: "https://u") as mock_post:
            _auto_post_pr_feedback(42, "CR-042", result, token="err-token")
        assert mock_post.call_args.kwargs.get("token") == "err-token"

    def test_explicit_empty_warnings_no_warning_comment(self):
        result = {
            "warnings": [],
            "outcome": "completed_with_errors",
            "errors": [{"field": "f", "issue": "i", "fix": "x"}],
        }
        captured: list[str] = []
        with patch(self.MOCK_TARGET, side_effect=lambda pr, body, **kw: captured.append(body) or "https://u"):
            _auto_post_pr_feedback(42, "CR-042", result)
        assert all("Warnings" not in b for b in captured)
        assert any("Validation errors" in b for b in captured)

    def test_missing_result_keys_produces_no_comments(self):
        with patch(self.MOCK_TARGET) as mock_post:
            urls = _auto_post_pr_feedback(42, "CR-042", {})
        mock_post.assert_not_called()
        assert urls == []

    def test_completed_with_errors_but_no_errors_key_posts_no_comment(self):
        # outcome == completed_with_errors with absent errors key → empty list → no post
        result = {"warnings": [], "outcome": "completed_with_errors"}
        with patch(self.MOCK_TARGET) as mock_post:
            urls = _auto_post_pr_feedback(42, "CR-042", result)
        mock_post.assert_not_called()
        assert urls == []

    def test_multiple_warnings_combined_into_single_body(self):
        result = {
            "warnings": [
                {"code": "W001", "message": "first warning"},
                {"code": "W002", "message": "second warning"},
            ],
            "outcome": "ok",
        }
        captured: list[str] = []
        with patch(self.MOCK_TARGET, side_effect=lambda pr, body, **kw: captured.append(body) or "https://u") as mock_post:
            _auto_post_pr_feedback(42, "CR-042", result)
        assert mock_post.call_count == 1
        assert "- `W001`: first warning" in captured[0]
        assert "- `W002`: second warning" in captured[0]


# ── LLMConfig and _resolve_stage_llm ──────────────────────────────────────────

class TestResolveStageLlm:
    def test_defaults_to_anthropic_when_no_env(self, monkeypatch):
        monkeypatch.delenv("MEDHARNESS_DESIGN_MODEL", raising=False)
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        cfg = _resolve_stage_llm("design")
        assert cfg.provider == "anthropic"
        assert cfg.model == ""

    def test_picks_up_anthropic_model_env(self, monkeypatch):
        monkeypatch.delenv("MEDHARNESS_DESIGN_MODEL", raising=False)
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-7")
        cfg = _resolve_stage_llm("design")
        assert cfg.provider == "anthropic"
        assert cfg.model == "claude-opus-4-7"

    def test_provider_colon_model_format(self, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DEVELOP_MODEL", "openai:gpt-4o")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        cfg = _resolve_stage_llm("develop")
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"
        assert cfg.api_key == "sk-test"
        assert cfg.base_url == "https://api.openai.com/v1"

    def test_deepseek_provider(self, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_CODE_REVIEW_MODEL", "deepseek:deepseek-chat")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
        cfg = _resolve_stage_llm("code_review")
        assert cfg.provider == "deepseek"
        assert cfg.model == "deepseek-chat"
        assert cfg.api_key == "ds-key"
        assert cfg.base_url == "https://api.deepseek.com/v1"

    def test_stage_names_are_uppercased(self, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DESIGN_REVIEW_MODEL", "openai:gpt-4o")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        cfg = _resolve_stage_llm("design_review")
        assert cfg.provider == "openai"

    def test_bare_model_without_provider_treated_as_anthropic(self, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DESIGN_MODEL", "claude-opus-4-7")
        cfg = _resolve_stage_llm("design")
        assert cfg.provider == "anthropic"
        assert cfg.model == "claude-opus-4-7"

    def test_unknown_provider_returns_empty_api_key_and_base_url(self, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DESIGN_MODEL", "custom:my-model")
        cfg = _resolve_stage_llm("design")
        assert cfg.provider == "custom"
        assert cfg.model == "my-model"
        assert cfg.api_key == ""
        assert cfg.base_url == ""

    def test_custom_base_url_overrides_default(self, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DESIGN_MODEL", "openai:gpt-4o")
        monkeypatch.setenv("MEDHARNESS_DESIGN_BASE_URL", "https://my-azure.openai.azure.com/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-1")
        cfg = _resolve_stage_llm("design")
        assert cfg.base_url == "https://my-azure.openai.azure.com/v1"

    def test_default_base_url_used_when_custom_not_set(self, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DESIGN_MODEL", "openai:gpt-4o")
        monkeypatch.delenv("MEDHARNESS_DESIGN_BASE_URL", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-1")
        cfg = _resolve_stage_llm("design")
        assert cfg.base_url == "https://api.openai.com/v1"


class TestModelLabel:
    def test_anthropic_with_model(self):
        assert _model_label(LLMConfig(provider="anthropic", model="claude-opus-4-7")) == "anthropic:claude-opus-4-7"

    def test_provider_without_model(self):
        assert _model_label(LLMConfig(provider="anthropic")) == "anthropic"

    def test_openai_with_model(self):
        assert _model_label(LLMConfig(provider="openai", model="gpt-4o")) == "openai:gpt-4o"


# ── _run_claude model param ────────────────────────────────────────────────────

class TestRunClaudeModelParam:
    def test_model_param_takes_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"result":"","session_id":""}', stderr="")
            _run_claude("p", model="claude-opus-4-7")
        args = mock_run.call_args[0][0]
        assert "--model" in args
        idx = args.index("--model")
        assert args[idx + 1] == "claude-opus-4-7"

    def test_env_used_when_model_param_empty(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"result":"","session_id":""}', stderr="")
            _run_claude("p", model="")
        args = mock_run.call_args[0][0]
        idx = args.index("--model")
        assert args[idx + 1] == "claude-haiku-4-5"


# ── _run_openai_compatible ─────────────────────────────────────────────────────

class TestRunOpenaiCompatible:
    BASE_URL = "https://api.openai.com/v1"

    def _make_response(self, content: str, tool_calls: list | None = None) -> bytes:
        message: dict = {"role": "assistant", "content": content}
        if tool_calls is not None:
            message["tool_calls"] = tool_calls
        return json.dumps({
            "choices": [{"message": message, "finish_reason": "stop" if not tool_calls else "tool_calls"}]
        }).encode()

    def test_returns_error_when_no_api_key(self):
        rc, output, sid = _run_openai_compatible("prompt", model="gpt-4o", api_key="", base_url=self.BASE_URL)
        assert rc == 1
        assert "API key" in output
        assert sid == ""

    def test_system_message_included_in_first_request(self):
        response_body = self._make_response("ok")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = response_body
        captured_payload: list[dict] = []
        def fake_urlopen(req, timeout=None):
            captured_payload.append(json.loads(req.data))
            return mock_resp
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _run_openai_compatible("do the task", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL)
        messages = captured_payload[0]["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "do the task"

    def test_returns_text_content_on_success(self):
        response_body = self._make_response("hello from gpt")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = response_body
        with patch("urllib.request.urlopen", return_value=mock_resp):
            rc, output, sid = _run_openai_compatible(
                "prompt", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL
            )
        assert rc == 0
        assert "hello from gpt" in output
        assert sid == ""

    def test_executes_tool_call_and_returns_result(self):
        tool_call = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "bash", "arguments": '{"command": "echo hi"}'},
        }
        first_response = self._make_response("", [tool_call])
        second_response = self._make_response("done")
        responses = iter([first_response, second_response])
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.side_effect = lambda: next(responses)
        with patch("urllib.request.urlopen", return_value=mock_resp), \
             patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout="hi\n", stderr="")
            rc, output, _ = _run_openai_compatible(
                "prompt", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL
            )
        assert rc == 0
        assert "done" in output
        cmd_args = mock_sub.call_args
        assert cmd_args[0][0] == "echo hi"

    def test_http_error_returns_exit_code_1(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(None, 401, "Unauthorized", {}, None)):
            rc, output, _ = _run_openai_compatible(
                "prompt", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL
            )
        assert rc == 1
        assert "401" in output

    def test_url_error_returns_exit_code_1(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            rc, output, _ = _run_openai_compatible(
                "prompt", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL
            )
        assert rc == 1
        assert "connection refused" in output

    def test_none_content_in_response_is_skipped(self):
        """Model returns content=None (tool_calls-only turn) — must not crash or add empty string."""
        response_body = json.dumps({
            "choices": [{"message": {"role": "assistant", "content": None}, "finish_reason": "stop"}]
        }).encode()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = response_body
        with patch("urllib.request.urlopen", return_value=mock_resp):
            rc, output, _ = _run_openai_compatible(
                "prompt", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL
            )
        assert rc == 0
        assert output == ""

    def test_max_turns_terminates_loop(self):
        """Loop exits after max_turns even when the model keeps requesting tool calls."""
        tool_call = {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": '{"command": "true"}'}}
        always_tool = json.dumps({
            "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [tool_call]}, "finish_reason": "tool_calls"}]
        }).encode()
        api_call_count = {"n": 0}
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        def _read():
            api_call_count["n"] += 1
            return always_tool
        mock_resp.read.side_effect = _read
        with patch("urllib.request.urlopen", return_value=mock_resp), \
             patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")):
            rc, _, _ = _run_openai_compatible(
                "prompt", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL, max_turns=3
            )
        assert rc == 0
        assert api_call_count["n"] == 3

    def test_subprocess_timeout_captured_as_tool_result(self):
        """A timed-out tool call must not crash the loop — the timeout message is sent back."""
        tool_call = {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": '{"command": "sleep 999"}'}}
        first_response = self._make_response("", [tool_call])
        second_response = self._make_response("got timeout result")
        responses = iter([first_response, second_response])
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.side_effect = lambda: next(responses)
        with patch("urllib.request.urlopen", return_value=mock_resp), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 120)):
            rc, output, _ = _run_openai_compatible(
                "prompt", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL
            )
        assert rc == 0
        assert "got timeout result" in output

    def test_subprocess_exception_captured_as_tool_result(self):
        """A subprocess error (non-timeout) must not crash the loop — the error is sent back."""
        tool_call = {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": '{"command": "bad"}'}}
        first_response = self._make_response("", [tool_call])
        second_response = self._make_response("got error result")
        responses = iter([first_response, second_response])
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.side_effect = lambda: next(responses)
        with patch("urllib.request.urlopen", return_value=mock_resp), \
             patch("subprocess.run", side_effect=OSError("permission denied")):
            rc, output, _ = _run_openai_compatible(
                "prompt", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL
            )
        assert rc == 0
        assert "got error result" in output

    def test_malformed_tool_arguments_captured_as_error(self):
        """Invalid JSON in tool call arguments must not crash the loop."""
        tool_call = {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": "not-json"}}
        first_response = self._make_response("", [tool_call])
        second_response = self._make_response("recovered")
        responses = iter([first_response, second_response])
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.side_effect = lambda: next(responses)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            rc, output, _ = _run_openai_compatible(
                "prompt", model="gpt-4o", api_key="sk-test", base_url=self.BASE_URL
            )
        assert rc == 0
        assert "recovered" in output


# ── diagnostics model fields ───────────────────────────────────────────────────

class TestDiagnosticsModelFields:
    @pytest.fixture(autouse=True)
    def stub_session(self, monkeypatch):
        monkeypatch.setattr("medharness.services.cr_generation.get_session", lambda pr: "")
        monkeypatch.setattr("medharness.services.cr_generation.put_session", lambda pr, sid: None)

    def test_generate_dhf_has_design_and_design_review_model(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DESIGN_MODEL", "openai:gpt-4o")
        monkeypatch.setenv("MEDHARNESS_DESIGN_REVIEW_MODEL", "deepseek:deepseek-chat")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-1")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-1")
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_llm", return_value=(0, "", "")), \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]):
            result = generate_dhf("CR-070", dhf)
        assert result["diagnostics"]["design_model"] == "openai:gpt-4o"
        assert result["diagnostics"]["design_review_model"] == "deepseek:deepseek-chat"
        assert "review_model" not in result["diagnostics"]
        assert "anthropic_model" not in result["diagnostics"]

    def test_generate_code_has_develop_and_code_review_model(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DEVELOP_MODEL", "deepseek:deepseek-chat")
        monkeypatch.setenv("MEDHARNESS_CODE_REVIEW_MODEL", "openai:gpt-4o")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-1")
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_llm", return_value=(0, "", "")), \
             patch("medharness.services.code_validation.validate_code", return_value=[]):
            result = generate_code("CR-071", dhf)
        assert result["diagnostics"]["develop_model"] == "deepseek:deepseek-chat"
        assert result["diagnostics"]["code_review_model"] == "openai:gpt-4o"
        assert "review_model" not in result["diagnostics"]
        assert "anthropic_model" not in result["diagnostics"]

    def test_generate_dhf_routes_generation_and_review_to_different_models(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DESIGN_MODEL", "openai:gpt-4o")
        monkeypatch.setenv("MEDHARNESS_DESIGN_REVIEW_MODEL", "deepseek:deepseek-chat")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-1")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-1")
        dhf = tmp_path / "DHF"
        dhf.mkdir()

        from medharness.services.cr_generation import LLMConfig
        configs_used: list[LLMConfig] = []

        def capture(prompt, *, config, resume_session=""):
            configs_used.append(config)
            return 0, "", ""

        with patch("medharness.services.cr_generation._run_llm", side_effect=capture), \
             patch("medharness.services.cr_generation.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": [], "deleted": []}), \
             patch("medharness.services.design_validation.validate_generate_dhf", return_value=[]):
            generate_dhf("CR-072", dhf)

        providers = [c.provider for c in configs_used]
        assert "openai" in providers, "generation step must use design model (openai)"
        assert "deepseek" in providers, "review step must use design_review model (deepseek)"
        # generation step is always first
        assert configs_used[0].provider == "openai"
        # review step is last
        assert configs_used[-1].provider == "deepseek"

    def test_generate_code_routes_generation_and_review_to_different_models(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MEDHARNESS_DEVELOP_MODEL", "deepseek:deepseek-chat")
        monkeypatch.setenv("MEDHARNESS_CODE_REVIEW_MODEL", "openai:gpt-4o")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-1")
        dhf = tmp_path / "DHF"
        dhf.mkdir()

        from medharness.services.cr_generation import LLMConfig
        configs_used: list[LLMConfig] = []

        def capture(prompt, *, config, resume_session=""):
            configs_used.append(config)
            return 0, "", ""

        with patch("medharness.services.cr_generation._run_llm", side_effect=capture), \
             patch("medharness.services.code_validation.validate_code", return_value=[]):
            generate_code("CR-073", dhf)

        providers = [c.provider for c in configs_used]
        assert "deepseek" in providers, "generation step must use develop model (deepseek)"
        assert "openai" in providers, "review step must use code_review model (openai)"
        # generation step is always first
        assert configs_used[0].provider == "deepseek"
        # review step is last
        assert configs_used[-1].provider == "openai"

