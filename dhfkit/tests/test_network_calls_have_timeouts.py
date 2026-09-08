"""Every outbound HTTP call must carry a timeout.

Python's `urlopen` has no default timeout: against a hung endpoint it blocks
forever. These run inside CI, where forever means the job hangs until the
runner's own limit kills it — with no message pointing at the cause.

Seven calls in `artifact_fetcher.py` had none. The check is source-level and
covers both packages, so a call added later is caught rather than discovered
during an outage.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Callables that open a connection and accept a timeout.
_NETWORK_CALLS = {"urlopen", "get", "post", "put", "delete", "head", "request"}
#: Modules whose `get`/`post` are network calls. A bare `.get()` on a dict is not.
_NETWORK_OWNERS = {"requests", "httpx", "session", "urllib", "urlopen"}


def _calls_without_timeout() -> list[tuple[str, int, str]]:
    found = []
    for package in ("dhfkit", "medharness"):
        for path in sorted((ROOT / package).rglob("*.py")):
            if "tests" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name not in _NETWORK_CALLS:
                    continue
                if name != "urlopen":
                    owner = getattr(getattr(func, "value", None), "id", "")
                    if owner.lower() not in _NETWORK_OWNERS:
                        continue
                if any(k.arg == "timeout" for k in node.keywords):
                    continue
                found.append((str(path.relative_to(ROOT)), node.lineno, name))
    return found


UNTIMED = _calls_without_timeout()


def test_the_scan_finds_network_calls_at_all() -> None:
    """A scan matching nothing would make the assertion below vacuous."""
    text = (ROOT / "dhfkit" / "artifact_fetcher.py").read_text()
    assert text.count("urlopen(") >= 4, "the probe file no longer has the calls"


@pytest.mark.parametrize("where,line,name", UNTIMED,
                         ids=[f"{w}:{ln}" for w, ln, _n in UNTIMED] or ["none"])
def test_no_network_call_lacks_a_timeout(where: str, line: int, name: str) -> None:
    pytest.fail(
        f"{where}:{line} calls {name}() with no timeout. Python's default is to "
        f"block forever, and this runs in CI."
    )


def _text_io_without_encoding() -> list[tuple[str, int, str]]:
    """`read_text()` / `write_text(...)` that fall back to the locale.

    On Python 3.11 those use `locale.getpreferredencoding()`. A DHF with any
    non-ASCII content — a Chinese requirement title, an accented supplier name —
    raises UnicodeDecodeError on a runner whose locale is not UTF-8, and the
    same file reads fine on the developer's machine.
    """
    found = []
    for package in ("dhfkit", "medharness"):
        for path in sorted((ROOT / package).rglob("*.py")):
            if "tests" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call):
                    continue
                name = getattr(node.func, "attr", None)
                if name not in ("read_text", "write_text"):
                    continue
                if any(k.arg == "encoding" for k in node.keywords):
                    continue
                found.append((str(path.relative_to(ROOT)), node.lineno, name))
    return found


UNENCODED = _text_io_without_encoding()


def test_the_encoding_scan_sees_real_calls() -> None:
    text = (ROOT / "medharness" / "workflows" / "upgrade.py").read_text(encoding="utf-8")
    assert "read_text(" in text, "the probe file no longer does text IO"


@pytest.mark.parametrize("where,line,name", UNENCODED,
                         ids=[f"{w}:{ln}" for w, ln, _n in UNENCODED] or ["none"])
def test_text_io_names_its_encoding(where: str, line: int, name: str) -> None:
    pytest.fail(
        f"{where}:{line} calls {name}() without an encoding, so it uses the "
        f"runner's locale. A DHF with any non-ASCII content then reads on one "
        f"machine and raises UnicodeDecodeError on another."
    )
