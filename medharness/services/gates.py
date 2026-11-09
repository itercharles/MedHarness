"""Machine-readable description of the verification gates.

CI is deliberately not scaffolded, because a pipeline carries a project's runner
labels, secrets, and branch names. That decision only holds up if the interface
is described well enough to build against, which is what this is: `docs/interface.md`
is written from these facts and checked against them.

The registry is hand-written rather than derived from Click, because the facts
that matter most — whether a gate blocks, whether it reaches the network — are
not expressible as command metadata. What Click does state, the options, is not
repeated here: `scripts/generate_interface.py` reads it from the command. Tests
assert that every gate command appears here and every entry names a real one.
"""

from __future__ import annotations

from typing import Any

#: How a gate's findings affect the exit code.
#:
#: ``always``      — any finding fails the gate.
#: ``conditional`` — some findings always fail, others only under a flag.
BLOCKING = ("always", "conditional")

GATES: tuple[dict[str, Any], ...] = (
    {
        "command": "verify dhf",
        "checks": "Schema validity, required traceability, dangling links, "
                  "coverage between V-model layers, and that a completed CR has "
                  "what its type requires of one.",
        "blocking": "conditional",
        "blocking_note": "Schema errors, required-link failures, broken links "
                         "(dangling, wrong type, cycles) and a status no state of "
                         "its type always fail. Coverage gaps, placeholder text and a "
                         "completed CR missing what completing asks warn unless "
                         "--strict is passed.",
        "needs_network": False,
    },
    {
        "command": "verify tests",
        "checks": "Requirement-to-test coverage from JUnit evidence, including "
                  "declared test points; with --cr, only for the items one CR changed.",
        "blocking": "conditional",
        "blocking_note": "Uncovered requirements and unverified tests always fail. "
                         "A missing verification_method warns unless --strict, "
                         "and always fails under --cr.",
        "needs_network": False,
    },
    {
        "command": "verify soup",
        "checks": "The SOUP register against the dependency manifests, and each "
                  "item against the OSV vulnerability database, honouring "
                  "documented per-CVE acceptances.",
        "blocking": "conditional",
        "blocking_note": "Known vulnerabilities always fail, and so does an unreachable "
                         "osv.dev unless --offline-mode warn. Drift from the manifests "
                         "warns unless --strict.",
        "needs_network": True,
    },
    {
        "command": "verify impact",
        "checks": "That the CR's record of its impact (impact_analysis, reviewed_items, "
                  "affected_risk_items) is complete, evidenced and settles every item the "
                  "branch's changes reach, and that the branch changes exactly the items "
                  "the CR lists.",
        "blocking": "always",
        "blocking_note": "A change to code is required only when --code-path is given.",
        "needs_network": False,
    },
    {
        "command": "verify approval",
        "checks": "That every approval is signed by an approver holding its roles, that approvals "
                  "are only added, and that a change to the approvers list is approved from the "
                  "list as it was. With --release: that each document of the release manifest "
                  "and the release itself carry a current signature from their role.",
        "blocking": "always",
        "blocking_note": "Does nothing until DHF/config/approvers.yaml exists, and never asks for a "
                         "signature without --release. A signature made without a proven touch of "
                         "the key only warns.",
        "needs_network": False,
    },
)
