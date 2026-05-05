"""Tests for CLI commands: item transitions, item transition"""
import json

from click.testing import CliRunner

from dhfkit.cli import main


def _parse_json(output: str):
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            return json.loads(line)
    raise ValueError(f"No JSON found in output: {output!r}")


def test_item_transitions_existing_cr(populated_dhf):
    """item transitions returns available transitions for a CR item."""
    result = CliRunner().invoke(main, ["--dhf", str(populated_dhf), "item", "transitions", "CR-001"])
    assert result.exit_code == 0, result.output + result.stderr
    data = _parse_json(result.output)
    assert data["item_id"] == "CR-001"
    assert "current_status" in data
    assert isinstance(data["transitions"], list)


def test_item_transitions_not_found(populated_dhf):
    """item transitions fails for unknown item."""
    result = CliRunner().invoke(main, ["--dhf", str(populated_dhf), "item", "transitions", "FAKE-999"])
    assert result.exit_code == 1


def test_item_transition_execute(populated_dhf):
    """item transition executes a valid lifecycle transition."""
    result = CliRunner().invoke(
        main, ["--dhf", str(populated_dhf), "item", "transition", "CR-001", "approved"]
    )
    assert result.exit_code == 0, result.output + result.stderr
    data = _parse_json(result.output)
    assert data["id"] == "CR-001"
    assert data.get("status") == "approved"


def test_item_transition_invalid_state(populated_dhf):
    """item transition fails for invalid state."""
    result = CliRunner().invoke(
        main, ["--dhf", str(populated_dhf), "item", "transition", "CR-001", "bogus"]
    )
    assert result.exit_code == 1
