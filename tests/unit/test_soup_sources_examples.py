"""The soup-sources.yaml example in adopting.md must actually work.

The `command` source is the only escape hatch for a package manager with no
parser. Its example embedded multi-line Python in a double-quoted YAML string —
and YAML folds those newlines into spaces, so it collapsed to one unparseable
line. It could never have run, and was copied from the package into the docs
with the bug intact.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from dhfkit.tests.fixtures import bare_dhf

ADOPTING = Path(__file__).resolve().parents[2] / "docs" / "adopting.md"


def _examples() -> list[dict]:
    """Every entry of the documented soup-sources.yaml."""
    text = ADOPTING.read_text(encoding="utf-8")
    section = text[text.index("### Persistent source configuration"):]
    block = re.search(r"```yaml\n(.*?)```", section, re.S).group(1)
    return yaml.safe_load(block)["sources"]


EXAMPLES = _examples()
COMMANDS = [e for e in EXAMPLES if e.get("type") == "command"]


def test_the_scan_found_examples() -> None:
    """A silent zero would make every check below vacuous."""
    assert len(EXAMPLES) >= 4, EXAMPLES
    assert COMMANDS, "no command examples found — the escape hatch is undocumented"


@pytest.mark.parametrize("entry", EXAMPLES, ids=range(len(EXAMPLES)))
def test_an_example_names_a_source_type(entry: dict) -> None:
    assert entry.get("type") in {"manifest", "command", "manual"}


@pytest.mark.parametrize("entry", COMMANDS, ids=range(len(COMMANDS)))
def test_a_command_example_survives_yaml_parsing(entry: dict) -> None:
    """The failure was here: newlines folded to spaces by a quoted scalar."""
    run = entry["run"]
    assert "\n" in run, (
        "this command is one line after YAML parsing. Embedded Python needs a "
        "block scalar (|); a quoted string folds its newlines into spaces."
    )


@pytest.mark.parametrize("entry", COMMANDS, ids=range(len(COMMANDS)))
def test_the_embedded_script_compiles(entry: dict) -> None:
    """Run the inner python -c against stub input and check it is parseable.

    The tool itself (syft, pnpm) is not installed here, so the pipeline cannot
    run end to end. What can be checked is that the Python the example embeds is
    syntactically valid — which is exactly what the folded version was not.
    """
    run = entry["run"]
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
    """End to end through build soup, with a stub standing in for the tool."""

    def test_a_block_scalar_command_produces_items(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from medharness.cli import main

        dhf = tmp_path / "DHF"
        bare_dhf(dhf)
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
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "soup"])
        payload = json.loads(r.stdout.splitlines()[0])
        assert payload["outcome"] == "completed", payload["errors"]
        assert payload["packages_found"] == 1
        assert len(payload["items_created"]) == 1
