"""`build validation`: run the validation set where MedHarness is installed, and write the report.

The report is the user's evidence that the installed tool stops what it is relied on to stop
in their environment (ADR-005). It never reads the user's project: every case runs in a
temporary directory that is removed afterwards, and nothing reaches the network.
"""

from __future__ import annotations

import base64
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import medharness.validation as validation_package
from dhfkit.store import open_store
from medharness.scaffold import scaffold_dhf
from medharness.validation import CASES
from medharness.validation.case import Outcome, run_cases

#: Written into the package by the release build; absent from a source checkout.
RELEASE_RECORD = Path(validation_package.__file__).parent / "release.json"
REPORT = "validation-report"
TEMPLATE = "validation_report.md.j2"


def _digest(path: Path) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).rstrip(b"=").decode()


def _installation() -> dict:
    """Each file of the installed distribution against the hash its RECORD gives it."""
    dist = metadata.distribution("medharness")
    checked, altered = 0, []
    for file in dist.files or []:
        if file.hash is None or file.hash.mode != "sha256":
            continue
        path = Path(file.locate())
        checked += 1
        if not path.is_file() or _digest(path) != file.hash.value:
            altered.append(str(file))
    # An editable install records no module of the package, only the link to the source tree.
    verifiable = any(str(file).startswith("medharness/") and file.hash for file in dist.files or [])
    return {"version": dist.version, "verifiable": verifiable, "files_checked": checked, "altered": altered}


def _dependencies(record: dict | None) -> list[dict]:
    rows = []
    for dep in (record or {}).get("tested_with", []):
        try:
            installed = metadata.version(dep["name"])
        except metadata.PackageNotFoundError:
            installed = None
        status = "missing" if installed is None else "equal" if installed == dep["version"] else "different"
        rows.append({"name": dep["name"], "tested": dep["version"], "marker": dep.get("marker"),
                     "installed": installed, "status": status})
    return rows


def _tool_version(*command: str) -> str:
    if shutil.which(command[0]) is None:
        return "not found"
    proc = subprocess.run(command, capture_output=True, text=True)
    return (proc.stdout or proc.stderr).strip().splitlines()[0] if (proc.stdout or proc.stderr).strip() else "found"


def _pdf() -> str:
    try:
        import weasyprint  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001  (missing native libraries raise OSError, not ImportError)
        return f"not available ({type(exc).__name__})"
    return f"WeasyPrint {weasyprint.__version__}"


def _environment() -> dict:
    return {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python": f"{platform.python_implementation()} {platform.python_version()}",
        "git": _tool_version("git", "--version"),
        "ssh_keygen": shutil.which("ssh-keygen") or "not found",
        "pdf": _pdf(),
    }


def _point(cases: list[Outcome]) -> tuple[str, str]:
    if not cases:
        return "not_run", "no validation case exercises this point yet"
    for status in ("failed", "not_run"):
        messages = [f"{o.case.name}: {o.message}" for o in cases if o.status == status]
        if messages:
            return status, "; ".join(messages)
    return "passed", ""


def _requirements(record: dict | None, outcomes: list[Outcome]) -> tuple[list[dict], list[str]]:
    """Each requirement's test points with what exercised them, and cases that match no point."""
    declared = (record or {}).get("requirements") or [
        {"id": uid, "title": None, "risk": None,
         "points": [{"id": p, "text": None} for p in sorted({p for c in CASES if c.requirement == uid for p in c.points},
                                                              key=lambda p: int(p[1:]))]}
        for uid in sorted({c.requirement for c in CASES})
    ]
    known = {(r["id"], p["id"]) for r in declared for p in r["points"]}
    stale = [f"case {o.case.name} exercises {o.case.requirement} {p}, which the release does not define"
             for o in outcomes for p in o.case.points if (o.case.requirement, p) not in known]
    requirements = []
    for req in declared:
        points = []
        for point in req["points"]:
            by = [o for o in outcomes if o.case.requirement == req["id"] and point["id"] in o.case.points]
            status, message = _point(by)
            points.append({**point, "cases": [o.case.name for o in by], "status": status, "message": message})
        requirements.append({**req, "points": points})
    return requirements, stale


def _verdict(installation: dict, record: dict | None, requirements: list[dict], stale: list[str]) -> tuple[str, list[str]]:
    points = [p for r in requirements for p in r["points"]]
    failed = [f"{r['id']} {p['id']}: {p['message']}" for r in requirements for p in r["points"] if p["status"] == "failed"]
    errors = [f"FAILED {f}" for f in failed] + stale
    errors += [f"installed file differs from the release: {f}" for f in installation["altered"]]
    if errors:
        return "failed", errors
    not_run = sum(p["status"] == "not_run" for p in points)
    if not_run:
        errors.append(f"{not_run} of {len(points)} test point(s) were not run")
    if record is None:
        errors.append("this installation carries no release record: it is not a released build, "
                      "so there is no tested configuration or requirement text to compare against")
    if not installation["verifiable"]:
        errors.append("the installed files cannot be checked: the package is not installed from a wheel")
    return ("incomplete" if errors else "passed"), errors


def build_validation(out_dir: Path, doc_format: str = "html") -> dict:
    """Run the validation set and write `validation-report.<doc_format>` to *out_dir*."""
    record = json.loads(RELEASE_RECORD.read_text(encoding="utf-8")) if RELEASE_RECORD.is_file() else None
    ran_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    installation = _installation()
    with tempfile.TemporaryDirectory(prefix="medharness-validation-") as tmp:
        outcomes = run_cases(CASES, Path(tmp) / "run")
        requirements, stale = _requirements(record, outcomes)
        result, errors = _verdict(installation, record, requirements, stale)
        report = {
            "result": result, "ran_at": ran_at, "installation": installation,
            "dependencies": _dependencies(record), "environment": _environment(), "requirements": requirements,
            "release": {k: record[k] for k in ("version", "commit", "evidence")} if record else None,
            "errors": errors,
        }
        report["report_hash"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
        path = out_dir / f"{REPORT}.{doc_format}"
        scaffold_dhf(Path(tmp) / "render")
        try:
            open_store(Path(tmp) / "render" / "DHF").render_document(TEMPLATE, report, doc_format, path)
        except RuntimeError as exc:
            return {**report, "path": None, "errors": [*errors, str(exc)]}
    return {**report, "path": str(path)}
