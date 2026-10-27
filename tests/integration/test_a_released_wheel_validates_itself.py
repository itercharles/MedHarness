"""A wheel built as the release builds it validates itself where it is installed.

The release writes `release.json` into the package before building the wheel. Here the same
script writes it, with this environment as the tested configuration, the wheel is built with
`python -m build` from a clean copy of the tree, unpacked into a fresh virtual environment
the way an installer does, and `build validation` runs from there, not from this checkout.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import sysconfig
import zipfile
from importlib import metadata
from pathlib import Path

import pytest

from medharness.results import ValidationReport
from medharness.validation import CASES

ROOT = Path(__file__).resolve().parents[2]
NOISE = shutil.ignore_patterns(".git", ".venv", "build", "dist", "*.egg-info", "__pycache__", ".pytest_cache")


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The interpreter of a virtual environment with the built wheel in it, and this one's dependencies."""
    pytest.importorskip("build", reason="the 'build' package is required to build the wheel")
    work = tmp_path_factory.mktemp("wheel")
    src = work / "src"
    shutil.copytree(ROOT, src, ignore=NOISE)
    evidence = work / "evidence"
    evidence.mkdir()
    pins = sorted({f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions()
                   if d.metadata["Name"] and d.metadata["Name"].lower() != "medharness"})
    (evidence / "medharness-9.9.9-tested-with.txt").write_text("\n".join(pins) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(src / "scripts" / "write_release_record.py"), "--version", "9.9.9",
                    "--commit", "abc123", "--evidence-dir", str(evidence), "--dhf", str(src / "DHF"),
                    "--out", str(src / "medharness" / "validation" / "release.json")], check=True)
    proc = subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(work / "dist")],
                          cwd=src, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]
    (wheel,) = (work / "dist").glob("*.whl")

    venv = work / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    site = Path(subprocess.run([str(python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
                               capture_output=True, text=True, check=True).stdout.strip())
    with zipfile.ZipFile(wheel) as zf:
        zf.extractall(site)
    # The dependencies come from this environment, after the wheel on the path: a plain path
    # line, so the editable install of this checkout that lives there is not activated.
    (site / "zz_dependencies.pth").write_text(sysconfig.get_paths()["purelib"] + "\n", encoding="utf-8")
    where = subprocess.run([str(python), "-c", "import medharness; print(medharness.__file__)"],
                           capture_output=True, text=True, check=True, cwd=work).stdout.strip()
    assert Path(where).is_relative_to(site), f"the venv imports medharness from {where}, not the wheel"
    return python


# Every run is from a directory outside the checkout: `python -c` and `-m` put the working
# directory first on the path, and from the repository that would import its source instead.
def _validate(python: Path, out: Path) -> tuple[subprocess.CompletedProcess, dict]:
    proc = subprocess.run([str(python), "-m", "medharness", "build", "validation", "--out-dir", str(out)],
                          capture_output=True, text=True, cwd=out.parent)
    return proc, ValidationReport.model_validate_json(proc.stdout).model_dump()


@pytest.mark.dhf_links("SRS-073")
@pytest.mark.dhf_testing("T1")
def test_the_installed_wheel_is_checked_against_its_release_record(installed: Path, tmp_path: Path) -> None:
    proc, report = _validate(installed, tmp_path / "report")
    assert "Traceback" not in proc.stderr, proc.stderr[-2000:]
    assert report["installation"]["verifiable"] and report["installation"]["altered"] == []
    assert report["installation"]["files_checked"] > 50
    assert report["release"]["version"] == "9.9.9" and report["release"]["commit"] == "abc123"
    assert report["dependencies"] and {d["status"] for d in report["dependencies"]} == {"equal"}
    assert sum(len(r["points"]) for r in report["requirements"]) == 170

    exercised = {(c.requirement, p) for c in CASES for p in c.points}
    statuses = {(r["id"], p["id"]): p["status"] for r in report["requirements"] for p in r["points"]}
    assert {statuses[k] for k in exercised} == {"passed"}
    unexercised = [k for k in statuses if k not in exercised]
    # Until every high-risk point has a case, the set cannot say the tool is validated.
    assert {statuses[k] for k in unexercised} <= {"not_run"}
    assert report["result"] == ("incomplete" if unexercised else "passed")
    assert proc.returncode == (1 if unexercised else 0)
    assert (tmp_path / "report" / "validation-report.html").is_file()


@pytest.mark.dhf_links("SRS-071")
@pytest.mark.dhf_testing("T5")
def test_an_installed_file_that_was_changed_is_named(installed: Path, tmp_path: Path) -> None:
    site = Path(subprocess.run([str(installed), "-c", "import medharness, pathlib; print(pathlib.Path(medharness.__file__).parents[1])"],
                               capture_output=True, text=True, check=True, cwd=tmp_path).stdout.strip())
    target = site / "medharness" / "services" / "verify_impact.py"
    original = target.read_text(encoding="utf-8")
    target.write_text(original + "\n# changed after installation\n", encoding="utf-8")
    try:
        proc = subprocess.run([str(installed), "-c", "import json; from medharness.services.validation import _installation;"
                               "print(json.dumps(_installation()))"], capture_output=True, text=True, check=True, cwd=tmp_path)
    finally:
        target.write_text(original, encoding="utf-8")
    assert json.loads(proc.stdout)["altered"] == ["medharness/services/verify_impact.py"]
