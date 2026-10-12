"""Helpers for tests that run on the scaffolded starter DHF."""

from __future__ import annotations

from pathlib import Path


def keep_the_starter_text(dhf: Path) -> None:
    """Opt a project out of the placeholder check, as a project may in `global.yaml`.

    The starter items say "Replace with your own", which `verify dhf --strict` and
    `build release` rightly refuse. A test of something else — a release's
    mechanics, say — runs on them anyway.
    """
    global_yaml = dhf / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text() + "\nplaceholder_patterns: []\n", encoding="utf-8")


def verify_the_starter(dhf: Path, out: Path) -> Path:
    """Give every starter requirement a Test method and a passing test, and return the JUnit.

    `build release` requires every requirement to be verified by the JUnit it is given. A
    test of a release's mechanics gives it this.
    """
    import yaml

    from dhfkit.store import open_store

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
