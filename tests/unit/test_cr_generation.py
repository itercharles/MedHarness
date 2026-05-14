"""Unit tests for medharness.services.cr_generation."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from medharness.services.cr_generation import (
    _append_skills,
    _assemble_analyze_prompt,
    _assemble_design_prompt,
    _assemble_develop_prompt,
    _assemble_review_spec_prompt,
    _build_design_impact_notes,
    _get_pr_feedback,
    _load_prompt,
    _load_skill,
    _replace_managed_block,
    _run_claude,
    generate_code,
    generate_design,
    generate_dhf,
    generate_spec,
)

from medharness.services.prompt_assembly import (
    MAX_DIFF_CHARS,
    _build_dhf_context_block,
    _build_impact_closure_block,
)


# ── Prompt loading ────────────────────────────────────────────────────────────

class TestLoadPrompt:
    def test_load_cr_analyze(self):
        text = _load_prompt("cr_analyze.md")
        assert "{{cr_id}}" in text
        assert "affected_items" in text
        assert "manual_verification_candidates" in text
        assert "verification_method" in text
        assert "SYS" in text
        assert "SOUP" in text

    def test_load_cr_design(self):
        text = _load_prompt("cr_design.md")
        assert "{{cr_id}}" in text
        assert "medharness" in text

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
    def test_analyze_substitutes_cr_id(self):
        prompt = _assemble_analyze_prompt("CR-042")
        assert "CR-042" in prompt
        assert "{{cr_id}}" not in prompt

    def test_analyze_includes_skills(self):
        prompt = _assemble_analyze_prompt("CR-001")
        assert "Product Impact" in prompt
        assert "Risk Impact" in prompt

    def test_analyze_includes_dhf_item_list_command(self):
        prompt = _assemble_analyze_prompt("CR-001")
        assert "dhf item list" in prompt

    def test_design_substitutes_cr_id(self):
        prompt = _assemble_design_prompt("CR-007")
        assert "CR-007" in prompt
        assert "{{cr_id}}" not in prompt

    def test_design_includes_traceability_validation(self):
        prompt = _assemble_design_prompt("CR-007")
        assert "validate traceability" in prompt

    def test_design_includes_cli_create_syntax(self):
        prompt = _assemble_design_prompt("CR-007")
        assert "dhf item create" in prompt
        assert "dhf item update" in prompt

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

    def test_review_spec_substitutes_cr_id(self):
        prompt = _assemble_review_spec_prompt("CR-042")
        assert "CR-042" in prompt
        assert "{{cr_id}}" not in prompt

    def test_review_spec_focuses_on_soft_judgment(self):
        prompt = _assemble_review_spec_prompt("CR-001")
        assert "actionab" in prompt.lower()
        assert "placeholder" in prompt.lower() or "tbd" in prompt.lower() or "todo" in prompt.lower()

    def test_review_spec_instructs_not_to_re_verify_schema(self):
        prompt = _assemble_review_spec_prompt("CR-001")
        assert "deterministic" in prompt.lower() or "mechanically" in prompt.lower()


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


# ── generate_spec ─────────────────────────────────────────────────────────────

class TestGenerateSpec:
    def _dhf(self, tmp_path: Path) -> Path:
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        return dhf

    def _valid_spec_content(self, cr_id: str) -> str:
        return (
            f'---\ncr_id: "{cr_id}"\ndisposition: approve\npipeline_route: standard\n'
            'affected_items: []\nproposed_new_items: []\n'
            'design_impact_summary: "Test summary."\n'
            'test_plan:\n  auto_covered: []\n  needs_new_tc: []\n  must_be_manual: []\n---\n'
        )

    def test_returns_dict_with_required_keys(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-001-Spec.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(self._valid_spec_content("CR-001"), encoding="utf-8")
        with patch("medharness.services.cr_generation._run_claude") as mock_claude:
            mock_claude.return_value = (0, "done")
            result = generate_spec("CR-001", dhf)
        assert result["cr_id"] == "CR-001"
        assert result["stage"] == "spec"
        assert result["outcome"] == "ok"
        assert result["errors"] == []
        for key in ("summary", "timing", "inputs", "progress", "steps", "artifacts", "diagnostics", "warnings"):
            assert key in result, f"missing key: {key}"
        assert result["artifacts"]["analysis"]["disposition"] == "approve"
        assert result["artifacts"]["analysis"]["pipeline_route"] == "standard"
        assert result["artifacts"]["analysis"]["proposed_new_items"] == []
        assert result["artifacts"]["spec_json_path"] == str(spec_path.with_suffix(".json"))

    def test_analysis_includes_disposition(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-001-Spec.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(self._valid_spec_content("CR-001"), encoding="utf-8")
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "done")):
            result = generate_spec("CR-001", dhf)
        assert result["artifacts"]["analysis"]["disposition"] == "approve"

    def test_analysis_includes_pipeline_route(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-001-Spec.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(self._valid_spec_content("CR-001"), encoding="utf-8")
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "done")):
            result = generate_spec("CR-001", dhf)
        assert result["artifacts"]["analysis"]["pipeline_route"] == "standard"

    def test_analysis_has_no_direction_fit_key(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-001-Spec.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(self._valid_spec_content("CR-001"), encoding="utf-8")
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "done")):
            result = generate_spec("CR-001", dhf)
        assert "direction_fit" not in result["artifacts"]["analysis"]

    def test_calls_run_claude_twice_when_spec_valid(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-002-Spec.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(self._valid_spec_content("CR-002"), encoding="utf-8")
        with patch("medharness.services.cr_generation._run_claude") as mock_claude:
            mock_claude.return_value = (0, "done")
            result = generate_spec("CR-002", dhf)
        # Two calls: spec generation + soft review (no fix needed when checks pass).
        assert mock_claude.call_count == 2
        assert result["outcome"] == "ok"
        assert result["diagnostics"]["fix_attempted"] is False
        # Review prompt is augmented with the "already passed" note.
        review_prompt = mock_claude.call_args_list[1][0][0]
        assert "already passed" in review_prompt.lower()

    def test_self_corrects_when_spec_invalid(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-003-Spec.md"
        spec_path.parent.mkdir(parents=True)
        # Write a spec with missing disposition to trigger validation error
        spec_path.write_text(
            '---\ncr_id: "CR-003"\naffected_items: []\nproposed_new_items: []\n'
            'design_impact_summary: "No design impact."\n'
            'test_plan:\n  auto_covered: []\n  needs_new_tc: []\n  must_be_manual: []\n---\n',
            encoding="utf-8",
        )
        with patch("medharness.services.cr_generation._run_claude") as mock_claude:
            mock_claude.return_value = (0, "done")
            result = generate_spec("CR-003", dhf)
        # Three calls: spec generation + fix pass + soft review.
        assert mock_claude.call_count == 3
        assert result["outcome"] == "completed_with_errors"
        assert result["diagnostics"]["fix_attempted"] is True

    def test_creates_spec_dir(self, tmp_path):
        dhf = self._dhf(tmp_path)
        with patch("medharness.services.cr_generation._run_claude") as mock_claude:
            mock_claude.return_value = (0, "")
            generate_spec("CR-004", dhf)
        assert (tmp_path / "docs" / "cr-specs").is_dir()

    def test_revision_mode_uses_pr_feedback(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-005-Spec.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(self._valid_spec_content("CR-005"), encoding="utf-8")
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation._get_pr_feedback") as mock_fb:
            mock_claude.return_value = (0, "")
            mock_fb.return_value = {
                "prompt_text": '{"comments": [], "reviews": []}',
                "diagnostics": {"attempted": True, "comments_status": "ok", "reviews_status": "ok"},
                "warnings": [],
            }
            generate_spec("CR-005", dhf, pr_number=99)
        mock_fb.assert_called_once_with(99)
        # First call is the revision prompt; last call is the soft review — check the first.
        gen_prompt = mock_claude.call_args_list[0][0][0]
        assert "review feedback" in gen_prompt.lower()

    def test_writes_json_companion_on_success(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-010-Spec.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(self._valid_spec_content("CR-010"), encoding="utf-8")
        with patch("medharness.services.cr_generation._run_claude") as mock_claude:
            mock_claude.return_value = (0, "done")
            generate_spec("CR-010", dhf)
        json_path = spec_path.with_suffix(".json")
        assert json_path.exists()
        import json as _json
        data = _json.loads(json_path.read_text(encoding="utf-8"))
        assert data["cr_id"] == "CR-010"

    def test_writes_json_companion_even_with_residual_errors(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-011-Spec.md"
        spec_path.parent.mkdir(parents=True)
        # Missing disposition — will fail validation; fix pass won't help since
        # mock_claude returns (0, "done") without actually writing anything new.
        spec_path.write_text(
            '---\ncr_id: "CR-011"\naffected_items: []\n'
            'test_plan:\n  auto_covered: []\n  needs_new_tc: []\n  must_be_manual: []\n---\n',
            encoding="utf-8",
        )
        with patch("medharness.services.cr_generation._run_claude") as mock_claude:
            mock_claude.return_value = (0, "done")
            generate_spec("CR-011", dhf)
        # JSON is written from whatever front-matter was parsed (missing fields are absent).
        json_path = spec_path.with_suffix(".json")
        assert json_path.exists()

    def test_response_includes_spec_json_path(self, tmp_path):
        dhf = self._dhf(tmp_path)
        spec_path = tmp_path / "docs" / "cr-specs" / "CR-012-Spec.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(self._valid_spec_content("CR-012"), encoding="utf-8")
        with patch("medharness.services.cr_generation._run_claude") as mock_claude:
            mock_claude.return_value = (0, "done")
            result = generate_spec("CR-012", dhf)
        assert result["artifacts"]["spec_json_path"] is not None
        assert result["artifacts"]["spec_json_path"].endswith(".json")

    def test_spec_json_path_is_none_when_no_spec_file(self, tmp_path):
        dhf = self._dhf(tmp_path)
        # Claude writes nothing — spec file never gets created.
        with patch("medharness.services.cr_generation._run_claude") as mock_claude:
            mock_claude.return_value = (0, "")
            result = generate_spec("CR-013", dhf)
        assert result["artifacts"]["spec_json_path"] is None

    def test_analysis_is_none_when_no_spec_file(self, tmp_path):
        dhf = self._dhf(tmp_path)
        with patch("medharness.services.cr_generation._run_claude") as mock_claude:
            mock_claude.return_value = (0, "")
            result = generate_spec("CR-014", dhf)
        assert result["artifacts"]["analysis"] is None


# ── generate_design ───────────────────────────────────────────────────────────

class TestGenerateDesign:
    """Pipeline: design pass → deterministic check → fix-only on errors → soft review."""

    def test_returns_dict_with_required_keys(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]):
            mock_claude.return_value = (0, "")
            result = generate_design("CR-010", dhf)
        assert result["cr_id"] == "CR-010"
        assert result["stage"] == "design"
        assert result["outcome"] == "ok"
        assert result["errors"] == []
        for key in ("summary", "timing", "inputs", "progress", "steps", "artifacts", "diagnostics", "warnings"):
            assert key in result, f"missing key: {key}"
        assert set(result["artifacts"]["items_changed"]) == {"created", "updated", "deleted"}

    def test_happy_path_runs_design_then_review(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]):
            mock_claude.return_value = (0, "")
            result = generate_design("CR-011", dhf)
        # Two calls: design generation + soft review (no fix call when checks pass).
        assert mock_claude.call_count == 2
        assert result["outcome"] == "ok"
        assert result["diagnostics"]["fix_attempted"] is False
        # Review prompt is augmented with the "already passed" note so the
        # reviewer does not re-derive what the harness already proved.
        review_prompt = mock_claude.call_args_list[1][0][0]
        assert "already passed" in review_prompt.lower()

    def test_fix_pass_triggered_when_validation_fails(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        first_errors = [{"field": "schema", "issue": "x", "fix": "y"}]
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.design_validation.validate_design",
                   side_effect=[first_errors, []]):
            mock_claude.return_value = (0, "")
            result = generate_design("CR-014", dhf)
        # Three calls: design + fix + review.
        assert mock_claude.call_count == 3
        # Fix prompt is the second call and references the error.
        fix_prompt = mock_claude.call_args_list[1][0][0]
        assert "schema" in fix_prompt
        assert "deterministic validation" in fix_prompt
        assert result["outcome"] == "corrected"
        assert result["diagnostics"]["fix_attempted"] is True

    def test_residual_errors_recorded_when_fix_does_not_clear(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        errors = [{"field": "schema", "issue": "x", "fix": "y"}]
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.design_validation.validate_design",
                   side_effect=[errors, errors]):
            mock_claude.return_value = (0, "")
            result = generate_design("CR-015", dhf)
        assert mock_claude.call_count == 3
        assert result["outcome"] == "completed_with_errors"
        # Residual errors are surfaced in the response payload — clients can
        # render or post them without re-running the validator.
        assert result["errors"][0]["field"] == "schema"
        assert result["errors"][0]["issue"] == "x"
        assert result["errors"][0]["code"] == "schema"
        # The soft-review prompt should surface the residual issue.
        review_prompt = mock_claude.call_args_list[2][0][0]
        assert "residual issues" in review_prompt.lower()

    def test_items_changed_populated_from_git(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        diff_output = (
            "A\tDHF/items/01_sys/SYS-001.yaml\n"
            "M\tDHF/items/02_srs/SRS-002.yaml\n"
            "D\tDHF/items/02_srs/SRS-099.yaml\n"
        )
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]), \
             patch("subprocess.run",
                   return_value=MagicMock(stdout=diff_output, returncode=0)):
            mock_claude.return_value = (0, "")
            result = generate_design("CR-016", dhf)
        assert result["artifacts"]["items_changed"] == {
            "created": ["SYS-001"],
            "updated": ["SRS-002"],
            "deleted": ["SRS-099"],
        }

    def test_design_prompt_passed_to_claude(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]):
            mock_claude.return_value = (0, "")
            generate_design("CR-012", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "CR-012" in prompt
        assert "dhf item create" in prompt

    def test_revision_mode_uses_pr_feedback(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.cr_generation._get_pr_feedback") as mock_fb, \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]):
            mock_claude.return_value = (0, "")
            mock_fb.return_value = {
                "prompt_text": '{"comments": [], "reviews": []}',
                "diagnostics": {"attempted": True, "comments_status": "ok", "reviews_status": "ok"},
                "warnings": [],
            }
            generate_design("CR-013", dhf, pr_number=42)
        mock_fb.assert_called_once_with(42)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "review feedback" in prompt.lower()

    def test_design_prompt_includes_spec_json_when_json_exists(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        # Write a JSON companion alongside a (non-existent) spec .md
        spec_json = tmp_path / "docs" / "cr-specs" / "CR-099-Spec.json"
        spec_json.parent.mkdir(parents=True)
        import json as _json
        spec_json.write_text(
            _json.dumps({
                "cr_id": "CR-099",
                "disposition": "approve",
                "pipeline_route": "standard",
                "affected_items": ["SYS-001"],
                "proposed_new_items": [{
                    "type": "SRS",
                    "title": "New workflow requirement",
                    "parent": "SYS-001",
                    "verification_method": "Test",
                }],
                "design_impact_summary": "Injection test.",
                "test_plan": {"auto_covered": [], "needs_new_tc": [], "must_be_manual": []},
            }),
            encoding="utf-8",
        )
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]):
            mock_claude.return_value = (0, "")
            generate_design("CR-099", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "Pre-computed Spec Summary" in prompt
        assert "disposition" in prompt
        assert "pipeline_route" in prompt
        assert "verification_method" in prompt
        assert "parent" in prompt
        assert "SYS" in prompt
        assert "SOUP" in prompt

    def test_design_prompt_omits_injection_when_json_missing(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        with patch("medharness.services.cr_generation._run_claude") as mock_claude, \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]):
            mock_claude.return_value = (0, "")
            generate_design("CR-098", dhf)
        prompt = mock_claude.call_args_list[0][0][0]
        assert "Pre-computed Spec Summary" not in prompt

    def test_successful_design_records_impact_on_cr(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        diff_output = (
            "A\tDHF/items/01_sys/SYS-009.yaml\n"
            "M\tDHF/items/02_srs/SRS-010.yaml\n"
        )
        spec_json = {
            "affected_items": ["SYS-001"],
            "proposed_new_items": [{"type": "SRS", "title": "New workflow requirement", "parent": "SYS-001"}],
        }
        mock_adapter = MagicMock()
        mock_adapter.get_item.return_value = {"id": "CR-017", "implementation_notes": "Manual note"}
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "")), \
             patch("medharness.services.design_validation.validate_design", return_value=[]), \
             patch("subprocess.run", return_value=MagicMock(stdout=diff_output, returncode=0)), \
             patch("medharness.services.cr_impact.read_spec_json", return_value=spec_json), \
             patch("medharness.services.cr_impact.LocalDHFAdapter", return_value=mock_adapter):
            generate_design("CR-017", dhf)
        mock_adapter.update_item.assert_called_once()
        args, kwargs = mock_adapter.update_item.call_args
        assert args[0] == "CR-017"
        assert args[1]["affected_items"] == ["SRS-010", "SYS-001", "SYS-009"]
        assert "Design Impact Snapshot" in args[1]["implementation_notes"]
        assert "Manual note" in args[1]["implementation_notes"]
        assert "DHF items created: SYS-009" in args[1]["implementation_notes"]
        assert "DHF items updated: SRS-010" in args[1]["implementation_notes"]
        assert kwargs == {"author": "medharness", "cr_id": "CR-017"}

    def test_residual_design_errors_do_not_record_impact_on_cr(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        errors = [{"field": "schema", "issue": "x", "fix": "y"}]
        mock_adapter = MagicMock()
        with patch("medharness.services.cr_generation._run_claude", return_value=(0, "")), \
             patch("medharness.services.design_validation.validate_design", side_effect=[errors, errors]), \
             patch("subprocess.run", return_value=MagicMock(stdout="", returncode=0)), \
             patch("medharness.services.cr_impact.LocalDHFAdapter", return_value=mock_adapter):
            generate_design("CR-018", dhf)
        mock_adapter.update_item.assert_not_called()


class TestDesignImpactSnapshotHelpers:
    def test_build_design_impact_notes_includes_spec_and_actual_items(self):
        notes = _build_design_impact_notes(
            {
                "affected_items": ["SYS-001"],
                "proposed_new_items": [{"type": "SRS", "title": "New requirement", "parent": "SYS-001"}],
            },
            {"created": ["SRS-005"], "updated": ["SYS-001"], "deleted": []},
        )
        assert "Spec affected items: SYS-001" in notes
        assert "SRS: New requirement (parent: SYS-001)" in notes
        assert "DHF items created: SRS-005" in notes
        assert "DHF items deleted: none" in notes

    def test_replace_managed_block_replaces_existing_snapshot(self):
        original = (
            "Manual intro\n\n"
            "<!-- medharness:design-impact:start -->\nOld block\n"
            "<!-- medharness:design-impact:end -->\n\n"
            "Manual outro"
        )
        updated = _replace_managed_block(original, "<!-- medharness:design-impact:start -->\nNew block\n<!-- medharness:design-impact:end -->")
        assert "Old block" not in updated
        assert "New block" in updated
        assert "Manual intro" in updated
        assert "Manual outro" in updated


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
            "name": "System Requirement", "code": "SYSREQ",
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


# ── Impact closure block ───────────────────────────────────────────────────────

class TestBuildImpactClosureBlock:
    def test_returns_empty_on_empty_affected_items(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        result = _build_impact_closure_block(dhf, {"affected_items": []})
        assert result == ""

    def test_returns_empty_when_affected_not_list(self, tmp_path):
        dhf = tmp_path / "DHF"
        dhf.mkdir()
        result = _build_impact_closure_block(dhf, {})
        assert result == ""

    def test_returns_empty_on_adapter_failure(self, tmp_path):
        dhf = tmp_path / "nonexistent"
        result = _build_impact_closure_block(
            dhf, {"affected_items": ["SYS-001"]}
        )
        assert result == ""

    def test_includes_upstream_and_downstream(self, tmp_path):
        from tests.fixtures.stub_adapter import StubDHFAdapter

        dhf = tmp_path / "DHF"
        dhf.mkdir()
        adapter = StubDHFAdapter()
        adapter.create_item({"id": "SYS-001", "title": "System req",
                             "derives_from": ["CRS-001"]})
        adapter.create_item({"id": "CRS-001", "title": "User need"})
        adapter.create_item({"id": "SRS-001", "title": "Software req",
                             "implements": ["SYS-001"]})
        adapter.create_item({"id": "RISK-001", "title": "Risk item",
                             "satisfies": ["SYS-001"]})
        with patch(
            "dhfkit.local_adapter.LocalDHFAdapter",
            return_value=adapter,
        ):
            result = _build_impact_closure_block(
                dhf, {"affected_items": ["SYS-001"]}
            )
        assert "Pre-computed Impact Closure" in result
        assert "### SYS-001" in result
        assert "CRS-001" in result
        assert "SRS-001" in result

    def test_reports_not_found_for_missing_item(self, tmp_path):
        from tests.fixtures.stub_adapter import StubDHFAdapter

        dhf = tmp_path / "DHF"
        dhf.mkdir()
        adapter = StubDHFAdapter()
        with patch(
            "dhfkit.local_adapter.LocalDHFAdapter",
            return_value=adapter,
        ):
            result = _build_impact_closure_block(
                dhf, {"affected_items": ["SYS-999"]}
            )
        assert "Not found in DHF graph" in result


# ── Analyze prompt with DHF context ────────────────────────────────────────────

class TestAssembleAnalyzePromptWithContext:
    def test_includes_context_when_dhf_path_provided(self, tmp_path):
        from tests.fixtures.stub_adapter import StubDHFAdapter

        dhf = tmp_path / "DHF"
        dhf.mkdir()
        adapter = StubDHFAdapter()
        adapter.create_item({"id": "SYS-001", "title": "Test req"})
        with patch(
            "dhfkit.local_adapter.LocalDHFAdapter",
            return_value=adapter,
        ):
            prompt = _assemble_analyze_prompt("CR-050", dhf)
        assert "Pre-computed DHF Context" in prompt
        assert "CR-050" in prompt

    def test_omits_context_when_no_dhf_path(self):
        prompt = _assemble_analyze_prompt("CR-051")
        assert "Pre-computed DHF Context" not in prompt
        assert "CR-051" in prompt
