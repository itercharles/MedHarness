"""A cycle in the traceability graph passed every gate.

The V-model is directed: a customer requirement gives rise to a system
requirement, which gives rise to a software one. A cycle means two items each
derive from the other, so neither has an origin and the matrix loses the
direction that makes it a matrix.

`medharness/graph.py` has had `validate_for_cycles` since it was written. The
only caller was `_run_acceptance_gate`, which is not on the `verify dhf` path —
so the detection existed, was correct, and never ran on anything a project
would notice. Built and never wired, the same as the closure criteria and
`soup-sync`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from dhfkit.traceability import find_link_cycles
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


class TestFindLinkCycles:
    def test_a_two_item_cycle(self) -> None:
        items = [{"id": "SYS-001", "derives_from": ["SRS-001"]},
                 {"id": "SRS-001", "derives_from": ["SYS-001"]}]
        assert find_link_cycles(items) == [["SRS-001", "SYS-001"]]

    def test_a_longer_cycle(self) -> None:
        items = [{"id": "A-1", "derives_from": ["A-2"]},
                 {"id": "A-2", "derives_from": ["A-3"]},
                 {"id": "A-3", "derives_from": ["A-1"]}]
        assert find_link_cycles(items) == [["A-1", "A-2", "A-3"]]

    def test_a_self_link_is_the_degenerate_cycle(self) -> None:
        """An item deriving from itself is as wrong as a two-item loop."""
        assert find_link_cycles([{"id": "S-1", "derives_from": ["S-1"]}]) == [["S-1"]]

    def test_a_directed_chain_is_not_a_cycle(self) -> None:
        items = [{"id": "SYS-001"},
                 {"id": "SRS-001", "derives_from": ["SYS-001"]},
                 {"id": "SRS-002", "derives_from": ["SYS-001"]}]
        assert find_link_cycles(items) == []

    def test_a_dangling_link_yields_no_cycle(self) -> None:
        """A link to something absent belongs to find_dangling_links.

        This holds for a structural reason rather than because of the guard that
        drops absent targets: a target that is not an item has no outgoing
        edges, so no walk can return through it. The behaviour is pinned here;
        the guard is not what produces it, and a test claiming otherwise would
        pass with the guard removed.
        """
        items = [
            {"id": "SRS-001", "derives_from": ["SYS-404"]},
            {"id": "SRS-002", "derives_from": ["SYS-404", "SRS-001"]},
        ]
        assert find_link_cycles(items) == []

    def test_one_cycle_is_reported_once(self) -> None:
        """Entering the same loop from two places is still one finding."""
        items = [{"id": "A-1", "derives_from": ["A-2"]},
                 {"id": "A-2", "derives_from": ["A-1"]},
                 {"id": "B-1", "derives_from": ["A-1"]}]
        assert find_link_cycles(items) == [["A-1", "A-2"]]

    def test_the_ordering_is_stable(self) -> None:
        """Each cycle starts from its lowest ID, so a re-run reads the same."""
        forward = [{"id": "A-2", "derives_from": ["A-1"]},
                   {"id": "A-1", "derives_from": ["A-2"]}]
        reversed_ = list(reversed(forward))
        assert find_link_cycles(forward) == find_link_cycles(reversed_) == [["A-1", "A-2"]]


class TestTheGateReportsIt:
    @pytest.fixture
    def cyclic(self, tmp_path: Path) -> Path:
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Cycles")
        dhf = tmp_path / "DHF"
        sys_item = next((dhf / "items").rglob("SYS-001.yaml"))
        data = yaml.safe_load(sys_item.read_text(encoding="utf-8"))
        data["derives_from"] = ["SRS-001"]      # SRS-001 already derives from SYS-001
        sys_item.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                            encoding="utf-8")
        return dhf

    def _verify(self, dhf: Path) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, "-m", "medharness", "--dhf", str(dhf), "verify", "dhf"],
            capture_output=True, text=True,
        )
        assert "Traceback" not in proc.stderr, proc.stderr[-400:]
        return proc.returncode, json.loads(proc.stdout.splitlines()[0])

    def test_verify_dhf_fails_and_names_the_path(self, cyclic: Path) -> None:
        code, payload = self._verify(cyclic)
        assert code == 1
        assert payload["passed"] is False
        cycles = [e for e in payload["errors"] if "cycle" in e.lower()]
        assert cycles, payload["errors"]
        assert "SRS-001" in cycles[0] and "SYS-001" in cycles[0]

    def test_the_scaffold_itself_has_none(self, tmp_path: Path) -> None:
        """The check is only useful if a healthy DHF stays green."""
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Clean")
        code, payload = self._verify(tmp_path / "DHF")
        assert code == 0, payload["errors"]


class TestTheGateCopiesEveryFinding:
    """`cycles` was computed, returned, and dropped by a hand-written copy.

    `ci_structural_gate` rebuilds `results["traceability"]` field by field from
    `validate_traceability()`. A finding the adapter reports and that copy omits
    is computed and thrown away — which is what happened here, and is the same
    drift that has bitten `_UPGRADE_MAP`, the gates manifest, and the envelope's
    reader sites.
    """

    def test_no_finding_key_is_left_behind(self, tmp_path: Path) -> None:
        from dhfkit.local_adapter import LocalDHFAdapter
        from medharness.services.ci import ci_structural_gate

        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Copy")
        dhf = tmp_path / "DHF"

        produced = set(LocalDHFAdapter(dhf).validate_traceability())
        copied = set(ci_structural_gate(dhf)["details"]["results"]["traceability"])

        # Keys the gate deliberately reshapes or reports elsewhere.
        elsewhere = {"orphans", "risk_chain", "deprecation_warnings"}
        missing = produced - copied - elsewhere
        assert not missing, (
            f"validate_traceability reports {sorted(missing)} and the gate's copy "
            f"drops them — computed, then thrown away"
        )
