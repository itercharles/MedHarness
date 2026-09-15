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
#: ``opt_in``      — inert until the project opts in; passes otherwise.
BLOCKING = ("always", "conditional", "opt_in")

GATES: tuple[dict[str, Any], ...] = (
    {
        "command": "verify dhf",
        "checks": "Schema validity, required traceability, dangling links, and "
                  "coverage between V-model layers.",
        "options": {
            "required": ["--dhf"],
            "optional": ["--fail-on-uncovered", "--coverage-pair",
                         "--run-schema/--no-run-schema",
                         "--run-traceability/--no-run-traceability"],
        },
        "blocking": "conditional",
        "blocking_note": "Schema errors, required-link failures, and dangling "
                         "links always fail. Coverage gaps warn unless "
                         "--fail-on-uncovered is passed.",
        "needs_network": False,
        "needs_safety_class": False,
    },
    {
        "command": "verify tests",
        "checks": "Requirement-to-test coverage from JUnit evidence, including "
                  "declared test points and verification levels.",
        "options": {
            "required": ["--dhf", "--junit-dir or --junit"],
            "optional": ["--requirement-type"],
        },
        "blocking": "always",
        "blocking_note": "Level requirements apply only once a safety class is "
                         "declared; unlabelled tests count as unit.",
        "needs_network": False,
        "needs_safety_class": False,
    },
    {
        "command": "verify soup",
        "checks": "SOUP items against the OSV vulnerability database, honouring "
                  "documented per-CVE acceptances.",
        "options": {"required": ["--dhf"], "optional": ["--offline-mode"]},
        "blocking": "always",
        "blocking_note": "An unreachable osv.dev fails by default; "
                         "--offline-mode warn tolerates it for air-gapped runners.",
        "needs_network": True,
        "needs_safety_class": False,
    },
    {
        "command": "verify classification",
        "checks": "That a software safety class is declared with a rationale, and "
                  "that the item types the class requires exist.",
        "options": {"required": ["--dhf"], "optional": []},
        "blocking": "opt_in",
        "blocking_note": "Warns and exits zero until software_safety_class is "
                         "declared in global.yaml. Once declared, a missing or "
                         "empty safety_activities.yaml fails: the opt-in has "
                         "been taken and the gate cannot check anything.",
        "needs_network": False,
        "needs_safety_class": True,
    },
    {
        "command": "change verify-completion",
        "checks": "CR closure: mandatory CR fields, an approval record, created "
                  "items, and test evidence for each.",
        "options": {
            "required": ["--dhf", "--cr"],
            "optional": ["--junit-dir", "--junit"],
        },
        "blocking": "always",
        "blocking_note": "",
        "needs_network": False,
        "needs_safety_class": False,
    },
    {
        "command": "change verify-branch",
        "checks": "That a branch carries the DHF and code changes its CR implies.",
        "options": {
            "required": ["--dhf", "--cr"],
            "optional": ["--since-ref", "--code-path"],
        },
        "blocking": "always",
        "blocking_note": "Code-change enforcement applies only when --code-path "
                         "is given.",
        "needs_network": False,
        "needs_safety_class": False,
    },
    {
        "command": "change verify-approval",
        "checks": "That an approving review on the PR names the commit being "
                  "merged, so the approval covers what ships.",
        "options": {
            "required": ["--cr", "--pr"],
            "optional": ["--token"],
        },
        "blocking": "always",
        "blocking_note": "An approval of an earlier commit is stale and fails.",
        "needs_network": True,
        "needs_safety_class": False,
    },
)


def gates_manifest() -> dict[str, Any]:
    """Return the manifest, including the envelope every gate answers with."""
    from medharness.services.ci import ENVELOPE_KEYS

    return {
        "envelope": list(ENVELOPE_KEYS),
        # 1 covers two cases the caller must distinguish by stdout: a gate that
        # ran and failed writes JSON; a usage error raised before it ran does not.
        "exit_codes": {
            "0": "gate passed; JSON on stdout",
            "1": "gate failed (JSON on stdout), or a usage error raised before "
                 "the gate ran (no stdout)",
            "2": "argument parsing error; no stdout",
        },
        "gates": list(GATES),
    }
