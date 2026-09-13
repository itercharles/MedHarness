"""The commented examples in soup-sources.yaml must actually work.

The `command` source is the only escape hatch for a package manager with no
parser. Its one shipped example embedded multi-line Python in a double-quoted
YAML string — and YAML folds those newlines into spaces, so the example
collapsed to one unparseable line. It could never have run.

Uncommenting an example and running it is the only check that catches that.
"""

from __future__ import annotations

import importlib.resources as resources
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

TEMPLATE = resources.files("dhfkit").joinpath("templates/config/soup-sources.yaml")


def _examples() -> list[str]:
    """Every commented `- type: …` block, uncommented."""
    text = TEMPLATE.read_text()
    stripped = "\n".join(
        re.sub(r"^  # ?", "", line) if line.startswith("  #") else ""
        for line in text.splitlines()
    )
    blocks, current = [], []
    for line in stripped.splitlines():
        if line.startswith("- type:"):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current and (line.startswith(" ") or not line.strip()):
            current.append(line)
        elif current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return [b.rstrip() for b in blocks if b.strip()]


EXAMPLES = _examples()
COMMANDS = [b for b in EXAMPLES if "type: command" in b]


def test_the_scan_found_examples() -> None:
    """A silent zero would make every check below vacuous."""
    assert len(EXAMPLES) >= 4, [e[:40] for e in EXAMPLES]
    assert COMMANDS, "no command examples found — the escape hatch is undocumented"


@pytest.mark.parametrize("block", EXAMPLES, ids=range(len(EXAMPLES)))
def test_an_example_is_valid_yaml(block: str) -> None:
    parsed = yaml.safe_load(block)
    assert isinstance(parsed, list) and parsed[0].get("type")


@pytest.mark.parametrize("block", COMMANDS, ids=range(len(COMMANDS)))
def test_a_command_example_survives_yaml_parsing(block: str) -> None:
    """The failure was here: newlines folded to spaces by a quoted scalar."""
    run = yaml.safe_load(block)[0]["run"]
    assert "\n" in run, (
        "this command is one line after YAML parsing. Embedded Python needs a "
        "block scalar (|); a quoted string folds its newlines into spaces."
    )


@pytest.mark.parametrize("block", COMMANDS, ids=range(len(COMMANDS)))
def test_the_embedded_script_compiles(block: str) -> None:
    """Run the inner python -c against stub input and check it is parseable.

    The tool itself (syft, pnpm) is not installed here, so the pipeline cannot
    run end to end. What can be checked is that the Python the example embeds is
    syntactically valid — which is exactly what the folded version was not.
    """
    run = yaml.safe_load(block)[0]["run"]
    m = re.search(r'python3 -c "\n(.*?)\n\s*"\s*$', run, re.S)
    if not m:
        pytest.skip("no embedded python in this example")
    script = m.group(1)
    proc = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse({script!r})"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"embedded script does not parse:\n{proc.stderr}"


class TestTheCommandSourceRunsForReal:
    """End to end through soup-sync, with a stub standing in for the tool."""

    def test_a_block_scalar_command_produces_items(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from dhfkit.cli import main as dhfkit_main
        from medharness.cli import main

        dhf = tmp_path / "DHF"
        CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
        (dhf / "config" / "doc_types" / "soup.yaml").write_bytes(
            resources.files("dhfkit")
            .joinpath("templates/config/doc_types/soup.yaml").read_bytes()
        )
        (tmp_path / "stub.py").write_text(
            "import json\n"
            "print(json.dumps([{'dependencies': {'react': {'version': '18.2.0'}}}]))\n"
        )
        (dhf / "config" / "soup-sources.yaml").write_text(
            "sources:\n"
            "  - type: command\n"
            "    run: |\n"
            f"      {sys.executable} stub.py | {sys.executable} -c \"\n"
            "      import sys, json\n"
            "      for root in json.load(sys.stdin):\n"
            "          for name, info in (root.get('dependencies') or {}).items():\n"
            "              print(json.dumps({'name': name, 'version': info['version'],\n"
            "                                'ecosystem': 'npm'}))\n"
            "      \"\n"
        )
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "soup-sync", "--write"])
        payload = json.loads(r.stdout.splitlines()[0])
        assert payload["outcome"] == "completed", payload["errors"]
        assert payload["packages_found"] == 1
        assert len(payload["items_created"]) == 1
