"""Machine-readable description of the verification gates.

CI is deliberately not scaffolded, because a pipeline carries a project's runner
labels, secrets, and branch names. That decision only holds up if the interface
is described well enough to build against, which is what this is: `docs/interface.md`
is written from these facts and checked against them.

The registry is hand-written rather than derived from Click, because the facts
that matter most — whether a gate blocks, whether it reaches the network — are
not expressible as command metadata. Tests assert both directions: every gate
command appears here, and every option declared here exists on the command.
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
        "checks": "Schema validity, required traceability, dangling links, and "
                  "coverage between V-model layers.",
        "options": {
            "required": [],
            "optional": ["--fail-on-uncovered"],
        },
        "blocking": "conditional",
        "blocking_note": "Schema errors, required-link failures, and dangling "
                         "links always fail. Coverage gaps warn unless "
                         "--fail-on-uncovered is passed.",
        "needs_network": False,
    },
    {
        "command": "verify tests",
        "checks": "Requirement-to-test coverage from JUnit evidence, including "
                  "declared test points.",
        "options": {
            "required": ["--junit"],
            "optional": ["--fail-on-missing-method"],
        },
        "blocking": "conditional",
        "blocking_note": "Uncovered requirements and unverified tests always fail. "
                         "A missing verification_method warns unless --fail-on-missing-method.",
        "needs_network": False,
    },
    {
        "command": "verify soup",
        "checks": "The SOUP register against the dependency manifests, and each "
                  "item against the OSV vulnerability database, honouring "
                  "documented per-CVE acceptances.",
        "options": {"required": [], "optional": ["--manifest", "--fail-on-drift", "--offline-mode"]},
        "blocking": "conditional",
        "blocking_note": "Known vulnerabilities always fail, and so does an unreachable "
                         "osv.dev unless --offline-mode warn. Drift from the manifests "
                         "warns unless --fail-on-drift.",
        "needs_network": True,
    },
    {
        "command": "verify completion",
        "checks": "CR closure: mandatory CR fields, that the CR's affected_items "
                  "exist, and verification evidence for each. Approval is `workflow check-approval`.",
        "options": {
            "required": ["--cr"],
            "optional": ["--junit"],
        },
        "blocking": "always",
        "blocking_note": "",
        "needs_network": False,
    },
    {
        "command": "workflow check-changes",
        "checks": "That a branch carries the DHF and code changes its CR implies.",
        "options": {
            "required": ["--cr"],
            "optional": ["--since-ref", "--code-path"],
        },
        "blocking": "always",
        "blocking_note": "Code-change enforcement applies only when --code-path "
                         "is given.",
        "needs_network": False,
    },
    {
        "command": "workflow check-approval",
        "checks": "That an approving review on the PR names the commit being "
                  "merged, so the approval covers what ships.",
        "options": {
            "required": ["--pr"],
            "optional": ["--token"],
        },
        "blocking": "always",
        "blocking_note": "An approval of an earlier commit is stale and fails.",
        "needs_network": True,
    },
)
