"""Tests for medharness.client.DHFClient."""

from pathlib import Path

from medharness.client import DHFClient


def _write_minimal_dhf_config(dhf: Path) -> None:
    (dhf / "config").mkdir(parents=True, exist_ok=True)
    (dhf / "config" / "global.yaml").write_text(
        "global_lifecycle:\n"
        "  states:\n"
        "    - id: planned\n      label: Planned\n"
        "    - id: in_review\n      label: In Review\n"
        "    - id: designing\n      label: Designing\n"
        "    - id: implementing\n      label: Implementing\n"
        "    - id: completed\n      label: Completed\n      is_stable: true\n"
        "    - id: cancelled\n      label: Cancelled\n      is_stable: true\n"
    )
    (dhf / "config" / "doc_types").mkdir(exist_ok=True)
    (dhf / "config" / "doc_types" / "cr.yaml").write_text(
        "code: CR\nname: Change Request\nprefix: CR-\ndirectory: 09_cr\n"
        "properties:\n"
        "  - id\n"
        "  - name: title\n    format: short_text\n    label: Title\n"
        "  - name: status\n    format: select\n    label: Status\n"
        "  - name: content\n    format: long_text\n    label: Content\n"
        "  - name: description\n    format: long_text\n    label: Description\n"
        "  - name: justification\n    format: long_text\n    label: Justification\n"
        "  - name: priority\n    format: select\n    label: Priority\n"
        "  - name: requested_by\n    format: short_text\n    label: Requested By\n"
        "  - name: target_version\n    format: short_text\n    label: Target Version\n"
        "  - name: category\n    format: short_text\n    label: Category\n"
        "lifecycle:\n"
        "  transitions:\n"
        "    - from_states: [null]\n      to_state: planned\n"
        "    - from_states: [planned]\n      to_state: in_review\n"
        "    - from_states: [in_review]\n      to_state: designing\n"
        "    - from_states: [designing]\n      to_state: implementing\n"
        "    - from_states: [implementing]\n      to_state: completed\n"
        "    - from_states: [implementing]\n      to_state: designing\n"
        "    - from_states: [planned, in_review, designing, implementing]\n      to_state: cancelled\n"
    )
    (dhf / "items" / "09_cr").mkdir(parents=True, exist_ok=True)


def _init_git(dhf: Path) -> None:
    import subprocess
    subprocess.run(["git", "init", "-b", "main"], cwd=dhf, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=dhf, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=dhf, capture_output=True)


def test_dhfclient_instantiation(tmp_path):
    dhf = tmp_path / "DHF"
    _write_minimal_dhf_config(dhf)

    client = DHFClient(dhf)
    assert client is not None


def test_dhfclient_list_items_returns_list(tmp_path):
    dhf = tmp_path / "DHF"
    _write_minimal_dhf_config(dhf)

    client = DHFClient(dhf)
    items = client.list_items()
    assert isinstance(items, list)


def test_dhfclient_get_item_returns_none_for_unknown(tmp_path):
    dhf = tmp_path / "DHF"
    _write_minimal_dhf_config(dhf)

    client = DHFClient(dhf)
    assert client.get_item("CR-999") is None


def test_dhfclient_create_and_get_item(tmp_path):
    dhf = tmp_path / "DHF"
    _write_minimal_dhf_config(dhf)
    _init_git(dhf)

    client = DHFClient(dhf)
    result = client.create_item("CR", {"title": "Test CR"}, author="tester")
    assert result["id"].startswith("CR-")

    item = client.get_item(result["id"])
    assert item is not None
    assert item["title"] == "Test CR"


def test_dhfclient_transition_item(tmp_path):
    dhf = tmp_path / "DHF"
    _write_minimal_dhf_config(dhf)
    _init_git(dhf)

    client = DHFClient(dhf)
    result = client.create_item("CR", {"title": "Transition Test"}, author="tester")
    cr_id = result["id"]

    transitioned = client.transition_item(cr_id, "in_review", performed_by="tester")
    assert transitioned["id"] == cr_id
    assert transitioned["status"] == "in_review"


def test_dhfclient_get_cr_context(tmp_path):
    dhf = tmp_path / "DHF"
    _write_minimal_dhf_config(dhf)
    _init_git(dhf)

    client = DHFClient(dhf)
    result = client.create_item("CR", {"title": "Context Test"}, author="tester")
    cr_id = result["id"]

    context = client.get_cr_context(cr_id)
    assert context["cr"] is not None
    assert context["cr"]["title"] == "Context Test"
    assert "spec" in context
