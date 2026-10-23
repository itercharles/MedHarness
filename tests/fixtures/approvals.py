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

from fixtures.starter import keep_the_starter_text, verify_the_starter
from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf
from medharness.services.approval import fingerprint, new_ulid


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
    junit: Path | None = None

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

    def manifest(self, version: str = "1.0.0") -> dict:
        return yaml.safe_load((self.dhf / "releases" / version / "manifest.yaml").read_text())

    def ready_to_release(self) -> None:
        """Close CR-001 over SRS-001 and verify every requirement, so `build release` passes."""
        keep_the_starter_text(self.dhf)
        self.edit("CR-001", status="completed", implementation_notes="n", affected_risk_items=[],
                  affected_items=["SRS-001"])
        self.junit = verify_the_starter(self.dhf, self.root / "test-results")

    def release(self, version: str = "1.0.0", *extra: str):
        result = self.run("build", "release", "--version", version, "--out-dir", str(self.root / "rel" / version),
                          "--junit", str(self.junit), "--write", *extra)
        assert result.exit_code == 0, result.stderr
        return result

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
        return self.run("item", "approve", "--key", str(self.keys[who]), "--yes", *extra)

    def sign(self, who: str, version: str = "1.0.0"):
        return self.approve(who, "--release", version)

    def forge(self, who: str, *, signer: str, roles: list[str], documents: list[dict], release: str = "1.0.0",
              file_id: str | None = None) -> str:
        """A record signed by *who*'s key with whatever it claims, which `item approve` would refuse.

        *file_id* is what the record's `id` says; it defaults to the file name.
        """
        uid = new_ulid()
        folder = self.dhf / "approvals" / f"release-{release}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{uid}.yaml"
        record = {
            "id": file_id or uid, "release": release, "signer": signer, "roles": roles,
            "signed_at": "2026-10-22T09:30:00Z", "statement": "forged", "documents": documents,
            "key": fingerprint(self.keys[who].with_name(self.keys[who].name + ".pub").read_text()),
        }
        path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", str(self.keys[who]), "-n", "medharness-approval", str(path)],
                       check=True, capture_output=True, stdin=subprocess.DEVNULL)
        return uid

    def pin(self, code: str, version: str = "1.0.0") -> dict:
        """The manifest's entry for a document, as a record names it."""
        return {"id": code, "hash": self.manifest(version)["documents"][code]["hash"]}


def build_project(tmp_path: Path, *, with_approvers: bool = True) -> Project:
    """A starter DHF on `main`, then a `feat` branch.

    Lead holds software-lead, Pat product-manager and risk-manager, Sam system-architect, Quinn
    quality-lead. All are on the list at `main` when *with_approvers*. Mallory's key is on no list.
    """
    require_ssh_keygen()
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    project = Project(tmp_path / "repo", {n: make_key(keys_dir, n) for n in ("Lead", "Pat", "Sam", "Quinn", "Mallory")})
    project.root.mkdir()
    scaffold_dhf(project.root)
    replace_placeholders(project.root, "Approvals")
    if with_approvers:
        project.write_approvers([
            entry("Lead", project.keys["Lead"], ["software-lead"]),
            entry("Pat", project.keys["Pat"], ["product-manager", "risk-manager"]),
            entry("Sam", project.keys["Sam"], ["system-architect"]),
            entry("Quinn", project.keys["Quinn"], ["quality-lead"]),
        ])
    git(project.root, "init", "-q", "-b", "main")
    git(project.root, "config", "user.email", "t@example.com")
    git(project.root, "config", "user.name", "t")
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "base")
    git(project.root, "checkout", "-q", "-b", "feat")
    return project
