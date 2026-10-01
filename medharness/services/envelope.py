"""The envelope every gate answers in: `{gate, passed, summary, errors, warnings}`."""

from __future__ import annotations

from typing import Any

from medharness.results import GateResult


#: Keys every gate result carries, whatever the gate. A caller — a CI script or
#: an agent — parses this once and handles any gate, present or future.
#: What a gate writes to stdout. `details` is built alongside it for the CLI
#: to render lines from, in-process, and is deliberately not serialised.
ENVELOPE_KEYS = tuple(GateResult.model_fields)


#: What a gate hands back in-process. One key wider than what is emitted: the
#: CLI renders its lines from `details` and then drops it.
GATE_RESULT_KEYS = ENVELOPE_KEYS + ("details",)


def gate_result(
    gate: str,
    passed: bool,
    summary: str,
    *,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    **details: Any,
) -> dict[str, Any]:
    """Wrap a gate outcome in the common envelope.

    The answer is the verdict and what the gate found: ``errors`` are what made
    it fail, ``warnings`` what it noticed without failing, both already phrased
    for a human. Every finding must reach one of those two — they are the whole
    answer, so anything only in ``details`` is invisible to a caller.

    ``details`` carries the same findings structured, for the CLI to render its
    stderr lines from in the same process. It is not serialised: no caller has
    ever read it, and a shape nobody reads is one that drifts.
    """
    return {
        "gate": gate,
        "passed": passed,
        "summary": summary,
        "errors": list(errors or []),
        "warnings": list(warnings or []),
        "details": details,
    }


def envelope_from(gate: str, raw: dict) -> dict:
    """Restructure a gate's own dict into the common envelope.

    The gate keeps building its own messages — it knows what its findings mean.
    This only moves the gate-specific keys under ``details`` so the top level is
    identical across gates.
    """
    return gate_result(
        gate,
        bool(raw.get("passed", False)),
        str(raw.get("summary") or ""),
        errors=raw.get("errors") or [],
        warnings=raw.get("warnings") or [],
        **{k: v for k, v in raw.items()
           if k not in ("passed", "summary", "errors", "warnings")},
    )
