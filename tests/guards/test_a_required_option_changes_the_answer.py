"""The approval gate may only require what it reads.

`--stage` was required through four releases and never changed a verdict. It was
caught once, in 0.26.0, and the fix was to record it in the output rather than to
ask why it was required — then 0.27.0 removed the part of the output it had been
recorded in, and it was inert again, with a README sentence still explaining a
mechanism that no longer existed.

`test_no_parameter_is_decorative` reads function bodies, and `stage` was read:
it reached a dict literal. That is why it survived. This pins the gate's
required set instead, so adding one means saying what it narrows.

Scoped deliberately to this command. A general "two values give two answers"
check needs data built per option to be meaningful — on a clean scaffold two
valid `--coverage-pair` values answer identically for a good reason — and a
version of it that passes on any fixture would assert nothing.
"""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from medharness.cli import main


def _required(group: str, command: str) -> set[str]:
    return {
        opt
        for p in main.commands[group].commands[command].params
        for opt in p.opts
        if getattr(p, "required", False)
    }


def test_the_approval_gate_requires_only_what_it_reads() -> None:
    """It reads one PR's reviews and head commit. Nothing else narrows that.

    A stage cannot: the commit is what separates design from develop, because a
    design approval stops matching the head the moment code lands.
    """
    assert _required("change", "verify-approval") == {"--cr", "--pr"}, (
        f"required options are {sorted(_required('change', 'verify-approval'))}; "
        f"each one must narrow or identify what the gate reads"
    )


def test_both_required_options_reach_the_answer() -> None:
    seen: list = []

    def fake(pr_number, *, token=""):
        seen.append(pr_number)
        return {"approved": False, "reason": "no approving review",
                "head_sha": "", "approvals": [], "stale_approvals": []}

    runner = CliRunner()
    with patch("medharness.services.pr_approval.approval_evidence", side_effect=fake):
        a = runner.invoke(main, ["change", "verify-approval", "--cr", "CR-1", "--pr", "7"])
        b = runner.invoke(main, ["change", "verify-approval", "--cr", "CR-2", "--pr", "9"])

    assert seen == [7, 9], "--pr does not reach the evidence lookup"
    assert "CR-1" in a.output and "CR-2" in b.output, "--cr does not reach the answer"


def test_the_evidence_lookup_takes_no_stage() -> None:
    """The service too: `--stage` was dropped at the CLI once and grew back."""
    import inspect

    from medharness.services.pr_approval import approval_evidence

    params = set(inspect.signature(approval_evidence).parameters)
    assert "stage" not in params, (
        "approval_evidence takes a stage again; the commit is what separates "
        "the stages, so a stage cannot narrow the search"
    )
