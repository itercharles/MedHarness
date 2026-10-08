"""Running a model: provider config, the `claude` CLI, and the OpenAI-compatible loop."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class LLMConfig:
    provider: str = "anthropic"  # "anthropic" | "openai" | "deepseek"
    model: str = ""
    api_key: str = ""
    base_url: str = ""


_PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


_PROVIDER_API_KEY_ENVS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def _resolve_stage_llm(stage: str) -> LLMConfig:
    """Resolve LLM config for a workflow stage.

    Reads MEDHARNESS_{stage}_MODEL (e.g. MEDHARNESS_DESIGN_MODEL,
    MEDHARNESS_DESIGN_REVIEW_MODEL, MEDHARNESS_DEVELOP_MODEL,
    MEDHARNESS_CODE_REVIEW_MODEL). Format: "provider:model"
    (e.g. "deepseek:deepseek-chat", "openai:gpt-4o").
    Falls back to anthropic + ANTHROPIC_MODEL if not set.

    For non-anthropic providers, MEDHARNESS_{stage}_BASE_URL overrides the
    default endpoint, enabling Azure OpenAI, Ollama, vLLM, LM Studio, etc.
    """
    raw = os.environ.get(f"MEDHARNESS_{stage.upper()}_MODEL", "")
    if raw:
        provider, _, model = raw.partition(":")
        if not model:
            provider, model = "anthropic", raw
    else:
        provider = "anthropic"
        model = os.environ.get("ANTHROPIC_MODEL", "")

    if provider == "anthropic":
        return LLMConfig(provider=provider, model=model)

    api_key_env = _PROVIDER_API_KEY_ENVS.get(provider, "")
    api_key = os.environ.get(api_key_env, "") if api_key_env else ""
    base_url = (
        os.environ.get(f"MEDHARNESS_{stage.upper()}_BASE_URL")
        or _PROVIDER_BASE_URLS.get(provider, "")
    )
    return LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)


def _model_label(config: LLMConfig) -> str:
    if config.model:
        return f"{config.provider}:{config.model}"
    return config.provider


_SESSION_GONE = "no conversation found with session id"


def _run_claude(prompt: str, *, resume_session: str = "", model: str = "") -> tuple[int, str, str]:
    """Invoke claude -p. Returns (exit_code, text_output, session_id).

    Uses --output-format json so the session_id is always captured from the
    structured response envelope. Falls back gracefully if JSON cannot be parsed.
    """
    effective_model = model or os.environ.get("ANTHROPIC_MODEL", "")
    cmd = ["claude", "-p", "--dangerously-skip-permissions", "--output-format", "json"]
    if effective_model:
        cmd += ["--model", effective_model]
    if resume_session:
        cmd += ["--resume", resume_session]
    cmd.append(prompt)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    except FileNotFoundError:
        return 1, "claude CLI not found — install @anthropic-ai/claude-code", ""
    session_id = ""
    text_output = result.stdout
    if result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            result_val = data.get("result")
            text_output = result_val if result_val is not None else result.stdout
            session_id = data.get("session_id") or ""
        except (json.JSONDecodeError, AttributeError):
            pass
    if result.stderr:
        text_output += "\n" + result.stderr
    return result.returncode, text_output, session_id


def _run_openai_compatible(
    prompt: str,
    *,
    model: str,
    api_key: str,
    base_url: str,
    max_turns: int = 100,
) -> tuple[int, str, str]:
    """Run an agentic loop against an OpenAI-compatible chat completions API.

    Exposes a single `bash` function tool. Loops until the model stops calling
    tools or max_turns is reached. Returns (exit_code, text_output, session_id).
    Session IDs are not supported by OpenAI-compatible APIs; always returns "".
    """
    if not api_key:
        return 1, f"API key not configured for provider at {base_url}", ""

    bash_tool = {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run."},
                },
                "required": ["command"],
            },
        },
    }

    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are an expert software engineering assistant. "
                "Use the bash tool to read files, run CLI commands, create and modify "
                "DHF items, and verify your work. Complete the task fully before stopping."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    output_parts: list[str] = []

    for _ in range(max_turns):
        payload = json.dumps({"model": model, "tools": [bash_tool], "messages": messages}).encode()
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return 1, f"HTTP {exc.code}: {exc.reason}", ""
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            return 1, f"API error: {exc}", ""

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message", {})
        messages.append(message)

        content = message.get("content") or ""
        if content:
            output_parts.append(content)

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            break

        tool_results: list[dict] = []
        for tc in tool_calls:
            tc_id = tc.get("id", "")
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
                command = args.get("command", "")
                proc = subprocess.run(  # noqa: S603 S602
                    command, shell=True, capture_output=True, text=True, timeout=120
                )
                tc_output = proc.stdout + (("\n" + proc.stderr) if proc.stderr else "")
            except subprocess.TimeoutExpired:
                tc_output = "Command timed out."
            except Exception as exc:  # noqa: BLE001
                tc_output = f"Error: {exc}"
            tool_results.append({"role": "tool", "tool_call_id": tc_id, "content": tc_output})
        messages.extend(tool_results)
    else:
        return 1, "\n".join([*output_parts, f"Stopped after {max_turns} turns without finishing."]), ""

    return 0, "\n".join(output_parts), ""


def _resume_unavailable(output: str) -> bool:
    """Whether a failure was the stored session being absent, not the work failing."""
    return _SESSION_GONE in output.lower()


def _run_llm(
    prompt: str,
    *,
    config: LLMConfig,
    resume_session: str = "",
) -> tuple[int, str, str]:
    """Dispatch to the appropriate LLM runner based on config.provider."""
    if config.provider == "anthropic":
        return _run_claude(prompt, resume_session=resume_session, model=config.model)
    return _run_openai_compatible(
        prompt,
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )
