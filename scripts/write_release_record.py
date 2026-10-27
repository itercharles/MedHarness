"""Write `release.json`, the record a release's wheel carries for `build validation` (ADR-005).

It holds what the installed package is compared against without downloading anything: the
version and commit, the evidence files attached to the GitHub Release, the dependency
versions the suite passed with (from the `tested-with` constraints file), and the text of
each high-risk requirement the validation set covers, from MedHarness's own DHF.

    python scripts/write_release_record.py --version 0.71.0 --commit SHA \\
        --evidence-dir evidence --dhf DHF --out medharness/validation/release.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dhfkit.store import open_store  # noqa: E402

_POINT = re.compile(r"^\s*(T\d+)\s*:\s*(.*?)(?=^\s*T\d+\s*:|\Z)", re.MULTILINE | re.DOTALL)


def tested_with(path: Path) -> list[dict]:
    """`name==version ; marker` lines, as `uv export` writes them."""
    pins = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pin, _, marker = line.partition(";")
        name, sep, version = pin.strip().partition("==")
        if not sep:
            raise SystemExit(f"{path}: not a pinned requirement: {line!r}")
        pins.append({"name": name.strip(), "version": version.strip(), "marker": marker.strip() or None})
    return pins


def requirements(dhf: Path) -> list[dict]:
    return [
        {"id": item["id"], "title": item["title"], "risk": item["risk"],
         "points": [{"id": uid, "text": " ".join(text.split())} for uid, text in _POINT.findall(item.get("testing") or "")]}
        for item in open_store(dhf).list_items("SRS") if item.get("risk") == "high"
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--dhf", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    constraints = args.evidence_dir / f"medharness-{args.version}-tested-with.txt"
    record = {
        "version": args.version,
        "commit": args.commit,
        "evidence": sorted(p.name for p in args.evidence_dir.iterdir() if p.is_file()),
        "tested_with": tested_with(constraints),
        "requirements": requirements(args.dhf),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
