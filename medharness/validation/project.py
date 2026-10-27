"""Scratch projects the cases start from, built from the starter DHF `init` writes."""

from __future__ import annotations

import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

from dhfkit.store import open_store
from medharness.scaffold import replace_placeholders, scaffold_dhf


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def item_path(repo: Path, uid: str) -> Path:
    return next((repo / "DHF" / "items").rglob(f"{uid}.yaml"))


def edit(repo: Path, uid: str, **fields) -> None:
    path = item_path(repo, uid)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(fields)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def keep_the_starter_text(dhf: Path) -> None:
    """Opt a project out of the placeholder check, as a project may in `global.yaml`.

    The starter items say "Replace with your own", which `verify dhf --strict` and
    `build release` rightly refuse. A case about something else runs on them anyway.
    """
    global_yaml = dhf / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text(encoding="utf-8") + "\nplaceholder_patterns: []\n", encoding="utf-8")


def verify_the_starter(dhf: Path, out: Path) -> Path:
    """Give every starter requirement a Test method and a passing test, and return the JUnit."""
    store = open_store(dhf)
    requirements = set(store.config.requirement_types())
    ids = [item["id"] for item in store.list_items() if item["type"] in requirements]
    for uid in ids:
        path = next((dhf / "items").rglob(f"{uid}.yaml"))
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data.update(verification_method=["Test"], verification_criteria="It works as stated.")
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    junit = out / "junit.xml"
    junit.write_text(
        '<testsuite name="s"><testcase classname="c" name="test_all">'
        f'<properties><property name="medharness.links" value="{",".join(ids)}"/></properties>'
        "</testcase></testsuite>", encoding="utf-8")
    return junit


def junit(path: Path, *tests: tuple) -> Path:
    """JUnit results of *tests*, each `(name, linked IDs or None, outcome[, test points])`.

    The outcome is `passed`, `failed`, `error` or `skipped`.
    """
    cases = []
    for name, links, outcome, *points in tests:
        props = [("medharness.links", links)] if links else []
        props += [("medharness.testing", points[0])] if points and points[0] else []
        body = "".join(f'<property name="{k}" value="{v}"/>' for k, v in props)
        body = f"<properties>{body}</properties>" if body else ""
        body += {"passed": "", "failed": '<failure message="assertion failed"/>',
                 "error": '<error message="crashed"/>', "skipped": '<skipped message="skipped"/>'}[outcome]
        cases.append(f'<testcase classname="c" name="{escape(name)}">{body}</testcase>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'<testsuite name="s">{"".join(cases)}</testsuite>', encoding="utf-8")
    return path


def scaffolded(root: Path, name: str) -> None:
    """The starter DHF exactly as `init` writes it, with the project's name."""
    scaffold_dhf(root)
    replace_placeholders(root, name)


def starter(root: Path, name: str) -> None:
    """The starter DHF, its text kept and every requirement verified, with its JUnit in `results/`."""
    scaffolded(root, name)
    keep_the_starter_text(root / "DHF")
    verify_the_starter(root / "DHF", root / "results")
    (root / ".gitignore").write_text("results/\n", encoding="utf-8")


def commit_base(root: Path, branch: str = "feat") -> None:
    """Commit what is there as `main` and start *branch* from it."""
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "validation@medharness.invalid")
    git(root, "config", "user.name", "validation")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    git(root, "checkout", "-q", "-b", branch)
