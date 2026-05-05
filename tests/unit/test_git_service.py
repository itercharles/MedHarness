"""Tests for medharness.services.git — commit_dhf_item."""

from pathlib import Path

from medharness.services.git import commit_dhf_item


def test_commit_dhf_item_stages_and_commits(tmp_path):
    dhf_path = tmp_path / "DHF"
    item_dir = dhf_path / "items" / "09_cr"
    item_dir.mkdir(parents=True)

    import subprocess
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, capture_output=True, check=True)

    item_file = item_dir / "CR-001.yaml"
    item_file.write_text("id: CR-001\n", encoding="utf-8")

    result = commit_dhf_item(dhf_path, "CR-001", "chore: test commit")

    assert result["staged"] is True
    assert result["committed"] is True
    assert result["pushed"] is False


def test_commit_dhf_item_raises_when_item_not_found(tmp_path):
    dhf_path = tmp_path / "DHF"
    dhf_path.mkdir()

    import subprocess
    import pytest
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, capture_output=True, check=True)

    with pytest.raises(FileNotFoundError, match="CR-999"):
        commit_dhf_item(dhf_path, "CR-999", "chore: nothing")


def test_commit_dhf_item_noop_when_no_changes(tmp_path):
    dhf_path = tmp_path / "DHF"
    item_dir = dhf_path / "items" / "09_cr"
    item_dir.mkdir(parents=True)

    import subprocess
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, capture_output=True, check=True)

    item_file = item_dir / "CR-002.yaml"
    item_file.write_text("id: CR-002\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    # Initial commit needs an identity — set once for the seed commit only
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

    result = commit_dhf_item(dhf_path, "CR-002", "chore: no change")

    assert result["staged"] is False
    assert result["committed"] is False
