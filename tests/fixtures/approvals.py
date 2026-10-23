"""A repository with an approvers list and throwaway keys, for the tests of signed approvals."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf
from medharness.services.approval import content_hash, fingerprint, new_ulid


def require_ssh_keygen() -> None:
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen is not installed")


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_key(directory: Path, name: str) -> Path:
    path = directory / name
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(path)],
                   check=True, capture_output=True)
    return path


def entry(name: str, key: Path, roles: list[str], *, no_touch_required: bool = True) -> dict:
    """An approvers.yaml entry. Test keys are not hardware keys, so they never prove a touch."""
    return {"name": name, "principal": name.lower(), "roles": roles,
            "keys": [key.with_name(key.name + ".pub").read_text().strip()],
            "no_touch_required": no_touch_required}


@dataclass
class Project:
    root: Path
    keys: dict[str, Path] = field(default_factory=dict)

    @property
    def dhf(self) -> Path:
        return self.root / "DHF"

    @property
    def approvers_file(self) -> Path:
        return self.dhf / "config" / "approvers.yaml"

    def write_approvers(self, entries: list[dict]) -> None:
        self.approvers_file.write_text(yaml.safe_dump(entries), encoding="utf-8")

    def item_file(self, uid: str) -> Path:
        return next((self.dhf / "items").rglob(f"{uid}.yaml"))

    def records(self) -> list[Path]:
        """The approval records in the log, oldest first."""
        return sorted((self.dhf / "approvals").rglob("*.yaml"), key=lambda p: p.stem)

    def edit(self, uid: str, **fields) -> None:
        path = self.item_file(uid)
        data = yaml.safe_load(path.read_text())
        data.update(fields)
        path.write_text(yaml.safe_dump(data))

    def run(self, *args: str, input: str | None = None):
        result = CliRunner().invoke(main, ["--dhf", str(self.dhf), *args], input=input)
        assert "Traceback" not in (result.stderr or "")
        return result

    def verify(self, *extra: str) -> dict:
        result = self.run("verify", "approval", "--since-ref", "main", *extra)
        answer = json.loads(result.stdout.splitlines()[0])
        assert result.exit_code == (0 if answer["passed"] else 1), result.stderr
        return answer

    def approve(self, who: str, *extra: str):
        return self.run("item", "approve", "--key", str(self.keys[who]), "--since-ref", "main", "--yes", *extra)

    def forge(self, who: str, *, signer: str, roles: list[str], items: list[dict], file_id: str | None = None) -> str:
        """A record signed by *who*'s key with whatever it claims, which `item approve` would refuse.

        *file_id* is what the record's `id` says; it defaults to the file name.
        """
        uid = new_ulid()
        folder = self.dhf / "approvals" / "unscoped"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{uid}.yaml"
        record = {
            "id": file_id or uid, "cr": None, "signer": signer, "roles": roles, "signed_at": "2026-10-22T09:30:00Z",
            "statement": "forged", "items": items,
            "key": fingerprint(self.keys[who].with_name(self.keys[who].name + ".pub").read_text()),
        }
        path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", str(self.keys[who]), "-n", "medharness-approval", str(path)],
                       check=True, capture_output=True, stdin=subprocess.DEVNULL)
        return uid

    def pin(self, uid: str) -> dict:
        return {"id": uid, "hash": content_hash(self.item_file(uid))}


def build_project(tmp_path: Path, *, with_approvers: bool = True) -> Project:
    """A starter DHF on `main`, then a `feat` branch.

    Lead holds software-lead and ccb, Pat product-manager. Both are on the list at `main`
    when *with_approvers*. A third key, Mallory, is on no list.
    """
    require_ssh_keygen()
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    project = Project(tmp_path / "repo", {n: make_key(keys_dir, n) for n in ("Lead", "Pat", "Mallory")})
    project.root.mkdir()
    scaffold_dhf(project.root)
    replace_placeholders(project.root, "Approvals")
    if with_approvers:
        project.write_approvers([
            entry("Lead", project.keys["Lead"], ["software-lead", "ccb"]),
            entry("Pat", project.keys["Pat"], ["product-manager"]),
        ])
    git(project.root, "init", "-q", "-b", "main")
    git(project.root, "config", "user.email", "t@example.com")
    git(project.root, "config", "user.name", "t")
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "base")
    git(project.root, "checkout", "-q", "-b", "feat")
    return project
