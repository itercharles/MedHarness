"""There is one definition of approved, and one gate that holds it.

Before 0.24.0 the stage gate read a GitHub label while the closure gate required
an APR record — one workflow, two unrelated definitions of approved, and the
weaker one decided whether a stage could advance. 0.24.0 made both read the
review; this removes the second reader entirely.

Approval is a pull-request review. It lives in GitHub, not in the DHF, so a gate
that reads the DHF has no business ruling on it. `workflow approval` asks
whether the commit being merged was approved; `verify completion` asks
whether the CR delivered what it promised. Neither answers the other's question.

What this guards is the separation. A second definition creeps back the moment
closure grows an approval check again — that is how the label and the APR record
came to disagree in the first place.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from medharness.services import ci as ci_module
from medharness.services.ci import cr_closure_gate


class TestClosureDoesNotRuleOnApproval:
    def test_the_closure_gate_takes_no_pull_request(self) -> None:
        params = set(inspect.signature(cr_closure_gate).parameters)
        assert "pr_number" not in params, (
            "closure accepts a pull request again, which is how it grows a "
            "second definition of approved"
        )

    def test_the_closure_gate_reads_no_approval_record(self) -> None:
        source = inspect.getsource(cr_closure_gate)
        for name in ("approval_evidence", "find_approvals", "design_review", "APR"):
            assert name not in source, (
                f"closure mentions {name!r}; approval belongs to "
                f"`workflow approval`, which reads the pull request"
            )

    def test_nothing_in_the_gate_module_reads_an_approval_record(self) -> None:
        """The helper it used to call is gone, not merely unreferenced."""
        assert not hasattr(ci_module, "_check_design_review")

    def test_closure_still_fails_a_cr_that_did_not_deliver(self, tmp_path: Path) -> None:
        """Dropping the approval check must not make the gate toothless."""
        import subprocess
        import sys

        import pytest
        import yaml

        subprocess.run([sys.executable, "-c", "from medharness.cli import main; main()", "init"],
                       cwd=tmp_path, capture_output=True, check=False)
        dhf = tmp_path / "DHF"
        if not (dhf / "config" / "global.yaml").exists():
            pytest.skip("scaffold unavailable")

        cr = dhf / "items" / "07_cr" / "CR-001.yaml"
        data = yaml.safe_load(cr.read_text())
        data.update({
            "implementation_notes": "n",
            "affected_risk_items": [],
            "triage_result": {"verdict": "approved"},
            "proposed_new_items": [{"type": "SRS", "title": "Never created"}],
        })
        cr.write_text(yaml.safe_dump(data), encoding="utf-8")

        result = cr_closure_gate("CR-001", dhf)
        assert result["passed"] is False
        assert any("Never created" in e for e in result["errors"]), (
            f"the CR proposed an item it never created; closure said: "
            f"{result['errors']}"
        )


class TestApprovalIsOwnedByOneGate:
    def test_only_the_approval_gate_reads_the_pull_request(self) -> None:
        from medharness.cli import main

        takes_pr = {
            f"{verb} {name}"
            for verb in ("verify", "workflow")
            for name, cmd in main.commands[verb].commands.items()
            if any("--pr" in p.opts for p in cmd.params)
        }
        assert "workflow approval" in takes_pr
        assert "verify completion" not in takes_pr, (
            "closure takes a pull request again"
        )
