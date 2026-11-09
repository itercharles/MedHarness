"""There is one definition of approved, and one gate that holds it.

Before 0.24.0 the stage gate read a GitHub label while the closure gate required
an APR record — one workflow, two unrelated definitions of approved, and the
weaker one decided whether a stage could advance. 0.24.0 made both read the
review; this removes the second reader entirely.

Approval is a pull-request review. It lives in GitHub, not in the DHF, so a gate
that reads the DHF has no business ruling on it. GitHub's branch protection
decides whether the commit being merged was approved; `verify tests --cr` asks
whether what the CR changed is verified. Neither answers the other's question.

What this guards is the separation. A second definition creeps back the moment
closure grows an approval check again — that is how the label and the APR record
came to disagree in the first place.
"""

from __future__ import annotations

def test_no_verify_command_reads_a_pull_request() -> None:
    from medharness.cli import main

    takes_pr = [name for name, cmd in main.commands["verify"].commands.items()
                if any("--pr" in p.opts for p in cmd.params)]
    assert not takes_pr, f"verify {takes_pr} takes a pull request again"
