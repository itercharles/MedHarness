"""CR lifecycle state helpers.

Provides a canonical CRPhase enum and guard functions so every command that
gates on CR status uses the same source of truth instead of inline string sets.
"""

from __future__ import annotations

from enum import Enum


class CRPhase(str, Enum):
    """Canonical CR lifecycle phases derived from DHF status values."""
    NEW = "new"
    DESIGN = "design"
    DEVELOP = "develop"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


# Phases where a CR may still accept work (generate-dhf, develop-cr).
ACTIVE_PHASES = frozenset({CRPhase.NEW, CRPhase.DESIGN, CRPhase.DEVELOP})

# Phases that are terminal — no further transitions are permitted.
# 'rejected' is written by the generate-dhf triage step; omitting it made a
# rejected CR indistinguishable from a missing one.
TERMINAL_PHASES = frozenset({CRPhase.COMPLETED, CRPhase.CANCELLED, CRPhase.REJECTED})


def get_cr_phase(adapter, cr_id: str) -> CRPhase | None:
    """Return the current CRPhase for a CR, or None if it has no known phase.

    None covers three different situations — missing CR, absent status, and
    unrecognised status — so callers that need to tell them apart should use
    :func:`assert_cr_active`, which inspects the item itself.
    """
    item = adapter.get_item(cr_id)
    if item is None:
        return None
    status = str(item.get("status") or "").strip()
    if not status:
        # A CR with no status has not started a workflow yet. The scaffolded
        # starter CR is in exactly this state.
        return CRPhase.NEW
    try:
        return CRPhase(status)
    except ValueError:
        return None


def assert_cr_active(adapter, cr_id: str) -> CRPhase:
    """Return the current phase if the CR is active; raise ValueError otherwise.

    Callers use this to gate workflow commands that require an in-progress CR
    (generate-dhf, develop-cr). Idempotent re-runs on terminal CRs get a clear
    error rather than a silent no-op or a traceback.
    """
    item = adapter.get_item(cr_id)
    if item is None:
        raise ValueError(f"CR '{cr_id}' not found.")

    phase = get_cr_phase(adapter, cr_id)
    if phase is None:
        # The CR exists but carries a status this workflow does not model.
        # Reporting "not found" here sent people looking for the wrong problem.
        raise ValueError(
            f"CR '{cr_id}' has status '{item.get('status')}', which is not a "
            f"recognised phase. Expected one of: "
            f"{', '.join(sorted(p.value for p in CRPhase))}."
        )
    if phase in TERMINAL_PHASES:
        raise ValueError(
            f"CR '{cr_id}' is already '{phase.value}' and cannot accept further work. "
            f"Create a new CR if additional changes are needed."
        )
    if phase not in ACTIVE_PHASES:
        raise ValueError(
            f"CR '{cr_id}' has unexpected status '{phase.value}'. "
            f"Expected one of: {sorted(p.value for p in ACTIVE_PHASES)}."
        )
    return phase
