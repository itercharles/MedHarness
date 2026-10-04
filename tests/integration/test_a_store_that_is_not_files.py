"""The CLI works on items kept somewhere other than YAML files.

An adapter is five methods (`dhfkit.adapter.DHFAdapter`); everything else — the
schema, links, ID allocation, the lifecycle, the checks — must behave the same
on top of it. This registers an in-memory adapter the way an installed package
would, points a project's `global.yaml` at it, and runs the real commands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

import dhfkit.adapter as adapter_module
from dhfkit.local_adapter import LocalDHFAdapter
from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


class MemoryAdapter:
    tracks_files = False

    def __init__(self, items: dict):
        self.items = items
        self.ever: set[str] = set(items)

    def load_all(self):
        return list(self.items.values())

    def load_by_uid(self, uid):
        return self.items.get(uid)

    def save(self, item):
        self.items[item.uid] = item
        self.ever.add(item.uid)

    def delete(self, uid):
        return self.items.pop(uid, None) is not None

    def used_ids(self):
        return set(self.ever)

    def integrity_errors(self):
        return []


class _EntryPoint:
    def __init__(self, name, factory):
        self.name, self._factory = name, factory

    def load(self):
        return self._factory


@pytest.fixture
def memory_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A scaffolded project whose items live in memory, none on disk."""
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Memory")
    dhf = tmp_path / "DHF"
    yaml_adapter = LocalDHFAdapter(dhf / "items", None)
    items = {i.uid: i for i in yaml_adapter.load_all()}
    for path in (dhf / "items").rglob("*.yaml"):
        path.unlink()
    shared = MemoryAdapter(items)
    monkeypatch.setattr(
        adapter_module, "entry_points",
        lambda group: [_EntryPoint("memory", lambda **_: shared)] if group == "dhfkit.adapters" else [],
    )
    global_yaml = dhf / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text() + "\nstore:\n  type: memory\n")
    return dhf, shared


def _run(dhf: Path, *args: str):
    result = CliRunner().invoke(main, ["--dhf", str(dhf), *args])
    assert "Traceback" not in (result.stderr or "") + result.output, result.stderr
    return result


class TestItemsInMemory:
    def test_items_are_read_from_the_adapter_not_from_files(self, memory_project) -> None:
        dhf, store = memory_project
        assert not list((dhf / "items").rglob("*.yaml"))
        result = _run(dhf, "item", "list", "--type", "SRS")
        assert result.exit_code == 0
        ids = [json.loads(line)["id"] for line in result.stdout.splitlines()]
        assert ids and all(i.startswith("SRS-") for i in ids)
        assert _run(dhf, "item", "get", ids[0]).exit_code == 0

    def test_a_created_item_is_stored_in_the_adapter_with_a_fresh_id(self, memory_project) -> None:
        dhf, store = memory_project
        before = set(store.items)
        result = _run(dhf, "item", "create", "--type", "SRS",
                      "--data", json.dumps({"title": "New", "content": "c", "derives_from": ["SYS-001"]}))
        assert result.exit_code == 0, result.stderr
        created = json.loads(result.stdout)["id"]
        assert created not in before and created in store.items
        assert not list((dhf / "items").rglob("*.yaml")), "a file was written"

    def test_the_schema_still_refuses_what_it_refuses_on_files(self, memory_project) -> None:
        dhf, store = memory_project
        before = dict(store.items)
        result = _run(dhf, "item", "update", "SRS-001", "--data", '{"nope": 1}')
        assert result.exit_code == 1 and "Unknown field" in result.stderr
        assert store.items == before

    def test_an_update_is_kept(self, memory_project) -> None:
        dhf, store = memory_project
        assert _run(dhf, "item", "update", "SRS-001", "--data", '{"title": "Changed"}').exit_code == 0
        assert _run(dhf, "item", "get", "SRS-001").stdout.count("Changed") == 1

    def test_the_lifecycle_applies(self, memory_project) -> None:
        dhf, _ = memory_project
        assert _run(dhf, "item", "transition", "CR-001", "design").exit_code == 0
        assert _run(dhf, "item", "transition", "CR-001", "completed").exit_code == 1

    def test_verify_dhf_gives_the_same_verdict_as_on_files(self, memory_project, tmp_path_factory) -> None:
        dhf, _ = memory_project
        on_memory = json.loads(_run(dhf, "verify", "dhf").stdout)
        plain = tmp_path_factory.mktemp("plain")
        scaffold_dhf(plain)
        replace_placeholders(plain, "Memory")
        on_files = json.loads(_run(plain / "DHF", "verify", "dhf").stdout)
        assert on_memory["passed"] == on_files["passed"]
        assert on_memory["summary"] == on_files["summary"]


class TestWhatNeedsFilesSaysSo:
    @pytest.mark.parametrize("args", [
        ["verify", "changes", "--cr", "CR-001"],
        ["build", "plan", "--cr", "CR-001"],
        ["build", "code", "--cr", "CR-001"],
        ["build", "plan", "--cr", "CR-001", "--prompt"],
    ])
    def test_a_command_that_reads_the_diff_refuses_with_the_reason(self, memory_project, args) -> None:
        dhf, _ = memory_project
        result = _run(dhf, *args)
        assert result.exit_code == 1
        assert "memory" in result.stdout + result.stderr and "Git" in result.stdout + result.stderr


class TestChoosingAStore:
    def test_an_uninstalled_store_names_what_is_installed(self, tmp_path: Path, monkeypatch) -> None:
        scaffold_dhf(tmp_path)
        monkeypatch.setattr(adapter_module, "entry_points", lambda group: [])
        global_yaml = tmp_path / "DHF" / "config" / "global.yaml"
        global_yaml.write_text(global_yaml.read_text() + "\nstore:\n  type: jira\n")
        result = _run(tmp_path / "DHF", "verify", "dhf")
        assert result.exit_code == 1
        assert "'jira' " in result.stderr and "not installed" in result.stderr and "yaml" in result.stderr

    def test_no_store_key_means_yaml_files(self, tmp_path: Path) -> None:
        scaffold_dhf(tmp_path)
        result = _run(tmp_path / "DHF", "item", "list", "--type", "SRS")
        assert result.exit_code == 0 and result.stdout.strip()
        assert yaml.safe_load((tmp_path / "DHF" / "config" / "global.yaml").read_text()).get("store") is None
