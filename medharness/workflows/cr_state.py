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


# Phases where a CR may still accept work (generate-dhf, develop-cr).
ACTIVE_PHASES = frozenset({CRPhase.NEW, CRPhase.DESIGN, CRPhase.DEVELOP})

# Phases that are terminal — no further transitions are permitted.
TERMINAL_PHASES = frozenset({CRPhase.COMPLETED, CRPhase.CANCELLED})


def get_cr_phase(adapter, cr_id: str) -> CRPhase | None:
    """Return the current CRPhase for a CR, or None if the CR does not exist."""
    item = adapter.get_item(cr_id)
    if item is None:
        return None
    status = item.get("status", "")
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
    phase = get_cr_phase(adapter, cr_id)
    if phase is None:
        raise ValueError(f"CR '{cr_id}' not found.")
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
